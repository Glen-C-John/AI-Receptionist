"""
Appointment Pydantic model.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, model_validator
from enum import Enum


class AppointmentStatus(str, Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class AppointmentType(str, Enum):
    INTERIOR = "interior"
    EXTERIOR = "exterior"
    FULL = "full"


class AppointmentBase(BaseModel):
    """Base appointment schema."""
    appointment_type: AppointmentType
    start_time: datetime
    end_time: datetime
    notes: Optional[str] = None

    @model_validator(mode='after')
    def validate_appointment_logic(self):
        """Sanity checks for appointment times."""
        # 1. Check chronology
        if self.end_time <= self.start_time:
            raise ValueError('End time must be after start time')
            
        # 2. Check duration limits
        duration = self.end_time - self.start_time
        
        if duration < timedelta(minutes=15):
            raise ValueError('Appointment must be at least 15 minutes')
            
        if duration > timedelta(hours=8):
            raise ValueError('Appointment cannot exceed 8 hours (data entry error?)')
            
        return self


class AppointmentCreate(AppointmentBase):
    client_id: UUID
    calendar_event_id: Optional[str] = None


class AppointmentUpdate(BaseModel):
    appointment_type: Optional[AppointmentType] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[AppointmentStatus] = None
    notes: Optional[str] = None


class Appointment(AppointmentBase):
    id: UUID = Field(default_factory=uuid4)
    client_id: UUID
    calendar_event_id: Optional[str] = None
    status: AppointmentStatus = AppointmentStatus.SCHEDULED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        from_attributes = True