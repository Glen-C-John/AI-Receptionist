"""
Call log Pydantic model.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, field_validator
from app.utils.validators import normalize_phone_number

class CallLogBase(BaseModel):
    """Base call log schema."""
    phone_number: str
    summary: Optional[str] = None
    outcome: Optional[str] = None

    # REUSE THE VALIDATOR!
    @field_validator('phone_number')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Ensure phone numbers in logs match Client format."""
        return normalize_phone_number(v) or v  # Return original if validation fails slightly (logs shouldn't crash)


class CallLogCreate(CallLogBase):
    client_id: Optional[UUID] = None
    call_sid: Optional[str] = None
    duration_seconds: Optional[int] = None
    conversation_transcript: Optional[Dict[str, Any]] = None


class CallLog(CallLogBase):
    id: UUID = Field(default_factory=uuid4)
    client_id: Optional[UUID] = None
    call_sid: Optional[str] = None
    duration_seconds: Optional[int] = None
    conversation_transcript: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        from_attributes = True