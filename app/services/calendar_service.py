"""Domain service for calendar operations.

This service uses GoogleCalendarClient for HTTP interactions and exposes
higher-level business logic: get_events, create_event, find_available_slots.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

from app.services.google_client import GoogleCalendarClient, CalendarPermissionError
from app.google_calendar import _tzinfo_from_name


class CalendarService:
    def __init__(self, user, http=None):
        self.user = user
        # Only pass an explicit http client when one is provided; otherwise
        # allow GoogleCalendarClient to use its default (requests)
        if http is None:
            self.client = GoogleCalendarClient(user)
        else:
            self.client = GoogleCalendarClient(user, http=http)

    def get_events(self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None, max_results: int = 10) -> List[Dict[str, Any]]:
        """Return list of events using the GoogleCalendarClient.

        Preserves the semantics of the old `get_events` helper.
        """
        # Default range
        if not start_time:
            start_time = datetime.utcnow()
        if not end_time:
            end_time = start_time + timedelta(days=7)

        def _to_rfc3339_z(dt: datetime) -> str:
            if dt.tzinfo is None:
                tz = _tzinfo_from_name('UTC')
                dt = dt.replace(tzinfo=tz)
            return dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')

        params = {
            'timeMin': _to_rfc3339_z(start_time),
            'timeMax': _to_rfc3339_z(end_time),
            'maxResults': max_results,
            'singleEvents': True,
            'orderBy': 'startTime'
        }

        # Prefer the legacy make_calendar_request if available (allows tests to patch it)
        try:
            from app import google_calendar as _gc
            if hasattr(_gc, 'make_calendar_request'):
                resp = _gc.make_calendar_request(self.user, 'GET', 'calendars/primary/events', params=params)
                resp.raise_for_status()
                return resp.json().get('items', [])
        except Exception:
            # If any problem importing/patching, fall back to client
            pass

        resp = self.client.request('GET', 'calendars/primary/events', params=params)
        resp.raise_for_status()
        return resp.json().get('items', [])

    def create_event(self, start_time: datetime, end_time: datetime, title: str, description: str = "", attendees: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create an event via GoogleCalendarClient and return the created event dict."""
        cal_tz = 'UTC'

        def _to_iso_with_tz(dt: datetime, tz_name: str) -> str:
            tz = _tzinfo_from_name(tz_name)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tz)
            else:
                try:
                    dt = dt.astimezone(tz)
                except Exception:
                    dt = dt.replace(tzinfo=tz)
            return dt.isoformat()

        event_data = {
            'summary': title,
            'description': description,
            'start': {
                'dateTime': _to_iso_with_tz(start_time, cal_tz),
                'timeZone': cal_tz
            },
            'end': {
                'dateTime': _to_iso_with_tz(end_time, cal_tz),
                'timeZone': cal_tz
            }
        }
        if attendees:
            event_data['attendees'] = [{'email': e} for e in attendees]

        # Allow tests to patch app.google_calendar.make_calendar_request
        try:
            from app import google_calendar as _gc
            if hasattr(_gc, 'make_calendar_request'):
                resp = _gc.make_calendar_request(self.user, 'POST', 'calendars/primary/events', json=event_data)
                resp.raise_for_status()
                return resp.json()
        except Exception:
            pass

        resp = self.client.request('POST', 'calendars/primary/events', json=event_data)
        resp.raise_for_status()
        return resp.json()

    def find_available_slots(self, start_date: datetime, end_date: datetime, duration_minutes: int = 30, working_hours=(9, 17)) -> List[Dict[str, Any]]:
        """Simple free-slot finder using get_events and naive logic.

        This mirrors the old `find_available_slots` helper.
        """
        events = self.get_events(start_date, end_date, max_results=250)

        busy_periods = []
        for event in events:
            start = event.get('start', {})
            end = event.get('end', {})
            if 'dateTime' in start and 'dateTime' in end:
                start_dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))
                busy_periods.append((start_dt, end_dt))

        available_slots = []
        current_time = start_date.replace(hour=working_hours[0], minute=0, second=0, microsecond=0)
        end_of_search = end_date.replace(hour=working_hours[1], minute=0, second=0, microsecond=0)
        slot_duration = timedelta(minutes=duration_minutes)

        while current_time + slot_duration <= end_of_search:
            slot_end = current_time + slot_duration
            is_free = True
            for busy_start, busy_end in busy_periods:
                if (current_time < busy_end and slot_end > busy_start):
                    is_free = False
                    break
            if is_free:
                available_slots.append({'start': current_time, 'end': slot_end})
            current_time += timedelta(minutes=30)
            if current_time.hour >= working_hours[1]:
                current_time = current_time.replace(hour=working_hours[0], minute=0) + timedelta(days=1)

        return available_slots
