"""
Calendly integration tool for Danny AI.
Handles appointment scheduling via Calendly API.
"""

import httpx
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from ..config import get_config


class AppointmentType(Enum):
    """Types of dental appointments."""
    CLEANING = "cleaning"
    CHECKUP = "checkup"
    CONSULTATION = "consultation"
    EMERGENCY = "emergency"
    FOLLOWUP = "followup"


@dataclass
class TimeSlot:
    """Represents an available time slot."""
    start_time: datetime
    end_time: datetime
    scheduling_url: str


@dataclass
class ScheduledAppointment:
    """Represents a scheduled appointment."""
    uri: str
    name: str
    email: str
    start_time: datetime
    end_time: datetime
    status: str
    event_type: str
    cancel_url: Optional[str] = None
    reschedule_url: Optional[str] = None


class CalendlyClient:
    """Client for interacting with Calendly API."""

    def __init__(self):
        self.config = get_config().calendly
        self.base_url = self.config.base_url
        self.headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        self._user_uri: Optional[str] = None
        self._event_types: Optional[list] = None

    async def _get_user_uri(self) -> str:
        """Get the current user's URI."""
        if self._user_uri:
            return self._user_uri

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/users/me",
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            self._user_uri = data["resource"]["uri"]
            return self._user_uri

    async def get_event_types(self) -> list[dict]:
        """Get all event types (appointment types) for the user."""
        if self._event_types:
            return self._event_types

        user_uri = await self._get_user_uri()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/event_types",
                headers=self.headers,
                params={"user": user_uri, "active": "true"}
            )
            response.raise_for_status()
            data = response.json()
            self._event_types = data.get("collection", [])
            return self._event_types

    async def get_available_times(
        self,
        event_type_uri: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> list[TimeSlot]:
        """Get available time slots for an event type."""
        if not start_date:
            start_date = datetime.utcnow()
        if not end_date:
            end_date = start_date + timedelta(days=7)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/event_type_available_times",
                headers=self.headers,
                params={
                    "event_type": event_type_uri,
                    "start_time": start_date.isoformat() + "Z",
                    "end_time": end_date.isoformat() + "Z"
                }
            )
            response.raise_for_status()
            data = response.json()

        slots = []
        for item in data.get("collection", []):
            slots.append(TimeSlot(
                start_time=datetime.fromisoformat(item["start_time"].replace("Z", "+00:00")),
                end_time=datetime.fromisoformat(item["start_time"].replace("Z", "+00:00")) + timedelta(minutes=30),
                scheduling_url=item.get("scheduling_url", "")
            ))
        return slots

    async def get_scheduled_events(
        self,
        min_start_time: Optional[datetime] = None,
        max_start_time: Optional[datetime] = None,
        status: str = "active"
    ) -> list[ScheduledAppointment]:
        """Get scheduled appointments."""
        user_uri = await self._get_user_uri()
        
        params = {
            "user": user_uri,
            "status": status
        }
        
        if min_start_time:
            params["min_start_time"] = min_start_time.isoformat() + "Z"
        if max_start_time:
            params["max_start_time"] = max_start_time.isoformat() + "Z"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/scheduled_events",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            data = response.json()

        appointments = []
        for event in data.get("collection", []):
            appointments.append(ScheduledAppointment(
                uri=event["uri"],
                name=event.get("name", ""),
                email="",  # Need to fetch invitees for email
                start_time=datetime.fromisoformat(event["start_time"].replace("Z", "+00:00")),
                end_time=datetime.fromisoformat(event["end_time"].replace("Z", "+00:00")),
                status=event["status"],
                event_type=event.get("event_type", ""),
                cancel_url=event.get("cancellation", {}).get("cancel_url"),
                reschedule_url=event.get("reschedule_url")
            ))
        return appointments

    async def create_scheduling_link(self, event_type_uri: str) -> str:
        """
        Get the scheduling link for an event type.
        Note: Calendly doesn't allow direct booking via API for free accounts.
        Returns the scheduling URL for the patient to book.
        """
        event_types = await self.get_event_types()
        for et in event_types:
            if et["uri"] == event_type_uri:
                return et.get("scheduling_url", "")
        return ""

    async def find_event_type_by_name(self, name_keywords: list[str]) -> Optional[dict]:
        """Find an event type by matching keywords in the name."""
        event_types = await self.get_event_types()
        
        for et in event_types:
            et_name = et.get("name", "").lower()
            for keyword in name_keywords:
                if keyword.lower() in et_name:
                    return et
        return None


