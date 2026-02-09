"""
Main voice agent orchestration.
The "Brain" that coordinates LLM, Database, Calendar, and TTS services.

This is the production-ready version with:
- Robust state machine
- Intent analysis with conversation context
- Email/phone/date parsing from speech
- Confirmation flows
- Retry logic
- Business hours validation
- Latency masking with filler phrases
"""

import asyncio
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from dateutil import parser as date_parser

from app.config import settings
from app.utils.logger import logger
from app.utils.validators import normalize_phone_number
from app.services.llm_service import llm_service
from app.services.tts_service import tts_service
from app.services.database_service import db_service
from app.services.calendar_service import calendar_service
from app.core.conversation import conversation_manager, ConversationState, ConversationContext
from app.models.client import ClientCreate
from app.models.appointment import AppointmentCreate, AppointmentType
from app.models.call_log import CallLogCreate


class VoiceAgent:
    """
    Orchestrates the voice conversation flow.
    
    Implements a state machine that handles:
    - Client identification
    - Information collection
    - Appointment booking
    - General Q&A
    """

    def __init__(self):
        """Initialize voice agent."""
        self.agent_name = settings.AGENT_NAME
        self.business_name = settings.BUSINESS_NAME
        logger.info(f"✓ Voice Agent '{self.agent_name}' initialized for {self.business_name}")

    # =========================================================================
    # ENTRY POINTS
    # =========================================================================

    async def generate_greeting(self, call_sid: str, phone_number: str) -> bytes:
        """
        Generate a personalized greeting based on caller history.
        
        Args:
            call_sid: Twilio call SID
            phone_number: Caller's phone number (E.164 format)
            
        Returns:
            Audio bytes (WAV format)
        """
        # 1. Start tracking conversation state
        context = conversation_manager.start_conversation(call_sid, phone_number)
        
        # 2. Check if this is a returning customer
        client = await db_service.get_client_by_phone(phone_number)
        
        if client:
            # Returning Customer
            greeting_text = (
                f"Hi {client.name}, welcome back to {self.business_name}. "
                f"This is {self.agent_name}. How can I help you today?"
            )
            conversation_manager.update_context(
                call_sid, 
                client_id=str(client.id),
                client_name=client.name,
                client_email=client.email,
                is_new_client=False
            )
            logger.info(f"👤 Returning client: {client.name} ({client.email})")
        else:
            # New Customer
            greeting_text = (
                f"Hello! Thank you for calling {self.business_name}. "
                f"This is {self.agent_name}. How can I help you today?"
            )
            conversation_manager.update_context(call_sid, is_new_client=True)
            logger.info(f"🆕 New caller: {phone_number}")

        # 3. Add to conversation history & synthesize
        conversation_manager.add_message(call_sid, "assistant", greeting_text)
        audio = await tts_service.generate_audio_file(greeting_text, output_filename=None)
        
        return audio or b""

    async def process_user_input(self, call_sid: str, user_text: str) -> Optional[bytes]:
        """
        Main conversation processing loop.
        
        Flow:
        1. Retrieve conversation context
        2. Route to appropriate state handler
        3. Analyze intent and extract entities
        4. Execute actions (DB/Calendar)
        5. Generate and return response
        
        Args:
            call_sid: Twilio call SID
            user_text: Transcribed user speech
            
        Returns:
            Audio response bytes
        """
        context = conversation_manager.get_conversation(call_sid)
        if not context:
            logger.error(f"❌ No context found for call {call_sid}")
            return None

        # Log user input
        conversation_manager.add_message(call_sid, "user", user_text)
        logger.info(f"💬 User [{context.state}]: {user_text}")

        # State machine routing
        if context.state == ConversationState.COLLECTING_NAME:
            return await self._handle_collecting_name(context, user_text)
            
        elif context.state == ConversationState.COLLECTING_PHONE:
            return await self._handle_collecting_phone(context, user_text)
            
        elif context.state == ConversationState.COLLECTING_INFO:
            return await self._handle_collecting_email(context, user_text)
            
        elif context.state == ConversationState.BOOKING:
            return await self._handle_booking_flow(context, user_text)
        
        elif context.state == ConversationState.BOOKING_CONFIRMATION:
            return await self._handle_booking_confirmation(context, user_text)
            
        elif context.state == ConversationState.CANCELLING:
            return await self._handle_cancellation(context, user_text)
            
        else:
            # General conversation / intent detection
            return await self._handle_general_intent(context, user_text)

    # =========================================================================
    # STATE HANDLERS
    # =========================================================================

    async def _handle_general_intent(self, context: ConversationContext, user_text: str) -> bytes:
        """
        Analyzes generic input to determine the next action.
        Handles intent detection and routing to appropriate state.
        """
        # Analyze intent with conversation context
        analysis = await llm_service.analyze_intent(user_text, context.messages)
        intent = analysis.get("intent", "unknown")
        entities = analysis.get("entities", {})

        logger.info(f"🧠 Intent: {intent} | Entities: {entities}")

        # Update context with extracted entities
        conversation_manager.update_context(
            context.call_sid,
            appointment_type=entities.get("service_type") or context.appointment_type,
            appointment_date=entities.get("date") or context.appointment_date,
            appointment_time=entities.get("time") or context.appointment_time
        )

        # ============ INTENT ROUTING ============
        
        if intent == "book_appointment":
            # New client needs to provide details first
            if context.is_new_client and not context.client_name:
                response_text = (
                    "I'd love to help you book that appointment. "
                    "Since you're a new client, could I get your full name first?"
                )
                conversation_manager.update_state(context.call_sid, ConversationState.COLLECTING_NAME)
            else:
                # Existing client or details already collected
                conversation_manager.update_state(context.call_sid, ConversationState.BOOKING)
                return await self._handle_booking_flow(context, user_text)
                
        elif intent == "check_availability":
            response_text = (
                "I can check that for you. What day and time were you thinking of?"
            )
            conversation_manager.update_state(context.call_sid, ConversationState.BOOKING)

        elif intent == "cancel_appointment":
            response_text = (
                "I can help you cancel. Do you remember what day your appointment was scheduled for?"
            )
            conversation_manager.update_state(context.call_sid, ConversationState.CANCELLING)

        elif intent == "reschedule":
            response_text = (
                "No problem! I can reschedule that for you. "
                "What's a better day and time?"
            )
            conversation_manager.update_state(context.call_sid, ConversationState.BOOKING)

        elif intent == "speak_to_human":
            response_text = (
                "Of course! Let me transfer you to our front desk. Please hold for just a moment."
            )
            conversation_manager.update_state(context.call_sid, ConversationState.TRANSFERRING)
            # TODO: Implement actual call transfer via Twilio

        else:
            # Fallback: General Q&A (pricing, services, hours, etc.)
            response_text = await llm_service.generate_response(
                context={"state": context.state, "business": self.business_name},
                user_input=user_text,
                conversation_history=context.messages
            )

        return await self._speak(context, response_text or "I'm sorry, I didn't quite catch that.")

    # =========================================================================
    # NEW CLIENT INFORMATION COLLECTION
    # =========================================================================

    async def _handle_collecting_name(self, context: ConversationContext, user_text: str) -> bytes:
        """
        Collect full name from new client.
        Uses LLM to extract name from natural speech.
        """
        # Use LLM to extract name
        analysis = await llm_service.analyze_intent(user_text, context.messages)
        name = analysis.get("entities", {}).get("name")

        if not name:
            # Fallback: If input is short (2-4 words), assume it's the name
            words = user_text.strip().split()
            if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words[:2]):
                name = " ".join(words[:4])
            else:
                return await self._speak(
                    context, 
                    "I'm sorry, I didn't quite catch your full name. Could you repeat it?"
                )

        # Update context and move to phone collection
        conversation_manager.update_context(context.call_sid, client_name=name)
        conversation_manager.update_state(context.call_sid, ConversationState.COLLECTING_PHONE)
        
        return await self._speak(
            context, 
            f"Thanks {name}. And what's a good phone number to reach you at?"
        )

    async def _handle_collecting_phone(self, context: ConversationContext, user_text: str) -> bytes:
        """
        Collect phone number from new client.
        Parses phone from speech (challenging!).
        """
        # Try to parse phone from speech
        phone = self._parse_phone_from_speech(user_text)
        
        if not phone:
            return await self._speak(
                context,
                "I didn't quite catch that number. Could you say it again, digit by digit?"
            )
        
        # Validate and normalize
        try:
            normalized_phone = normalize_phone_number(phone)
            if not normalized_phone:
                raise ValueError("Invalid phone")
        except ValueError:
            return await self._speak(
                context,
                "That doesn't seem like a valid phone number. Could you try again?"
            )
        
        # Update context and move to email collection
        conversation_manager.update_context(context.call_sid, client_phone=normalized_phone)
        conversation_manager.update_state(context.call_sid, ConversationState.COLLECTING_INFO)
        
        return await self._speak(
            context,
            "Got it. And what's the best email address to send your confirmation to?"
        )

    async def _handle_collecting_email(self, context: ConversationContext, user_text: str) -> bytes:
        """
        Collect email address from new client.
        Creates client profile in database.
        """
        # Use LLM to extract email
        analysis = await llm_service.analyze_intent(user_text, context.messages)
        email_candidate = analysis.get("entities", {}).get("email")
        
        if not email_candidate:
            # Fallback: Try parsing from speech
            email_candidate = self._parse_email_from_speech(user_text)
        
        if not email_candidate or "@" not in email_candidate:
            return await self._speak(
                context, 
                "I didn't catch that email. Could you spell it out? "
                "Like 'john dot smith at gmail dot com'?"
            )
        
        # Add filler while creating client
        await self._speak(context, "Perfect, let me get that set up for you...")
        
        # Create client in database
        try:
            new_client = await db_service.create_client(ClientCreate(
                name=context.client_name,
                phone=context.client_phone or context.phone_number,
                email=email_candidate
            ))
        except ValueError as e:
            logger.error(f"Client creation validation error: {e}")
            return await self._speak(
                context,
                "That email doesn't seem quite right. Could you say it again?"
            )
        except Exception as e:
            logger.error(f"Client creation failed: {e}")
            return await self._speak(
                context,
                "I'm having trouble with my system right now. Could we try again in a moment?"
            )
        
        if new_client:
            # Success! Update context
            conversation_manager.update_context(
                context.call_sid, 
                client_id=str(new_client.id),
                client_email=new_client.email,
                is_new_client=False
            )
            conversation_manager.update_state(context.call_sid, ConversationState.BOOKING)
            
            logger.success(f"✓ Created new client: {new_client.email}")
            
            return await self._speak(
                context, 
                "All set! You're in our system. Now, what date and time works best for your appointment?"
            )
        else:
            return await self._speak(
                context,
                "I'm having trouble setting up your profile. Let me try that again."
            )

    # =========================================================================
    # APPOINTMENT BOOKING FLOW
    # =========================================================================

    async def _handle_booking_flow(self, context: ConversationContext, user_text: str) -> bytes:
        """
        Handles appointment booking negotiation.
        
        Collects:
        1. Service type (interior/exterior/full)
        2. Date and time
        3. Validates business hours and availability
        4. Moves to confirmation
        """
        # Extract entities from current input
        analysis = await llm_service.analyze_intent(user_text, context.messages)
        entities = analysis.get("entities", {})
        
        # Merge new info with existing context
        new_date = entities.get("date") or context.appointment_date
        new_time = entities.get("time") or context.appointment_time
        new_type = entities.get("service_type") or context.appointment_type
        
        conversation_manager.update_context(
            context.call_sid,
            appointment_date=new_date,
            appointment_time=new_time,
            appointment_type=new_type
        )

        # Check what information is still missing
        if not new_type:
            return await self._speak(
                context, 
                "What type of detailing would you like? We offer Interior, Exterior, or Full detail."
            )
        
        if not new_date or not new_time:
            return await self._speak(
                context, 
                "What day and time works best for you?"
            )

        # All info collected - validate and check availability
        
        # Parse datetime
        start_dt = self._parse_datetime(new_date, new_time)
        
        if not start_dt:
            return await self._speak(
                context, 
                "I didn't quite get that date and time. Could you say it again? "
                "Like 'March 15th at 2 PM'?"
            )
        
        # Ensure appointment is in the future
        now = datetime.now(timezone.utc)
        if start_dt < now:
            return await self._speak(
                context,
                "That time has already passed. Did you mean tomorrow or next week?"
            )
        
        # Check business hours
        if not self._is_within_business_hours(start_dt):
            return await self._speak(
                context,
                f"We're open from {settings.BUSINESS_HOURS_START} to {settings.BUSINESS_HOURS_END}. "
                f"Could you pick a time during our business hours?"
            )
        
        # Add filler phrase while checking calendar
        await self._speak(context, "Let me check that time for you...")
        
        # Calculate end time
        end_dt = start_dt + timedelta(minutes=settings.APPOINTMENT_DURATION_MINUTES)
        
        # Check calendar availability
        try:
            is_available = await db_service.check_availability(start_dt, end_dt)
        except Exception as e:
            logger.error(f"Availability check failed: {e}")
            return await self._speak(
                context,
                "I'm having trouble checking the calendar. Could you try again in a moment?"
            )
        
        if not is_available:
            return await self._speak(
                context,
                "I'm sorry, that time slot is already booked. "
                "Would an hour earlier or later work for you?"
            )
        
        # Time is available - move to confirmation
        conversation_manager.update_state(context.call_sid, ConversationState.BOOKING_CONFIRMATION)
        
        # Store parsed datetime for confirmation
        conversation_manager.update_context(
            context.call_sid,
            parsed_start_time=start_dt.isoformat(),
            parsed_end_time=end_dt.isoformat()
        )
        
        # Ask for confirmation
        formatted_time = start_dt.strftime('%A, %B %d at %I:%M %p')
        return await self._speak(
            context,
            f"Great! Just to confirm: you want {new_type} detailing on {formatted_time}. "
            f"Is that correct?"
        )

    async def _handle_booking_confirmation(self, context: ConversationContext, user_text: str) -> bytes:
        """
        Handle user's confirmation response.
        Books appointment if confirmed, otherwise goes back to collection.
        """
        user_lower = user_text.lower()
        
        # Check for affirmative response
        affirmative_words = ["yes", "yeah", "yep", "correct", "right", "sure", "sounds good", "perfect"]
        negative_words = ["no", "nope", "wait", "actually", "change"]
        
        is_confirmed = any(word in user_lower for word in affirmative_words)
        is_rejected = any(word in user_lower for word in negative_words)
        
        if is_rejected:
            # User wants to change something
            conversation_manager.update_state(context.call_sid, ConversationState.BOOKING)
            return await self._speak(
                context,
                "No problem! What would you like to change?"
            )
        
        if not is_confirmed:
            # Ambiguous response
            return await self._speak(
                context,
                "I didn't quite catch that. Is this appointment time correct? Please say yes or no."
            )
        
        # User confirmed - proceed with booking!
        await self._speak(context, "Perfect! Let me book that for you...")
        
        # Retrieve stored datetime
        start_dt = datetime.fromisoformat(context.parsed_start_time)
        end_dt = datetime.fromisoformat(context.parsed_end_time)
        
        # Book with retry logic
        max_retries = 3
        event_id = None
        
        for attempt in range(max_retries):
            try:
                event_id = await calendar_service.create_event(
                    summary=f"{context.appointment_type.title()} Detail - {context.client_name}",
                    start_time=start_dt,
                    end_time=end_dt,
                    attendee_email=context.client_email,
                    description=f"{settings.BUSINESS_NAME} - {context.appointment_type} detailing service"
                )
                
                if event_id:
                    break  # Success!
                    
            except Exception as e:
                logger.error(f"Calendar booking attempt {attempt + 1} failed: {e}")
                
                if attempt == max_retries - 1:
                    # Final attempt failed
                    return await self._speak(
                        context,
                        "I'm having persistent technical issues with the calendar. "
                        "Your information is saved, and someone will call you back to confirm. "
                        "Is there anything else I can help with?"
                    )
                
                # Wait before retry
                await asyncio.sleep(0.5)
        
        if not event_id:
            return await self._speak(
                context,
                "I'm having trouble booking the calendar right now. "
                "Could you try calling back in a few minutes?"
            )
        
        # Save to database
        try:
            appointment = await db_service.create_appointment(AppointmentCreate(
                client_id=context.client_id,
                calendar_event_id=event_id,
                appointment_type=AppointmentType(context.appointment_type),
                start_time=start_dt,
                end_time=end_dt,
                notes="Booked via AI voice agent"
            ))
            
            if appointment:
                logger.success(f"✓ Appointment booked: {event_id}")
        except Exception as e:
            logger.error(f"Failed to save appointment to DB: {e}")
            # Calendar is booked, so we continue even if DB fails
        
        # Success!
        conversation_manager.update_state(context.call_sid, ConversationState.ENDING)
        
        formatted_time = start_dt.strftime('%A, %B %d at %I:%M %p')
        return await self._speak(
            context,
            f"All set! Your {context.appointment_type} detailing is confirmed for {formatted_time}. "
            f"You'll receive a confirmation email at {context.client_email}. "
            f"Is there anything else I can help you with today?"
        )

    # =========================================================================
    # CANCELLATION FLOW
    # =========================================================================

    async def _handle_cancellation(self, context: ConversationContext, user_text: str) -> bytes:
        """
        Handle appointment cancellation.
        TODO: Implement full cancellation logic.
        """
        # This is a placeholder - full implementation would:
        # 1. Ask for appointment date/time
        # 2. Look up appointment in DB
        # 3. Confirm cancellation
        # 4. Delete from calendar
        # 5. Update DB status
        
        return await self._speak(
            context,
            "I can help with cancellations. For now, could you call our office directly? "
            "The number is on our website. Is there anything else I can help with?"
        )

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    async def _speak(self, context: ConversationContext, text: str) -> bytes:
        """
        Helper to log, synthesize, and return audio.
        
        Args:
            context: Current conversation context
            text: Text to speak
            
        Returns:
            Audio bytes
        """
        conversation_manager.add_message(context.call_sid, "assistant", text)
        logger.info(f"🤖 Agent: {text[:100]}...")
        
        audio = await tts_service.generate_audio_file(text, output_filename=None)
        return audio or b""

    def _parse_email_from_speech(self, text: str) -> Optional[str]:
        """
        Parse email from speech input.
        
        Handles patterns like:
        - "john at gmail dot com"
        - "john.smith@example.com"
        - "my email is john@gmail.com"
        
        Args:
            text: Spoken text
            
        Returns:
            Parsed email or None
        """
        # Normalize to lowercase
        text = text.lower().strip()
        
        # Remove common phrases
        text = text.replace("my email is", "")
        text = text.replace("it's", "")
        text = text.replace("email", "")
        
        # Replace speech patterns
        text = text.replace(" at ", "@")
        text = text.replace(" dot ", ".")
        text = re.sub(r'\s+', '', text)  # Remove all spaces
        
        # Validate email pattern
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(email_pattern, text):
            return text
        
        return None

    def _parse_phone_from_speech(self, text: str) -> Optional[str]:
        """
        Parse phone number from speech.
        
        This is challenging because users might say:
        - "Five five five, one two three, four five six seven"
        - "My number is 555-123-4567"
        - "It's 5551234567"
        
        Args:
            text: Spoken text
            
        Returns:
            Parsed phone digits or None
        """
        # Convert word numbers to digits
        word_to_digit = {
            "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
            "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
            "oh": "0"
        }
        
        text_lower = text.lower()
        for word, digit in word_to_digit.items():
            text_lower = text_lower.replace(word, digit)
        
        # Extract all digits
        digits = re.findall(r'\d', text_lower)
        phone = ''.join(digits)
        
        # Validate length (10 or 11 digits for US/Canada)
        if len(phone) in [10, 11]:
            return phone
        
        return None

    def _parse_datetime(self, date_str: Optional[str], time_str: Optional[str]) -> Optional[datetime]:
        """
        Parse date and time strings into datetime object.
        
        Handles:
        - ISO formats: "2024-03-15", "14:00:00"
        - Natural language: "tomorrow", "next Monday", "2pm"
        - Relative: "in 2 hours"
        
        Args:
            date_str: Date string
            time_str: Time string
            
        Returns:
            Parsed datetime (UTC) or None
        """
        try:
            # If LLM gave us clean ISO format
            if date_str and time_str:
                try:
                    dt = datetime.fromisoformat(f"{date_str}T{time_str}")
                    return dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    pass
            
            # Try parsing with dateutil (handles natural language)
            combined = f"{date_str or ''} {time_str or ''}".strip()
            if combined:
                dt = date_parser.parse(combined, fuzzy=True)
                
                # Ensure timezone aware
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                
                return dt
            
            return None
            
        except Exception as e:
            logger.warning(f"Date parsing failed for '{date_str} {time_str}': {e}")
            return None

    def _is_within_business_hours(self, dt: datetime) -> bool:
        """
        Check if datetime falls within business hours.
        
        Args:
            dt: Datetime to check
            
        Returns:
            True if within business hours
        """
        time_str = dt.strftime("%H:%M")
        return settings.BUSINESS_HOURS_START <= time_str <= settings.BUSINESS_HOURS_END

    # =========================================================================
    # CALL CLEANUP
    # =========================================================================

    async def cleanup_call(self, call_sid: str):
        """
        Called when call ends (WebSocket disconnects).
        Saves call summary to database.
        
        Args:
            call_sid: Twilio call SID
        """
        context = conversation_manager.end_conversation(call_sid)
        
        if context:
            logger.info(f"📞 Call ended: {call_sid} (duration: {context.turn_count} turns)")
            
            # Save summary asynchronously (fire and forget)
            asyncio.create_task(self._save_call_summary(context))

    async def _save_call_summary(self, context: ConversationContext):
        """
        Generate AI summary and save call log to database.
        
        Args:
            context: Final conversation context
        """
        try:
            # 1. Generate summary using LLM
            transcript = "\n".join([
                f"{m['role']}: {m['content']}" 
                for m in context.messages
            ])
            
            summary_prompt = [
                {
                    "role": "system", 
                    "content": "Summarize this customer service call in 1-2 sentences. "
                               "Include what the customer wanted and the outcome."
                },
                {"role": "user", "content": transcript}
            ]
            
            summary = await llm_service.chat(summary_prompt, temperature=0.3, max_tokens=100)
            summary = summary or "Call completed."

            # 2. Determine outcome
            outcome_map = {
                ConversationState.ENDING: "appointment_booked",
                ConversationState.BOOKING_CONFIRMATION: "appointment_booked",
                ConversationState.TRANSFERRING: "transferred",
                ConversationState.CANCELLING: "appointment_cancelled",
                ConversationState.GREETING: "hung_up_early",
            }
            
            outcome = outcome_map.get(context.state, "completed")

            # 3. Calculate duration
            duration_seconds = int((datetime.now(timezone.utc) - context.started_at).total_seconds())

            # 4. Save to database
            await db_service.create_call_log(CallLogCreate(
                client_id=context.client_id if context.client_id else None,
                call_sid=context.call_sid,
                phone_number=context.phone_number,
                summary=summary,
                outcome=outcome,
                duration_seconds=duration_seconds,
                conversation_transcript={"messages": context.messages}
            ))
            
            logger.success(f"✓ Call log saved: {context.call_sid} - {outcome}")
            
        except Exception as e:
            logger.error(f"Failed to save call summary for {context.call_sid}: {e}")


# Singleton instance
voice_agent = VoiceAgent()