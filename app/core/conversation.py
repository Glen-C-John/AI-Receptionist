"""
Conversation state management.
Handles conversation context and state machine for voice calls.
"""

from enum import Enum
from typing import Optional, Dict, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field # <--- Added Field
from app.utils.logger import logger


class ConversationState(str, Enum):
    """
    Conversation states for the voice agent state machine.
    """
    GREETING = "greeting"
    COLLECTING_NAME = "collecting_name"
    COLLECTING_PHONE = "collecting_phone"
    COLLECTING_INFO = "collecting_info"  # Email collection
    CHECKING_AVAILABILITY = "checking_availability"
    BOOKING = "booking"
    BOOKING_CONFIRMATION = "booking_confirmation"
    UPDATING = "updating"
    CANCELLING = "cancelling"
    ANSWERING_QUESTION = "answering_question"
    TRANSFERRING = "transferring"
    ENDING = "ending"


class ConversationContext(BaseModel):
    """
    Context for an active conversation.
    """
    # Call identification
    call_sid: str
    phone_number: str
    
    # Current state
    state: ConversationState = ConversationState.GREETING
    
    # Client information
    client_id: Optional[str] = None
    client_email: Optional[str] = None
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    
    # Appointment booking context
    appointment_type: Optional[str] = None
    appointment_date: Optional[str] = None
    appointment_time: Optional[str] = None
    appointment_id: Optional[str] = None
    
    # Parsed datetime storage (for confirmation flow)
    parsed_start_time: Optional[str] = None
    parsed_end_time: Optional[str] = None
    
    # Conversation history
    # FIX: Use default_factory to ensure a fresh list for every call
    messages: List[Dict[str, str]] = Field(default_factory=list)
    
    turn_count: int = 0
    
    # FIX: Use default_factory so the time is calculated NOW, not at server startup
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Flags
    is_new_client: bool = False
    needs_transfer: bool = False
    booking_confirmed: bool = False
    
    class Config:
        use_enum_values = True


class ConversationManager:
    """
    Manages conversation state for active calls.
    """
    
    def __init__(self):
        """Initialize conversation manager."""
        self.active_conversations: Dict[str, ConversationContext] = {}
        logger.info("✓ Conversation manager initialized")
    
    def start_conversation(
        self,
        call_sid: str,
        phone_number: str
    ) -> ConversationContext:
        """Start a new conversation."""
        # Auto-cleanup to prevent memory leaks if many calls drop
        if len(self.active_conversations) > 500:
             self.cleanup_stale_conversations()

        context = ConversationContext(
            call_sid=call_sid,
            phone_number=phone_number
            # started_at is now handled automatically by the Field default
        )
        
        self.active_conversations[call_sid] = context
        logger.info(f"📞 Started conversation: {call_sid} from {phone_number}")
        
        return context
    
    def get_conversation(self, call_sid: str) -> Optional[ConversationContext]:
        """Retrieve active conversation."""
        return self.active_conversations.get(call_sid)
    
    def update_state(
        self,
        call_sid: str,
        new_state: ConversationState
    ) -> bool:
        """Update conversation state."""
        context = self.get_conversation(call_sid)
        if context:
            old_state = context.state
            context.state = new_state
            logger.info(f"🔄 State transition: {old_state} → {new_state} (call: {call_sid})")
            return True
        
        logger.warning(f"⚠ Cannot update state: conversation {call_sid} not found")
        return False
    
    def add_message(
        self,
        call_sid: str,
        role: str,
        content: str
    ):
        """Add message to conversation history."""
        context = self.get_conversation(call_sid)
        if context:
            context.messages.append({
                "role": role,
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            context.turn_count += 1
    
    def update_context(
        self,
        call_sid: str,
        **kwargs
    ):
        """Update conversation context fields."""
        context = self.get_conversation(call_sid)
        if context:
            for key, value in kwargs.items():
                if hasattr(context, key):
                    setattr(context, key, value)
                else:
                    logger.warning(f"⚠ Unknown context field: {key}")
    
    def end_conversation(self, call_sid: str) -> Optional[ConversationContext]:
        """End and remove conversation."""
        context = self.active_conversations.pop(call_sid, None)
        if context:
            duration = (datetime.now(timezone.utc) - context.started_at).total_seconds()
            logger.info(
                f"📴 Ended conversation: {call_sid} "
                f"(turns: {context.turn_count}, duration: {duration:.1f}s, state: {context.state})"
            )
        return context
    
    def get_active_count(self) -> int:
        """Get number of active conversations."""
        return len(self.active_conversations)
    
    def cleanup_stale_conversations(self, max_age_minutes: int = 30):
        """Remove conversations older than max_age_minutes."""
        now = datetime.now(timezone.utc)
        stale_calls = []
        
        for call_sid, context in self.active_conversations.items():
            age_minutes = (now - context.started_at).total_seconds() / 60
            if age_minutes > max_age_minutes:
                stale_calls.append(call_sid)
        
        for call_sid in stale_calls:
            self.active_conversations.pop(call_sid)
            logger.warning(f"🧹 Cleaned up stale conversation: {call_sid}")
        
        return len(stale_calls)


# Singleton instance
conversation_manager = ConversationManager()