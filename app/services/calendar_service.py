"""
Google Calendar integration service.
Refactored for non-blocking Async I/O.
"""

import asyncio
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.config import settings
from app.utils.logger import logger


class CalendarService:
    """Service for Google Calendar operations."""
    
    def __init__(self):
        """Initialize Google Calendar service safely."""
        self.service = None
        
        if not os.path.exists(settings.GOOGLE_CREDENTIALS_PATH):
            logger.warning(f"⚠️ Google Credentials file not found at: {settings.GOOGLE_CREDENTIALS_PATH}")
            logger.warning("Calendar features will be disabled.")
            return

        try:
            # Load credentials
            self.credentials = service_account.Credentials.from_service_account_file(
                settings.GOOGLE_CREDENTIALS_PATH,
                scopes=['https://www.googleapis.com/auth/calendar']
            )
            
            # Build service (this is synchronous, so we do it at startup)
            self.service = build('calendar', 'v3', credentials=self.credentials)
            logger.success("✓ Google Calendar service initialized")
        
        except Exception as e:
            logger.error(f"✗ Failed to initialize Calendar service: {e}")
            # We don't raise here to prevent the whole app from crashing on startup
            # The methods below check if self.service exists.

    async def check_availability(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Check calendar availability (Non-blocking)."""
        if not self.service:
            return {"available": False, "error": "Calendar service not configured"}

        try:
            # 1. Define the blocking function
            def _do_fetch():
                return self.service.events().list(
                    calendarId=settings.GOOGLE_CALENDAR_ID,
                    timeMin=start_time.isoformat(),
                    timeMax=end_time.isoformat(),
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()

            # 2. Run it in a separate thread so we don't block Voice Audio
            events_result = await asyncio.to_thread(_do_fetch)
            
            events = events_result.get('items', [])
            
            if not events:
                return {
                    "available": True,
                    "message": "The time slot is open.",
                    "busy_slots": []
                }
            
            # Format busy slots
            busy_slots = []
            for event in events:
                # Handle full-day events (date) vs timed events (dateTime)
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                busy_slots.append({
                    "start": start,
                    "end": end,
                    "summary": event.get('summary', 'Busy')
                })
            
            return {
                "available": False,
                "message": f"Time slot conflict: {len(busy_slots)} existing booking(s).",
                "busy_slots": busy_slots
            }
        
        except Exception as e:
            logger.error(f"Calendar API error: {e}")
            return {"available": False, "error": str(e)}

    async def create_event(
        self,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        attendee_email: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[str]:
        """Create a new calendar event (Non-blocking)."""
        if not self.service:
            return None

        try:
            event_body = {
                'summary': summary,
                'description': description or f"{settings.BUSINESS_NAME} Appointment",
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': settings.BUSINESS_TIMEZONE,
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': settings.BUSINESS_TIMEZONE,
                },
                # Default Reminders: Pop-up 30 mins before
                'reminders': {
                    'useDefault': False,
                    'overrides': [{'method': 'popup', 'minutes': 30}],
                },
            }
            
            if attendee_email:
                event_body['attendees'] = [{'email': attendee_email}]

            # Define blocking call
            def _do_insert():
                return self.service.events().insert(
                    calendarId=settings.GOOGLE_CALENDAR_ID,
                    body=event_body,
                    sendUpdates='all' # Emails the user automatically
                ).execute()

            # Run in thread
            created_event = await asyncio.to_thread(_do_insert)
            
            event_id = created_event['id']
            logger.info(f"Created calendar event: {event_id}")
            return event_id
        
        except Exception as e:
            logger.error(f"Error creating calendar event: {e}")
            return None

    async def update_event(self, event_id: str, **kwargs) -> bool:
        """Update an event (Non-blocking)."""
        if not self.service: return False

        try:
            # 1. Fetch existing event first
            def _do_get():
                return self.service.events().get(
                    calendarId=settings.GOOGLE_CALENDAR_ID,
                    eventId=event_id
                ).execute()
            
            event = await asyncio.to_thread(_do_get)

            # 2. Apply updates
            if 'start_time' in kwargs:
                event['start']['dateTime'] = kwargs['start_time'].isoformat()
            if 'end_time' in kwargs:
                event['end']['dateTime'] = kwargs['end_time'].isoformat()
            if 'summary' in kwargs:
                event['summary'] = kwargs['summary']
            if 'description' in kwargs:
                event['description'] = kwargs['description']

            # 3. Save updates
            def _do_update():
                return self.service.events().update(
                    calendarId=settings.GOOGLE_CALENDAR_ID,
                    eventId=event_id,
                    body=event,
                    sendUpdates='all'
                ).execute()

            await asyncio.to_thread(_do_update)
            logger.info(f"Updated calendar event: {event_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating calendar event: {e}")
            return False

    async def delete_event(self, event_id: str) -> bool:
        """Delete an event (Non-blocking)."""
        if not self.service: return False

        try:
            def _do_delete():
                self.service.events().delete(
                    calendarId=settings.GOOGLE_CALENDAR_ID,
                    eventId=event_id,
                    sendUpdates='all'
                ).execute()

            await asyncio.to_thread(_do_delete)
            logger.info(f"Deleted calendar event: {event_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting event: {e}")
            return False


# Singleton instance
calendar_service = CalendarService()