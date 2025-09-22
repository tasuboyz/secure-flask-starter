"""Google Calendar integration and token management utilities.

This module provides helpers for:
- Refreshing expired Google OAuth tokens
- Making authenticated calls to Google Calendar API
- Finding available time slots
- Creating/modifying calendar events
"""

import requests
from datetime import datetime, timedelta, timezone
try:
    # Python 3.9+ zoneinfo for IANA tz names
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None
from flask import current_app
from app.extensions import db


class TokenRefreshError(Exception):
    """Raised when token refresh fails."""
    pass


class CalendarPermissionError(Exception):
    """Raised when the access token lacks required calendar scopes.

    Attributes:
        message: human-readable message
        body: raw response body from Google (if available)
    """
    def __init__(self, message="Insufficient calendar permissions", body=None):
        super().__init__(message)
        self.body = body


def ensure_valid_token(user):
    """Ensure user has a valid Google access token, delegating to TokenManager.

    Kept for backward compatibility; now uses app.services.google_token.TokenManager.
    """
    # Lazy import to avoid circulars and keep old import path stable in tests
    try:
        from app.services.google_token import TokenManager, TokenRefreshError as _SvcTokenRefreshError
    except Exception:
        # If the service layer is unavailable, re-raise using local error type
        raise TokenRefreshError("Token service not available")

    try:
        manager = TokenManager(user)
        return manager.ensure_valid_token()
    except _SvcTokenRefreshError as e:
        # Normalize to this module's TokenRefreshError to avoid breaking callers/tests
        raise TokenRefreshError(str(e))


def make_calendar_request(user, method, endpoint, **kwargs):
    """Make an authenticated request to Google Calendar API.

    Backward-compatible facade that now uses GoogleCalendarClient.
    """
    try:
        from app.services.google_client import GoogleCalendarClient, CalendarPermissionError as _SvcPermissionError
    except Exception:
        # Hard failure if client layer is missing
        raise

    client = GoogleCalendarClient(user)
    try:
        return client.request(method, endpoint, **kwargs)
    except _SvcPermissionError as e:
        # Re-wrap to this module's CalendarPermissionError to keep imports stable
        raise CalendarPermissionError(str(e), body=getattr(e, 'body', None))


def get_primary_calendar_timezone(user) -> dict:
    """Best-effort timezone without calling Google APIs.

    Eliminates network calls to avoid ACCESS_TOKEN_SCOPE_INSUFFICIENT when
    the token lacks broad scopes. Returns a dict with:
      - timezone: str (IANA name when possible, else 'UTC')
      - permission_error: always False (no Google call is made)
      - error_body: None

    Heuristics:
      1) Use server local timezone name if available
      2) Fallback to UTC
    """
    # Try to get the system local timezone name or offset
    try:
        local_tz = datetime.now().astimezone().tzinfo
        if hasattr(local_tz, 'key') and isinstance(local_tz.key, str):
            # zoneinfo ZoneInfo provides .key (e.g., 'Europe/Rome')
            return {'timezone': local_tz.key, 'permission_error': False, 'error_body': None}
        # Fallback to tzname (non-IANA in some environments)
        tzname = datetime.now().astimezone().tzname()
        if isinstance(tzname, str) and tzname:
            return {'timezone': tzname, 'permission_error': False, 'error_body': None}
    except Exception:
        pass

    return {'timezone': 'UTC', 'permission_error': False, 'error_body': None}


def _tzinfo_from_name(tz_name: str):
    """Return a tzinfo for an IANA timezone name or a UTC±HH:MM hint.

    Falls back to UTC on failure.
    """
    if not tz_name:
        return timezone.utc

    # Accept dict-like input where tz_name may be a dict
    try:
        if isinstance(tz_name, dict):
            tz_name = tz_name.get('timezone') or tz_name.get('tz') or ''
    except Exception:
        pass

    # Handle simple UTC offset hints like 'UTC+02:00' or 'UTC-05:30'
    if isinstance(tz_name, str) and tz_name.upper().startswith('UTC'):
        # Exact 'UTC' fallback
        if tz_name.strip().upper() == 'UTC':
            return timezone.utc
        # Parse offset
        try:
            sign = 1
            rest = tz_name[3:]
            if rest.startswith('+'):
                sign = 1
                rest = rest[1:]
            elif rest.startswith('-'):
                sign = -1
                rest = rest[1:]
            if ':' in rest:
                hours_str, mins_str = rest.split(':', 1)
                hours = int(hours_str)
                mins = int(mins_str)
            else:
                hours = int(rest)
                mins = 0
            return timezone(timedelta(hours=sign * hours, minutes=sign * mins))
        except Exception:
            return timezone.utc

    # Try ZoneInfo for IANA names
    if ZoneInfo is not None and isinstance(tz_name, str):
        try:
            return ZoneInfo(tz_name)
        except Exception:
            # Try dateutil.tz as a softer fallback (not required dependency)
            # Skip optional dateutil dependency to avoid import issues; continue fallbacks
            # As a last resort, use the system local timezone (helps dev envs without zoneinfo)
            try:
                return datetime.now().astimezone().tzinfo
            except Exception:
                return timezone.utc

    return timezone.utc


