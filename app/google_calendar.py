"""Google Calendar integration and token management utilities.

This module provides helpers for:
- Refreshing expired Google OAuth tokens
- Making authenticated calls to Google Calendar API
- Finding available time slots
- Creating/modifying calendar events
"""

import requests
from datetime import datetime, timedelta, timezone
from flask import current_app
from app.extensions import db


class TokenRefreshError(Exception):
    """Raised when token refresh fails."""
    pass


def ensure_valid_token(user):
    """Ensure user has a valid Google access token, refreshing if necessary.
    
    Args:
        user: User model instance with google_access_token, google_refresh_token, 
              and google_token_expires_at fields
              
    Returns:
        str: Valid access token
        
    Raises:
        TokenRefreshError: If token refresh fails or no refresh token available
    """
    # Check if token is expired (with 5-minute buffer)
    now = datetime.utcnow()
    buffer = timedelta(minutes=5)
    
    if user.google_token_expires_at and user.google_token_expires_at > (now + buffer):
        # Token is still valid
        return user.google_access_token
    
    # Token is expired or missing, need to refresh
    if not user.google_refresh_token:
        raise TokenRefreshError("No refresh token available")
    
    current_app.logger.info(f"Refreshing Google token for user {user.id}")
    
    # Call Google's token endpoint to refresh
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        'client_id': current_app.config.get('GOOGLE_CLIENT_ID'),
        'client_secret': current_app.config.get('GOOGLE_CLIENT_SECRET'),
        'refresh_token': user.google_refresh_token,
        'grant_type': 'refresh_token'
    }
    
    try:
        response = requests.post(token_url, data=data, timeout=10)
        response.raise_for_status()
        token_data = response.json()
        
        # Update user's tokens
        user.google_access_token = token_data['access_token']
        
        # Calculate expiry (expires_in is in seconds)
        expires_in = token_data.get('expires_in', 3600)
        user.google_token_expires_at = now + timedelta(seconds=expires_in)
        
        # Google may return a new refresh token
        if 'refresh_token' in token_data:
            user.google_refresh_token = token_data['refresh_token']
        
        db.session.commit()
        current_app.logger.info(f"Successfully refreshed token for user {user.id}")
        
        return user.google_access_token
        
    except requests.RequestException as e:
        current_app.logger.error(f"Token refresh failed for user {user.id}: {str(e)}")
        raise TokenRefreshError(f"Failed to refresh token: {str(e)}")
    except KeyError as e:
        current_app.logger.error(f"Invalid token response for user {user.id}: {str(e)}")
        raise TokenRefreshError(f"Invalid token response: {str(e)}")
    except Exception as e:
        # Catch any other exception (including those raised by tests/mocks)
        current_app.logger.error(f"Token refresh unexpected error for user {user.id}: {str(e)}")
        raise TokenRefreshError(f"Failed to refresh token: {str(e)}")


def make_calendar_request(user, method, endpoint, **kwargs):
    """Make an authenticated request to Google Calendar API.
    
    Args:
        user: User model instance
        method: HTTP method ('GET', 'POST', etc.)
        endpoint: Calendar API endpoint (e.g., 'calendars/primary/events')
        **kwargs: Additional arguments passed to requests
        
    Returns:
        requests.Response: API response
        
    Raises:
        TokenRefreshError: If token refresh fails
    """
    access_token = ensure_valid_token(user)
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    if 'headers' in kwargs:
        headers.update(kwargs['headers'])
    kwargs['headers'] = headers
    
    url = f"https://www.googleapis.com/calendar/v3/{endpoint}"
    
    return requests.request(method, url, timeout=30, **kwargs)


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
    def _to_rfc3339_z(dt: datetime) -> str:
        """Convert datetime to RFC3339 string with 'Z' for UTC.

        Handles both naive and timezone-aware datetimes.
        """
        if dt.tzinfo is None:
            # naive -> assume UTC
            return dt.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')
        # aware -> convert to UTC and emit Z
        return dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')

    if not start_time:
        start_time = datetime.utcnow()
    if not end_time:
        end_time = start_time + timedelta(days=7)

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
    # Get existing events
    events = get_events(user, start_date, end_date)
    
    # Extract busy periods
    busy_periods = []
    for event in events:
        start = event.get('start', {})
        end = event.get('end', {})
        
        if 'dateTime' in start and 'dateTime' in end:
            start_dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))
            busy_periods.append((start_dt, end_dt))
    
    # Find free slots
    available_slots = []
    current_time = start_date.replace(hour=working_hours[0], minute=0, second=0, microsecond=0)
    end_of_search = end_date.replace(hour=working_hours[1], minute=0, second=0, microsecond=0)
    
    slot_duration = timedelta(minutes=duration_minutes)
    
    while current_time + slot_duration <= end_of_search:
        # Check if this slot conflicts with any busy period
        slot_end = current_time + slot_duration
        
        is_free = True
        for busy_start, busy_end in busy_periods:
            if (current_time < busy_end and slot_end > busy_start):
                is_free = False
                break
        
        if is_free:
            available_slots.append({
                'start': current_time,
                'end': slot_end
            })
        
        # Move to next 30-minute slot
        current_time += timedelta(minutes=30)
        
        # Skip to next day if we're past working hours
        if current_time.hour >= working_hours[1]:
            current_time = current_time.replace(hour=working_hours[0], minute=0) + timedelta(days=1)
    
    return available_slots


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
    event_data = {
        'summary': title,
        'description': description,
        'start': {
            'dateTime': start_time.isoformat() + 'Z',
            'timeZone': 'UTC'
        },
        'end': {
            'dateTime': end_time.isoformat() + 'Z', 
            'timeZone': 'UTC'
        }
    }
    
    if attendees:
        event_data['attendees'] = [{'email': email} for email in attendees]
    
    response = make_calendar_request(
        user, 'POST', 'calendars/primary/events', 
        json=event_data
    )
    response.raise_for_status()
    
    return response.json()


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