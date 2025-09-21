"""Calendar API blueprint for handling calendar operations."""

from flask import Blueprint, request, jsonify, render_template, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import json
import logging

from app.google_calendar import (
    ensure_valid_token, TokenRefreshError,
    get_events, find_available_slots, create_event, get_events_for_date
)

logger = logging.getLogger(__name__)

bp = Blueprint('calendar', __name__, url_prefix='/calendar')


@bp.before_request
def ensure_api_auth():
    """Return JSON 401 for unauthenticated API calls to this blueprint.

    This prevents Flask-Login from redirecting XHR/API requests to the HTML
    login page which causes client-side JSON parse errors.
    """
    # Allow static and OPTIONS
    if request.method == 'OPTIONS':
        return None
    try:
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
    except Exception:
        # If current_user is not set for any reason, return auth error
        return jsonify({'error': 'Authentication required'}), 401


@bp.route('/connect-status')
@login_required
def connect_status():
    """Check if user has connected their Google Calendar."""
    return jsonify({
        'connected': current_user.google_calendar_connected,
        'has_tokens': bool(current_user.google_access_token)
    })


@bp.route('/events')
@login_required
def list_events():
    """Get user's calendar events."""
    current_app.logger.info(f'User {current_user.id} requesting calendar events')
    current_app.logger.info(f'Calendar connected: {current_user.google_calendar_connected}')
    current_app.logger.info(f'Has access token: {bool(current_user.google_access_token)}')
    
    if not current_user.google_calendar_connected:
        return jsonify({'error': 'Google Calendar not connected'}), 400
    
    try:
        # Get optional date range from query parameters
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        
        start_time = None
        end_time = None
        
        if start_str:
            start_time = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
        if end_str:
            end_time = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
        
        current_app.logger.info(f'Fetching events from {start_time} to {end_time}')
        events = get_events(current_user, start_time, end_time)
        current_app.logger.info(f'Found {len(events)} events')
        return jsonify({'events': events})
        
    except TokenRefreshError as e:
        current_app.logger.error(f'Token refresh failed: {str(e)}')
        return jsonify({'error': f'Token refresh failed: {str(e)}'}), 401
    except Exception as e:
        current_app.logger.error(f'Error fetching events: {str(e)}', exc_info=True)
        return jsonify({'error': f'Failed to fetch events: {str(e)}'}), 500


@bp.route('/availability')
@login_required
def get_availability():
    """Find available time slots in user's calendar."""
    if not current_user.google_calendar_connected:
        return jsonify({'error': 'Google Calendar not connected'}), 400
    
    try:
        # Parse query parameters
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        duration = int(request.args.get('duration', 30))  # default 30 minutes
        
        if not start_str or not end_str:
            return jsonify({'error': 'start and end parameters required'}), 400
        start_date = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(end_str.replace('Z', '+00:00'))

        # find_available_slots expects datetimes for start_date and end_date
        slots = find_available_slots(current_user, start_date, end_date, duration)

        # Convert datetime objects to ISO strings for JSON serialization
        for slot in slots:
            # Ensure datetimes are serialized to RFC3339/Z
            if getattr(slot['start'], 'tzinfo', None):
                slot['start'] = slot['start'].astimezone().isoformat().replace('+00:00', 'Z')
            else:
                slot['start'] = slot['start'].isoformat() + 'Z'

            if getattr(slot['end'], 'tzinfo', None):
                slot['end'] = slot['end'].astimezone().isoformat().replace('+00:00', 'Z')
            else:
                slot['end'] = slot['end'].isoformat() + 'Z'

        return jsonify({'available_slots': slots})
        
    except TokenRefreshError as e:
        return jsonify({'error': f'Token refresh failed: {str(e)}'}), 401
    except ValueError as e:
        return jsonify({'error': f'Invalid parameters: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to find availability: {str(e)}'}), 500


