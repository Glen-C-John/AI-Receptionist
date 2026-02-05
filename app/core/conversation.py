"""
Conversation state management.
Handles context, history, and state transitions for active calls.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field, ConfigDict
from app.utils.logger import logger


class ConversationState(str, Enum):
    """Conversation states for flow control."""
    GREETING = "greeting"
    COLLECTING_NAME = "collecting_name" # Added this as it's often a distinct step
    COLLECTING_INFO = "collecting_info"
    CHECKING_AVAILABILITY = "checking_availability"
    BOOKING = "booking"
    UPDATING = "updating"
    CANCELLING = "cancelling"
    ANSWERING_QUESTION = "answering_question"
    TRANSFERRING = "transferring"
    ENDING = "ending"


class ConversationContext(BaseModel):
    """
    Context for an active conversation.
    Stores all metadata required to maintain state between voice turns.
    """
    # Pydantic V2 Configuration
    model_config = ConfigDict(use_enum_values=True)

    # Identifier
    call_sid: str
    phone_number: str
    state: ConversationState = ConversationState.GREETING
    
    # Client Data
    client_id: Optional[str] = None
    client_email: Optional[str] = None
    client_name: Optional[str] = None
    
    # Appointment Context (Scratchpad for partial info)
    appointment_type: Optional[str] = None
    appointment_date: Optional[str] = None
    appointment_time: Optional[str] = None
    appointment_id: Optional[str] = None
    
    # History & Metadata
    # FIX: Use default_factory to prevent shared mutable state
    messages: List[Dict[str, str]] = Field(default_factory=list)
    turn_count: int = 0
    
    # FIX: Use lambda for dynamic timestamp generation
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Flags
    is_new_client: bool = False
    needs_transfer: bool = False


class ConversationManager:
    """Manages conversation state for active calls (In-Memory)."""
    
    def __init__(self):
        self.active_conversations: Dict[str, ConversationContext] = {}
        logger.info("✓ Conversation manager initialized")
    
    def start_conversation(self, call_sid: str, phone_number: str) -> ConversationContext:
        """Start a new conversation session."""
        # Optional: Auto-cleanup occasionally to prevent memory leaks
        if len(self.active_conversations) > 100:
            self._cleanup_stale_conversations()

        context = ConversationContext(
            call_sid=call_sid,
            phone_number=phone_number
        )
        
        self.active_conversations[call_sid] = context
        logger.info(f"Started conversation: {call_sid}")
        return context
    
    def get_conversation(self, call_sid: str) -> Optional[ConversationContext]:
        """Retrieve active conversation."""
        return self.active_conversations.get(call_sid)
    
    def update_state(self, call_sid: str, new_state: ConversationState) -> bool:
        """Transition conversation state."""
        context = self.get_conversation(call_sid)
        if context:
            old_state = context.state
            context.state = new_state
            context.last_updated_at = datetime.now(timezone.utc)
            logger.info(f"State transition: {old_state} -> {new_state} (call: {call_sid})")
            return True
        return False
    
    def add_message(self, call_sid: str, role: str, content: str):
        """Add message to history and update timestamp."""
        context = self.get_conversation(call_sid)
        if context:
            context.messages.append({
                "role": role,
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            context.turn_count += 1
            context.last_updated_at = datetime.now(timezone.utc)
    
    def update_context(self, call_sid: str, **kwargs):
        """Update arbitrary context fields (e.g., extracted date/time)."""
        context = self.get_conversation(call_sid)
        if context:
            for key, value in kwargs.items():
                if hasattr(context, key):
                    setattr(context, key, value)
            context.last_updated_at = datetime.now(timezone.utc)

    def end_conversation(self, call_sid: str) -> Optional[ConversationContext]:
        """Remove conversation from memory."""
        context = self.active_conversations.pop(call_sid, None)
        if context:
            logger.info(f"Ended conversation: {call_sid} (Duration: {datetime.now(timezone.utc) - context.started_at})")
        return context

    def _cleanup_stale_conversations(self):
        """Remove conversations inactive for > 1 hour (Memory protection)."""
        now = datetime.now(timezone.utc)
        limit = timedelta(hours=1)
        
        # Identify stale keys
        stale_ids = [
            sid for sid, ctx in self.active_conversations.items()
            if (now - ctx.last_updated_at) > limit
        ]
        
        # Remove them
        for sid in stale_ids:
            self.active_conversations.pop(sid, None)
            
        if stale_ids:
            logger.warning(f"Cleaned up {len(stale_ids)} stale conversations")


# Singleton instance
conversation_manager = ConversationManager()