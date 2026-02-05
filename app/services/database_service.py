"""
Database service for Supabase operations.
"""

from typing import Optional, List
from uuid import UUID
from datetime import datetime
from supabase import create_client, Client as SupabaseClient
from app.config import settings
from app.utils.logger import logger
from app.utils.validators import normalize_phone_number
from app.models.client import Client, ClientCreate, ClientUpdate
from app.models.appointment import Appointment, AppointmentCreate, AppointmentUpdate
from app.models.call_log import CallLog, CallLogCreate


class DatabaseService:
    """Service for database operations using Supabase."""
    
    def __init__(self):
        """Initialize Supabase client."""
        self.client: SupabaseClient = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )
    
    # ==================== CLIENT OPERATIONS ====================
    
    async def get_client_by_email(self, email: str) -> Optional[Client]:
        """Retrieve a client by email address (case-insensitive)."""
        try:
            response = self.client.table("clients").select("*").eq(
                "email", email.lower().strip()
            ).execute()
            
            if response.data:
                return Client(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error fetching client by email: {e}")
            return None
    
    async def get_client_by_phone(self, phone: str) -> Optional[Client]:
        """Retrieve a client by phone number (auto-normalized to E.164)."""
        try:
            # Defensive normalization
            normalized_phone = normalize_phone_number(phone)
            
            if not normalized_phone:
                logger.warning(f"Invalid phone number for lookup: {phone}")
                return None
            
            response = self.client.table("clients").select("*").eq(
                "phone", normalized_phone
            ).execute()
            
            if response.data:
                return Client(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error fetching client by phone: {e}")
            return None
    
    async def create_client(self, client_data: ClientCreate) -> Optional[Client]:
        """Create a new client."""
        try:
            data = client_data.model_dump()
            # Double check email lowercasing
            if "email" in data: data["email"] = data["email"].lower()
            
            response = self.client.table("clients").insert(data).execute()
            
            if response.data:
                logger.info(f"Created new client: {data.get('email')}")
                return Client(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error creating client: {e}")
            return None
    
    async def update_client(self, client_id: UUID, update_data: ClientUpdate) -> Optional[Client]:
        """Update an existing client."""
        try:
            data = update_data.model_dump(exclude_unset=True)
            
            # FIXED: Table name is 'clients', not 'appointments'
            response = self.client.table("clients").update(data).eq(
                "id", str(client_id)
            ).execute()
            
            if response.data:
                return Client(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error updating client: {e}")
            return None
    
    # ==================== APPOINTMENT OPERATIONS ====================
    
    async def get_appointments_by_client(self, client_id: UUID) -> List[Appointment]:
        """Retrieve all appointments for a client."""
        try:
            response = self.client.table("appointments").select("*").eq(
                "client_id", str(client_id)
            ).order("start_time", desc=True).execute()
            
            return [Appointment(**apt) for apt in response.data]
        except Exception as e:
            logger.error(f"Error fetching appointments: {e}")
            return []

    async def check_availability(self, start_time: datetime, end_time: datetime) -> bool:
        """
        Check if a time slot is free.
        Returns True if available, False if overlapping appointment exists.
        """
        try:
            start_iso = start_time.isoformat()
            end_iso = end_time.isoformat()
            
            # Query for overlapping appointments (not cancelled)
            response = (
                self.client.table("appointments")
                .select("id")
                .lt("start_time", end_iso)  # Existing starts before requested ends
                .gt("end_time", start_iso)  # Existing ends after requested starts
                .neq("status", "cancelled") # Ignore cancelled ones
                .execute()
            )
            
            if response.data:
                logger.warning(f"Time slot conflict found for {start_time}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            # Fail-safe: assume booked to prevent double-booking
            return False

    async def create_appointment(self, appointment_data: AppointmentCreate) -> Optional[Appointment]:
        """Create a new appointment."""
        try:
            data = appointment_data.model_dump()
            data["client_id"] = str(data["client_id"])
            data["start_time"] = data["start_time"].isoformat()
            data["end_time"] = data["end_time"].isoformat()
            
            response = self.client.table("appointments").insert(data).execute()
            
            if response.data:
                logger.info(f"Created appointment for client {data['client_id']}")
                return Appointment(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error creating appointment: {e}")
            return None

    async def update_appointment(self, appointment_id: UUID, update_data: AppointmentUpdate) -> Optional[Appointment]:
        """Update/Cancel an appointment."""
        try:
            data = update_data.model_dump(exclude_unset=True)
            
            # Convert datetimes to strings if present
            if "start_time" in data: data["start_time"] = data["start_time"].isoformat()
            if "end_time" in data: data["end_time"] = data["end_time"].isoformat()
            
            response = self.client.table("appointments").update(data).eq(
                "id", str(appointment_id)
            ).execute()
            
            if response.data:
                return Appointment(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error updating appointment: {e}")
            return None

    # ==================== CALL LOG OPERATIONS ====================
    
    async def create_call_log(self, log_data: CallLogCreate) -> Optional[CallLog]:
        """Create a new call log entry."""
        try:
            data = log_data.model_dump()
            if data.get("client_id"):
                data["client_id"] = str(data["client_id"])
            
            response = self.client.table("call_logs").insert(data).execute()
            
            if response.data:
                return CallLog(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error creating call log: {e}")
            return None


# Singleton instance
db_service = DatabaseService()