@bp.route('/events', methods=['POST'])
@login_required
def create_calendar_event():
    """Create a new calendar event."""
    if not current_user.google_calendar_connected:
        return jsonify({'error': 'Google Calendar not connected'}), 400
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Validate required fields
        required_fields = ['title', 'start', 'end']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Parse datetime strings
        start_time = datetime.fromisoformat(data['start'].replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(data['end'].replace('Z', '+00:00'))
        
        # Optional fields
        description = data.get('description', '')
        attendees = data.get('attendees', [])
        
        # Create the event
        event = create_event(
            current_user,
            start_time,
            end_time,
            data['title'],
            description,
            attendees
        )
        
        return jsonify({'event': event})
        
    except TokenRefreshError as e:
        return jsonify({'error': f'Token refresh failed: {str(e)}'}), 401
    except ValueError as e:
        return jsonify({'error': f'Invalid data: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to create event: {str(e)}'}), 500


@bp.route('/chat', methods=['POST'])
@login_required 
def chat_message():
    """Handle chat messages for calendar assistant with AI integration."""
    if not current_user.google_calendar_connected:
        return jsonify({'error': 'Google Calendar not connected'}), 400
    
    try:
        # Robustly parse JSON body
        try:
            data = request.get_json(force=False, silent=False)
        except Exception as e:
            logger.error(f"Invalid JSON in chat request: {e}")
            return jsonify({'error': 'Invalid JSON body'}), 400

        if not data or not isinstance(data, dict):
            return jsonify({'error': 'Invalid JSON body'}), 400

        message = data.get('message', '')
        if not isinstance(message, str) or not message.strip():
            return jsonify({'error': 'No message provided'}), 400
        message = message.strip()
        
        # Process message with AI assistant
        from app.ai_assistant import process_calendar_message
        intent, ai_response = process_calendar_message(current_user, message)
        
        # Handle different intent actions
        calendar_result = None
        suggestions = []
        
        if intent.action == "create_event" and intent.confidence > 0.6:
            # Try to create the event if we have enough information
            try:
                if intent.start_time and intent.title:
                    # Parse start time
                    start_time = datetime.fromisoformat(intent.start_time.replace('Z', '+00:00'))
                    
                    # Calculate end time
                    if intent.end_time:
                        end_time = datetime.fromisoformat(intent.end_time.replace('Z', '+00:00'))
                    elif intent.duration_minutes:
                        end_time = start_time + timedelta(minutes=intent.duration_minutes)
                    else:
                        end_time = start_time + timedelta(hours=1)  # Default 1 hour
                    
                    # Create the event
                    calendar_result = create_event(
                        current_user,
                        start_time,
                        end_time,
                        intent.title,
                        intent.description or "",
                        intent.participants or []
                    )
                    
                    suggestions.append("Event created successfully! Check your calendar.")
                    
                else:
                    suggestions.append("I need more details to create the event. Please specify the title and time.")
                    
            except Exception as e:
                logger.error(f"Error creating event from AI intent: {e}")
                suggestions.append(f"Failed to create event: {str(e)}")
        
        elif intent.action == "list_events":
            # List events for the specified date or today
            try:
                if intent.date:
                    date_obj = datetime.fromisoformat(intent.date).date()
                else:
                    date_obj = datetime.now().date()

                events = get_events_for_date(current_user, date_obj)
                calendar_result = {'events': events, 'date': date_obj.isoformat()}
                
                if events:
                    suggestions.append(f"Found {len(events)} events for {date_obj}")
                else:
                    suggestions.append(f"No events found for {date_obj}")
                    
            except Exception as e:
                logger.error(f"Error listing events: {e}")
                suggestions.append(f"Failed to list events: {str(e)}")
        
        elif intent.action == "find_slot":
            # Find available time slots
            try:
                if intent.date:
                    date_obj = datetime.fromisoformat(intent.date).date()
                else:
                    date_obj = datetime.now().date()

                duration = intent.duration_minutes or 60  # Default 1 hour
                # Convert date to a datetime range covering working hours
                start_dt = datetime.combine(date_obj, datetime.min.time()).replace(hour=9, minute=0, second=0, microsecond=0)
                end_dt = datetime.combine(date_obj, datetime.min.time()).replace(hour=17, minute=0, second=0, microsecond=0)
                slots = find_available_slots(current_user, start_dt, end_dt, duration)
                calendar_result = {'slots': slots, 'date': date_obj.isoformat(), 'duration': duration}
                
                if slots:
                    suggestions.append(f"Found {len(slots)} available slots of {duration} minutes")
                else:
                    suggestions.append(f"No available slots found for {date_obj}")
                    
            except Exception as e:
                logger.error(f"Error finding slots: {e}")
                suggestions.append(f"Failed to find available slots: {str(e)}")
        
        else:
            # For low confidence or unsupported actions
            suggestions = [
                "Try being more specific about what you want to do",
                "Examples: 'Create meeting tomorrow at 2pm', 'What's on my calendar today?', 'When am I free this week?'"
            ]
            if intent.errors:
                suggestions.extend([f"Issue: {error}" for error in intent.errors])
        
        # Prepare response
        response = {
            'message': ai_response,
            'intent': {
                'action': intent.action,
                'confidence': intent.confidence,
                'title': intent.title,
                'start_time': intent.start_time,
                'end_time': intent.end_time
            },
            'suggestions': suggestions,
            'calendar_result': calendar_result
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'error': f'Chat error: {str(e)}'}), 500