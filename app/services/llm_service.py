"""
LLM service with DeepSeek primary and Groq fallback.
Production-ready with async I/O, timeouts, retries, and validation.
"""

import asyncio
import json
import re
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from groq import AsyncGroq
from app.config import settings
from app.utils.logger import logger
from datetime import datetime


class LLMService:
    """Service for language model inference (Async, Production-Ready)."""
    
    # Valid intents for validation
    VALID_INTENTS = {
        "book_appointment",
        "check_availability",
        "cancel_appointment",
        "update_appointment",
        "pricing",
        "ask_question",
        "greeting",
        "unknown"
    }
    
    # Valid service types
    VALID_SERVICE_TYPES = {"interior", "exterior", "full", None}
    
    def __init__(self):
        """Initialize Async LLM clients."""
        # Primary: DeepSeek (Using AsyncOpenAI client)
        self.deepseek_client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL
        ) if settings.DEEPSEEK_API_KEY else None
        
        # Fallback: Groq (Using AsyncGroq client)
        self.groq_client = AsyncGroq(
            api_key=settings.GROQ_API_KEY
        )
        
        # Default models
        self.primary_model = settings.LLM_MODEL  # deepseek-chat
        self.fallback_model = "llama-3.3-70b-versatile"  # Fast & Smart
        
        logger.info("✓ LLM service initialized (Async with fallback)")
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500,
        use_fallback: bool = False,
        timeout: float = 10.0,
        max_retries: int = 2
    ) -> Optional[str]:
        """
        Generate chat completion using Primary -> Fallback strategy.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            use_fallback: Force use of Groq instead of DeepSeek
            timeout: Timeout in seconds for each API call
            max_retries: Number of retry attempts per provider
            
        Returns:
            Generated text or None if all attempts fail
        """
        
        # Try Primary (DeepSeek) first
        if self.deepseek_client and not use_fallback:
            for attempt in range(max_retries):
                try:
                    response = await asyncio.wait_for(
                        self.deepseek_client.chat.completions.create(
                            model=self.primary_model,
                            messages=messages,
                            temperature=temperature,
                            max_tokens=max_tokens
                        ),
                        timeout=timeout
                    )
                    
                    text = response.choices[0].message.content
                    logger.info(f"✓ DeepSeek response: {text[:50]}...")
                    return text
                
                except asyncio.TimeoutError:
                    logger.warning(f"⚠️ DeepSeek timeout (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.5)  # Brief delay before retry
                        continue
                    else:
                        logger.warning("⚠️ DeepSeek timed out, switching to Groq")
                        break
                
                except Exception as e:
                    logger.warning(f"⚠️ DeepSeek error (attempt {attempt + 1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.5)
                        continue
                    else:
                        logger.warning("⚠️ DeepSeek failed, switching to Groq")
                        break
        
        # Fallback to Groq
        for attempt in range(max_retries):
            try:
                response = await asyncio.wait_for(
                    self.groq_client.chat.completions.create(
                        model=self.fallback_model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens
                    ),
                    timeout=timeout
                )
                
                text = response.choices[0].message.content
                logger.info(f"✓ Groq response: {text[:50]}...")
                return text
            
            except asyncio.TimeoutError:
                logger.warning(f"⚠️ Groq timeout (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5)
                    continue
            
            except Exception as e:
                logger.error(f"✗ Groq error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5)
                    continue
        
        logger.error("✗ All LLM providers failed after retries")
        return None
    
    async def analyze_intent(
        self, 
        user_input: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Analyze user intent with context awareness and validation.
        
        Args:
            user_input: User's spoken text
            conversation_history: Optional previous messages for context
            
        Returns:
            Dict with validated intent and extracted entities
        """
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        system_prompt = """You are the brain of an AI Receptionist for Hercules Detailing.
Your job is to analyze what the caller wants and extract structured data.
CURRENT CONTEXT:
- Current Date/Time: {current_time}
- Business: Hercules Detailing

OUTPUT FORMAT: Strictly JSON. No markdown. No conversational text. No code blocks.

EXAMPLES:

User: "I need an appointment tomorrow at 2pm"
Output: {"intent": "book_appointment", "entities": {"date": "2025-02-07", "time": "14:00", "service_type": null, "name": null, "phone": null}}

User: "How much for a full detail?"
Output: {"intent": "pricing", "entities": {"service_type": "full", "date": null, "time": null, "name": null, "phone": null}}

User: "Are you free on Friday morning?"
Output: {"intent": "check_availability", "entities": {"date": "2025-02-07", "time": "09:00", "service_type": null, "name": null, "phone": null}}

User: "Cancel my appointment"
Output: {"intent": "cancel_appointment", "entities": {"date": null, "time": null, "service_type": null, "name": null, "phone": null}}

User: "My name is John Smith"
Output: {"intent": "unknown", "entities": {"name": "John Smith", "date": null, "time": null, "service_type": null, "phone": null}}

User: "Hello"
Output: {"intent": "greeting", "entities": {"date": null, "time": null, "service_type": null, "name": null, "phone": null}}

REQUIRED SCHEMA:
{
  "intent": "book_appointment" | "check_availability" | "cancel_appointment" | "update_appointment" | "pricing" | "ask_question" | "greeting" | "unknown",
  "entities": {
     "date": "YYYY-MM-DD" or null,
     "time": "HH:MM" (24-hour) or null,
     "service_type": "interior" | "exterior" | "full" | null,
     "name": string or null,
     "phone": string or null
  }
}

RULES:
- Always output valid JSON matching the schema exactly
- Use null for missing entities, never omit them
- Extract phone numbers in format: +1234567890
- Normalize dates to YYYY-MM-DD format
- Normalize times to 24-hour HH:MM format
- If uncertain about intent, use "unknown"
"""
        
        # Build messages with optional conversation history
        messages = [{"role": "system", "content": system_prompt}]
        
        if conversation_history:
            messages.extend(conversation_history[-3:])  # Last 3 exchanges for context
        
        messages.append({"role": "user", "content": user_input})
        
        # Use low temperature for consistent JSON output
        response_text = await self.chat(
            messages=messages,
            temperature=0.1,  # Low temp for deterministic output
            max_tokens=300,
            timeout=8.0
        )
        
        if not response_text:
            logger.error("✗ LLM returned no response for intent analysis")
            return {"intent": "unknown", "entities": {}}
        
        try:
            # Clean JSON response (remove markdown code blocks if present)
            cleaned_text = self._clean_json_response(response_text)
            
            # Parse JSON
            result = json.loads(cleaned_text)
            
            # Validate and fix the response
            result = self._validate_intent_response(result)
            
            logger.info(f"✓ Intent: {result['intent']}, Entities: {result['entities']}")
            return result
        
        except json.JSONDecodeError as e:
            logger.error(f"✗ Failed to parse LLM JSON: {response_text[:200]}...")
            logger.error(f"   JSON error: {e}")
            return {"intent": "unknown", "entities": {}}
    
    def _clean_json_response(self, text: str) -> str:
        """
        Clean LLM response to extract pure JSON.
        Removes markdown code blocks and extra whitespace.
        """
        # Remove ```json ... ``` wrappers
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```", "", text)
        
        # Remove any leading/trailing whitespace
        text = text.strip()
        
        # Try to extract JSON object if there's extra text
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            text = json_match.group(0)
        
        return text
    
    def _validate_intent_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and fix intent analysis response.
        Ensures schema compliance and data integrity.
        """
        # Validate intent
        if "intent" not in result or result["intent"] not in self.VALID_INTENTS:
            logger.warning(f"⚠️ Invalid intent: {result.get('intent')}, defaulting to 'unknown'")
            result["intent"] = "unknown"
        
        # Ensure entities dict exists
        if "entities" not in result or not isinstance(result["entities"], dict):
            result["entities"] = {}
        
        # Ensure all required entity fields exist
        required_fields = ["date", "time", "service_type", "name", "phone"]
        for field in required_fields:
            if field not in result["entities"]:
                result["entities"][field] = None
        
        # Validate service_type
        if result["entities"]["service_type"] not in self.VALID_SERVICE_TYPES:
            logger.warning(f"⚠️ Invalid service_type: {result['entities']['service_type']}")
            result["entities"]["service_type"] = None
        
        # Clean phone number format
        if result["entities"]["phone"]:
            phone = re.sub(r'[^\d+]', '', result["entities"]["phone"])
            result["entities"]["phone"] = phone if phone else None
        
        return result
    
    async def generate_response(
        self,
        context: Dict[str, Any],
        user_input: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Optional[str]:
        """
        Generate natural conversational response based on context.
        
        Args:
            context: Current conversation context (state, entities, etc.)
            user_input: User's latest input
            conversation_history: Previous conversation turns
            
        Returns:
            Generated response text
        """
        
        system_prompt = f"""You are Kylie, a friendly and professional AI receptionist for Hercules Detailing.

PERSONALITY:
- Warm, helpful, and conversational
- Professional but not robotic
- Concise responses (2-3 sentences max)
- Never mention you're an AI unless asked

CURRENT CONTEXT:
- Business: {settings.BUSINESS_NAME}
- Services: Interior Detailing, Exterior Detailing, Full Detailing
- Hours: {settings.BUSINESS_HOURS_START} - {settings.BUSINESS_HOURS_END}
- Timezone: {settings.BUSINESS_TIMEZONE}

CONVERSATION STATE: {context.get('state', 'greeting')}

YOUR TASKS:
1. If greeting -> Welcome them warmly, ask how you can help
2. If booking -> Guide them through: service type -> date/time -> confirm details
3. If checking availability -> Ask for preferred date/time
4. If pricing -> Share service costs clearly
5. If answering questions -> Provide helpful, accurate information

Keep responses natural and conversational. Never output JSON or structured data.
"""
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history for context
        if conversation_history:
            messages.extend(conversation_history[-5:])  # Last 5 exchanges
        
        messages.append({"role": "user", "content": user_input})
        
        response = await self.chat(
            messages=messages,
            temperature=0.8,  # Higher temp for natural conversation
            max_tokens=150,   # Keep responses concise
            timeout=10.0
        )
        
        return response
    
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500
    ):
        """
        Stream chat completion for lower latency (Optional).
        
        Yields:
            Text chunks as they're generated
        """
        try:
            if self.deepseek_client:
                try:
                    stream = await self.deepseek_client.chat.completions.create(
                        model=self.primary_model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        stream=True
                    )
                    
                    async for chunk in stream:
                        if chunk.choices[0].delta.content:
                            yield chunk.choices[0].delta.content
                    
                    return  # Success, exit
                
                except Exception as e:
                    logger.warning(f"⚠️ DeepSeek streaming failed: {e}, trying Groq")
            
            # Fallback to Groq streaming
            stream = await self.groq_client.chat.completions.create(
                model=self.fallback_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        
        except Exception as e:
            logger.error(f"✗ Streaming failed: {e}")
            yield None


# Singleton instance
llm_service = LLMService()