def get_events(user, start_time=None, end_time=None, max_results=10):
    """Get events from user's primary calendar.
    
    Args:
        user: User model instance
        start_time: datetime for range start (default: now)
        end_time: datetime for range end (default: 7 days from now)
        max_results: maximum number of events to return
        
    Returns:
        list: List of event dictionaries
    """
    # Interpret naive datetimes as UTC to avoid requiring extra permissions
    cal_tz_name = 'UTC'

    def _to_rfc3339_z(dt: datetime) -> str:
        """Convert datetime to RFC3339 string (UTC 'Z').

        If dt is naive, interpret it in the user's calendar timezone then
        convert to UTC for the API call. If dt is aware, convert to UTC.
        """
        if dt.tzinfo is None:
            tz = _tzinfo_from_name(cal_tz_name)
            try:
                # Attach timezone without changing wall time
                dt = dt.replace(tzinfo=tz)
            except Exception:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
        # aware -> convert to UTC and emit Z
        return dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')

    if not start_time:
        start_time = datetime.utcnow()
    if not end_time:
        end_time = start_time + timedelta(days=7)

    # Delegate to CalendarService for domain logic
    try:
        from app.services.calendar_service import CalendarService
    except Exception:
        # Fallback to original implementation if service not present
        params = {
            'timeMin': _to_rfc3339_z(start_time),
            'timeMax': _to_rfc3339_z(end_time),
            'maxResults': max_results,
            'singleEvents': True,
            'orderBy': 'startTime'
        }
        response = make_calendar_request(user, 'GET', 'calendars/primary/events', params=params)
        response.raise_for_status()
        return response.json().get('items', [])

    svc = CalendarService(user)
    return svc.get_events(start_time, end_time, max_results)


def find_available_slots(user, start_date, end_date, duration_minutes=30, working_hours=(9, 17)):
    """Find available time slots in user's calendar.
    
    Args:
        user: User model instance
        start_date: datetime for search start
        end_date: datetime for search end  
        duration_minutes: required slot duration
        working_hours: tuple of (start_hour, end_hour) in 24h format
        
    Returns:
        list: List of available slots as {'start': datetime, 'end': datetime}
    """
    try:
        from app.services.calendar_service import CalendarService
    except Exception:
        # Fall back to old implementation if service missing
        events = get_events(user, start_date, end_date)
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

    svc = CalendarService(user)
    return svc.find_available_slots(start_date, end_date, duration_minutes, working_hours)


def create_event(user, start_time, end_time, title, description="", attendees=None):
    """Create a new calendar event.
    
    Args:
        user: User model instance
        start_time: datetime for event start
        end_time: datetime for event end
        title: str event title
        description: str event description
        attendees: list of email addresses
        
    Returns:
        dict: Created event data from Google Calendar API
    """
    # Use UTC when creating events to avoid Google timezone lookups
    cal_tz = 'UTC'

    def _to_rfc3339_with_tz(dt: datetime, tz_name: str) -> str:
        # Ensure dt is represented in the calendar timezone before serializing.
        tz = _tzinfo_from_name(tz_name)
        try:
            if dt.tzinfo is None:
                # Interpret naive as calendar timezone
                dt = dt.replace(tzinfo=tz)
            else:
                # Convert any aware datetime (e.g., UTC) into calendar timezone
                try:
                    dt = dt.astimezone(tz)
                except Exception:
                    # If astimezone fails, fall back to attaching tz
                    dt = dt.replace(tzinfo=tz)
        except Exception:
            # Last-resort: ensure UTC
            dt = dt.replace(tzinfo=timezone.utc)

        # Return an ISO string with offset (Google accepts ISO with offset)
        return dt.isoformat()

    event_data = {
        'summary': title,
        'description': description,
        'start': {
            'dateTime': _to_rfc3339_with_tz(start_time, cal_tz),
            'timeZone': cal_tz
        },
        'end': {
            'dateTime': _to_rfc3339_with_tz(end_time, cal_tz),
            'timeZone': cal_tz
        }
    }
    
    if attendees:
        event_data['attendees'] = [{'email': email} for email in attendees]
    
    try:
        from app.services.calendar_service import CalendarService
    except Exception:
        response = make_calendar_request(
            user, 'POST', 'calendars/primary/events', json=event_data
        )
        response.raise_for_status()
        return response.json()

    svc = CalendarService(user)
    return svc.create_event(start_time, end_time, title, description, attendees)


def get_events_for_date(user, date):
    """
    Get all events for a specific date.
    
    Args:
        user: User object with Google tokens
        date: Date object for the target date
        
    Returns:
        list: List of events for the specified date
    """
    # Convert date to datetime range (start of day to end of day)
    start_datetime = datetime.combine(date, datetime.min.time())
    end_datetime = datetime.combine(date, datetime.max.time())
    
    # Get events for the date range
    events = get_events(user, start_datetime, end_datetime)
    
    return events


def delete_event(user, event_id):
    """Delete an event from the user's primary calendar.

    Returns True if deletion succeeded (204/200), False if not found or could
    not be deleted. Raises TokenRefreshError on auth problems or requests
    exceptions for other failures.
    """
    try:
        resp = make_calendar_request(user, 'DELETE', f'calendars/primary/events/{event_id}')
        # Google Calendar returns 204 No Content on success
        if resp.status_code in (200, 204):
            return True
        # If not successful, try to raise for a clearer exception to be handled upstream
        resp.raise_for_status()
        return True
    except TokenRefreshError:
        # Propagate token refresh errors to callers
        raise
    except Exception:
        # For other errors return False so callers can surface a 4xx/5xx message
        return False