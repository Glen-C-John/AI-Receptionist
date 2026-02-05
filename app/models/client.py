"""
Client Pydantic models (Schema).
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, EmailStr, Field, field_validator

# IMPORT THE NEW VALIDATORS
from app.utils.validators import normalize_phone_number, normalize_name

class ClientBase(BaseModel):
    """Base client schema shared by Create and Read."""
    email: EmailStr
    name: str
    phone: Optional[str] = None
    
    # --- SHARED VALIDATORS ---
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        return normalize_phone_number(v)
        
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        return normalize_name(v)

    @field_validator('email')
    @classmethod
    def normalize_email(cls, v: EmailStr) -> str:
        """Ensure emails are always lowercase for reliable lookups."""
        return str(v).lower().strip()


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        return normalize_phone_number(v)
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if v is None: return None
        return normalize_name(v)


class Client(ClientBase):
    """
    Complete client model (matches Database).
    
    Database Indexes:
    - email (unique)
    - phone (for Twilio lookups)
    """
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        from_attributes = True