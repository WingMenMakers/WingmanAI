import os
import json
from datetime import datetime, timezone, timedelta
from google.oauth2.credentials import Credentials # Keep for type hinting
from google.auth.transport.requests import Request # Keep for internal Creds use if needed, but not for refresh
from googleapiclient.discovery import build
from typing import Any, List, Dict, Optional # Import typing modules

# REMOVE: load_dotenv()

class GoogleCalendarTool:
    SCOPES = ["https://www.googleapis.com/auth/calendar"] 
    CALENDAR_ID = "primary"
    DEFAULT_TIMEZONE = "Asia/Kolkata"

    # 2. CRITICAL: Accept Credentials object
    def __init__(self, credentials: Credentials):
        """Initialize with a guaranteed valid Credentials object."""
        self.credentials = credentials
        self.service = self._get_service()

    # 3. CRITICAL: Replace authenticate() with simplified service getter
    def _get_service(self):
        """Build the Google Calendar API service using the provided Credentials."""
        try:
            return build("calendar", "v3", credentials=self.credentials)
        except Exception as e:
            raise Exception(f"Error building Calendar service: {e}")
    
    def create_event(self, event_name: str, start_time: str, end_time: str) -> Dict[str, Any]:
        """Creates a new calendar event. Returns the raw event dictionary."""
        event = {
            "summary": event_name,
            "start": {"dateTime": start_time, "timeZone": self.DEFAULT_TIMEZONE},
            "end": {"dateTime": end_time, "timeZone": self.DEFAULT_TIMEZONE},
        }
        try:
            created_event = self.service.events().insert(calendarId=self.CALENDAR_ID, body=event).execute()
            return created_event
        except Exception as e:
            raise Exception(f"Calendar API error during creation: {str(e)}")
        
    def update_event(self, event_name: str, new_start_time: str, new_end_time: str, event_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Updates an existing calendar event by ID or Name.
        If event_id is missing, looks up the event by name in the next 7 days.
        """
        # 1. Resolve ID
        if event_id:
            match = {"event_id": event_id}
        else:
            # Look ahead 7 days to find the event by name
            now = datetime.now(timezone.utc)
            events = self.extract_schedule(now.isoformat(), (now + timedelta(days=7)).isoformat()) 
            match = next((e for e in events if e["event_name"].lower() == event_name.lower()), None)

        if not match:
            return None
        
        updated_event_body = {
            "summary": event_name, 
            "start": {"dateTime": new_start_time, "timeZone": self.DEFAULT_TIMEZONE},
            "end": {"dateTime": new_end_time, "timeZone": self.DEFAULT_TIMEZONE},
        }

        try:
            result = self.service.events().patch(
                calendarId=self.CALENDAR_ID,
                eventId=match.get("event_id"),
                body=updated_event_body
            ).execute()
            return result
        except Exception as e:
             raise Exception(f"Calendar API error during update: {str(e)}")
        
    def extract_schedule(self, start_time: str, end_time: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Fetch events in a date range (ISO format). 
        """
        try:
            start_dt = datetime.fromisoformat(start_time)
            end_dt = datetime.fromisoformat(end_time) if end_time else start_dt + timedelta(days=7) 

            # Convert to UTC for API query standardization
            time_min = start_dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
            time_max = end_dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')

            events_result = (
                self.service.events()
                .list(
                    calendarId=self.CALENDAR_ID,
                    timeMin=time_min,
                    timeMax=time_max,
                    maxResults=50,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            events = events_result.get("items", [])
            
            if not events:
                return [] 

            return [
                {
                    "event_name": event.get("summary", "Unnamed Event"),
                    "start_time": event["start"].get("dateTime", event["start"].get("date")), 
                    "end_time": event["end"].get("dateTime", event["end"].get("date")),
                    "event_id": event["id"],
                    "status": event.get("status")
                }
                for event in events
            ]
        except Exception as e:
            raise Exception(f"Calendar API error during extraction: {str(e)}")

    def delete_event(self, event_input: str | Dict[str, Any]) -> bool:
        """
        Deletes a Google Calendar event by name (string) or full detail (dict).
        """
        # Fetch 7 day window for lookup
        now = datetime.now(timezone.utc)
        events = self.extract_schedule(now.isoformat(), (now + timedelta(days=7)).isoformat()) 
        matches = []
        
        if isinstance(event_input, str):
            matches = [e for e in events if e["event_name"].lower() == event_input.lower()]
        elif isinstance(event_input, dict):
            name = event_input.get("event_name", "").lower()
            start = event_input.get("start_time")
            matches = [
                 e for e in events
                 if e["event_name"].lower() == name and e["start_time"] == start
            ]
        
        if not matches:
            return False 

        try:
            # Delete all matches (usually just one)
            for event in matches:
                self.service.events().delete(calendarId=self.CALENDAR_ID, eventId=event["event_id"]).execute()
            return True
        except Exception as e:
            raise Exception(f"Calendar API error during deletion: {str(e)}")

    def calculate_one_hour_end_time(self, start_time_iso: str) -> str:
        """
        Calculates the time one hour after the given ISO 8601 start time.
        """
        try:
            if len(start_time_iso) <= 10:
                raise ValueError("Start time must be a full ISO 8601 datetime string.")
                
            start_dt = datetime.fromisoformat(start_time_iso)
            end_dt = start_dt + timedelta(hours=1)
            
            return end_dt.isoformat()
        
        except Exception as e:
            raise Exception(f"Time calculation error: {str(e)}")
        