class CalendlyTool:
    """
    Tool wrapper for Danny to interact with Calendly.
    Provides a simplified interface for the AI agent.
    """

    def __init__(self):
        self.client = CalendlyClient()

    async def list_appointment_types(self) -> str:
        """List available appointment types for the practice."""
        try:
            event_types = await self.client.get_event_types()
            
            if not event_types:
                return "No appointment types are currently configured. Please contact the office directly."
            
            result = "Available appointment types:\n"
            for i, et in enumerate(event_types, 1):
                duration = et.get("duration", 30)
                name = et.get("name", "Appointment")
                result += f"{i}. {name} ({duration} minutes)\n"
            
            return result
        except Exception as e:
            return f"I'm having trouble accessing the scheduling system. Error: {str(e)}"

    async def check_availability(
        self,
        appointment_type: str,
        preferred_date: Optional[str] = None
    ) -> str:
        """Check available time slots for a specific appointment type."""
        try:
            # Find the matching event type
            keywords = appointment_type.lower().split()
            event_type = await self.client.find_event_type_by_name(keywords)
            
            if not event_type:
                return f"I couldn't find an appointment type matching '{appointment_type}'. Let me list the available types for you."
            
            # Parse preferred date or use next 7 days
            start_date = datetime.utcnow()
            if preferred_date:
                try:
                    start_date = datetime.fromisoformat(preferred_date)
                except ValueError:
                    pass
            
            end_date = start_date + timedelta(days=7)
            
            # Get available times
            slots = await self.client.get_available_times(
                event_type["uri"],
                start_date,
                end_date
            )
            
            if not slots:
                return f"I don't see any available slots for {event_type['name']} in the next 7 days. Would you like me to check further out or add you to our waitlist?"
            
            result = f"Available times for {event_type['name']}:\n"
            for i, slot in enumerate(slots[:5], 1):  # Show first 5 slots
                time_str = slot.start_time.strftime("%A, %B %d at %I:%M %p")
                result += f"{i}. {time_str}\n"
            
            if len(slots) > 5:
                result += f"\n...and {len(slots) - 5} more slots available."
            
            result += f"\n\nTo book, please visit: {event_type.get('scheduling_url', 'our booking page')}"
            
            return result
        except Exception as e:
            return f"I encountered an issue checking availability: {str(e)}"

    async def get_booking_link(self, appointment_type: str) -> str:
        """Get the direct booking link for an appointment type."""
        try:
            keywords = appointment_type.lower().split()
            event_type = await self.client.find_event_type_by_name(keywords)
            
            if not event_type:
                # Return general scheduling page
                user_uri = await self.client._get_user_uri()
                # Extract username from URI for scheduling URL
                return "Please visit our scheduling page to book an appointment."
            
            scheduling_url = event_type.get("scheduling_url", "")
            if scheduling_url:
                return f"You can book your {event_type['name']} appointment here: {scheduling_url}"
            else:
                return "I'll need to transfer you to our staff to complete the booking."
        except Exception as e:
            return f"I'm having trouble getting the booking link: {str(e)}"

    async def get_upcoming_appointments(self, patient_email: Optional[str] = None) -> str:
        """Get upcoming appointments (for staff use or patient lookup)."""
        try:
            appointments = await self.client.get_scheduled_events(
                min_start_time=datetime.utcnow(),
                max_start_time=datetime.utcnow() + timedelta(days=30)
            )
            
            if not appointments:
                return "No upcoming appointments found in the next 30 days."
            
            result = "Upcoming appointments:\n"
            for i, apt in enumerate(appointments[:10], 1):
                time_str = apt.start_time.strftime("%A, %B %d at %I:%M %p")
                result += f"{i}. {apt.name or 'Appointment'} - {time_str}\n"
            
            return result
        except Exception as e:
            return f"I couldn't retrieve the appointments: {str(e)}"


# Singleton instance
_calendly_tool: Optional[CalendlyTool] = None


def get_calendly_tool() -> CalendlyTool:
    """Get the singleton Calendly tool instance."""
    global _calendly_tool
    if _calendly_tool is None:
        _calendly_tool = CalendlyTool()
    return _calendly_tool
