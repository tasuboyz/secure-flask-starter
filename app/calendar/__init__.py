"""Calendar blueprint for Google Calendar integration and AI assistant."""

import logging

from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, url_for
from flask_login import login_required, current_user

from app.google_calendar import (
    delete_event as delete_calendar_event,
    _tzinfo_from_name,
    get_primary_calendar_timezone,
    CalendarPermissionError,
)
from app.services.calendar_service import CalendarService
from app.services.google_client import CalendarPermissionError as ClientCalendarPermissionError

class TokenRefreshError(Exception):
    """Local token refresh error placeholder to avoid hard dependency."""
    pass


logger = logging.getLogger(__name__)

bp = Blueprint('calendar', __name__, url_prefix='/calendar')


@bp.route('/events', methods=['GET'])
@login_required
def get_events_endpoint():
        """Get calendar events for a specific date."""
        if not current_user.google_calendar_connected:
            return jsonify({'error': 'Google Calendar not connected'}), 400

        try:
            date_str = request.args.get('date')
            if date_str:
                try:
                    date_obj = datetime.fromisoformat(date_str).date()
                except ValueError:
                    return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
            else:
                date_obj = datetime.now().date()

            start_dt = datetime.combine(date_obj, datetime.min.time())
            end_dt = datetime.combine(date_obj, datetime.max.time())

            try:
                svc = CalendarService(current_user)
                events = svc.get_events(start_dt, end_dt, max_results=250)
                return jsonify({'events': events, 'date': date_obj.isoformat()})
            except (CalendarPermissionError, ClientCalendarPermissionError) as e:
                logger.error(f"Calendar permission error fetching events: {e}")
                return jsonify({
                    'error': 'Calendar permissions required',
                    'calendar_permission_error': True,
                    'reauthorize_url': url_for('auth.google_calendar_reauthorize', _external=True),
                    'details': getattr(e, 'body', None)
                }), 403
        except Exception as e:
            logger.error(f"Error fetching events: {e}")
            return jsonify({'error': f'Failed to fetch events: {str(e)}'}), 500


@bp.route('/events/range', methods=['GET'])
@login_required
def get_events_range():
        """Get calendar events for a date range."""
        if not current_user.google_calendar_connected:
            return jsonify({'error': 'Google Calendar not connected'}), 400

        try:
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            if not start_date or not end_date:
                return jsonify({'error': 'Both start_date and end_date are required'}), 400

            try:
                start_dt = datetime.fromisoformat(start_date)
                end_dt = datetime.fromisoformat(end_date)
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'}), 400

            try:
                svc = CalendarService(current_user)
                events = svc.get_events(start_dt, end_dt, max_results=1000)
                return jsonify({'events': events, 'start_date': start_dt.isoformat(), 'end_date': end_dt.isoformat()})
            except (CalendarPermissionError, ClientCalendarPermissionError) as e:
                logger.error(f"Calendar permission error fetching events for range: {e}")
                return jsonify({
                    'error': 'Calendar permissions required',
                    'calendar_permission_error': True,
                    'reauthorize_url': url_for('auth.google_calendar_reauthorize', _external=True),
                    'details': getattr(e, 'body', None)
                }), 403
        except TokenRefreshError as e:
            logger.error(f"Token refresh failed: {e}")
            return jsonify({'error': 'Google Calendar authentication expired. Please reconnect.'}), 401
        except Exception as e:
            logger.error(f"Error fetching events: {e}")
            return jsonify({'error': f'Failed to fetch events: {str(e)}'}), 500


@bp.route('/slots', methods=['GET'])
@login_required
def get_available_slots():
        """Find available time slots in the calendar."""
        if not current_user.google_calendar_connected:
            return jsonify({'error': 'Google Calendar not connected'}), 400

        try:
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            duration = int(request.args.get('duration', 60))
            if not start_date or not end_date:
                return jsonify({'error': 'Both start_date and end_date are required'}), 400

            try:
                start_dt = datetime.fromisoformat(start_date)
                end_dt = datetime.fromisoformat(end_date)
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use ISO format'}), 400

            try:
                svc = CalendarService(current_user)
                slots = svc.find_available_slots(start_dt, end_dt, duration)
                return jsonify({'slots': slots, 'start_date': start_dt.isoformat(), 'end_date': end_dt.isoformat(), 'duration_minutes': duration})
            except (CalendarPermissionError, ClientCalendarPermissionError) as e:
                logger.error(f"Calendar permission error finding slots: {e}")
                return jsonify({
                    'error': 'Calendar permissions required',
                    'calendar_permission_error': True,
                    'reauthorize_url': url_for('auth.google_calendar_reauthorize', _external=True),
                    'details': getattr(e, 'body', None)
                }), 403
        except TokenRefreshError as e:
            logger.error(f"Token refresh failed: {e}")
            return jsonify({'error': 'Google Calendar authentication expired. Please reconnect.'}), 401
        except Exception as e:
            logger.error(f"Error finding slots: {e}")
            return jsonify({'error': f'Failed to find available slots: {str(e)}'}), 500


@bp.route('/events', methods=['POST'])
@login_required
def create_event_endpoint():
        """Create a new calendar event."""
        if not current_user.google_calendar_connected:
            return jsonify({'error': 'Google Calendar not connected'}), 400

        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400

            required_fields = ['title', 'start_time', 'end_time']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400

            def _parse_incoming_iso(dt_str: str, client_tz: str = None):
                if not dt_str or not isinstance(dt_str, str):
                    raise ValueError('Invalid datetime')
                if 'Z' in dt_str or (('+' in dt_str and dt_str.rfind('+') > 8) or ('-' in dt_str and dt_str.rfind('-') > 8)):
                    try:
                        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                    except Exception:
                        raise ValueError('Invalid datetime format')

                if client_tz:
                    cal_tz_name = client_tz
                else:
                    try:
                        cal_tz_info = get_primary_calendar_timezone(current_user)
                        cal_tz_name = cal_tz_info.get('timezone') if isinstance(cal_tz_info, dict) else (cal_tz_info or 'UTC')
                    except Exception:
                        cal_tz_name = 'UTC'

                tz = _tzinfo_from_name(cal_tz_name)
                try:
                    naive = datetime.fromisoformat(dt_str)
                except Exception:
                    raise ValueError('Invalid datetime format')
                try:
                    return naive.replace(tzinfo=tz)
                except Exception:
                    return naive.replace(tzinfo=timezone.utc)

            try:
                client_tz = data.get('client_timezone') or None
                if data.get('start_time_iso_with_offset'):
                    start_time = datetime.fromisoformat(data['start_time_iso_with_offset'].replace('Z', '+00:00'))
                else:
                    start_time = _parse_incoming_iso(data['start_time'], client_tz)

                if data.get('end_time_iso_with_offset'):
                    end_time = datetime.fromisoformat(data['end_time_iso_with_offset'].replace('Z', '+00:00'))
                else:
                    end_time = _parse_incoming_iso(data['end_time'], client_tz)
            except ValueError as e:
                return jsonify({'error': str(e)}), 400

            if end_time <= start_time:
                return jsonify({'error': 'End time must be after start time'}), 400

            description = data.get('description', '')
            attendees = data.get('attendees', [])

            try:
                svc = CalendarService(current_user)
                event = svc.create_event(start_time, end_time, data['title'], description, attendees)
                return jsonify({'event': event})
            except (CalendarPermissionError, ClientCalendarPermissionError) as e:
                logger.error(f"Calendar permission error creating event: {e}")
                return jsonify({
                    'error': 'Calendar permissions required',
                    'calendar_permission_error': True,
                    'reauthorize_url': url_for('auth.google_calendar_reauthorize', _external=True),
                    'details': getattr(e, 'body', None)
                }), 403
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

            from app.ai_assistant import create_ai_service_for_user
            ai_service = create_ai_service_for_user(current_user)
            if not ai_service:
                return jsonify({'error': 'AI assistant not configured. Please add your OpenAI API key in settings.'}), 400

            response_text = ai_service.process_chat(message, current_user)
            response_payload = {'response': response_text, 'timestamp': datetime.now().isoformat()}
            logger.debug(f"Chat endpoint returning payload: {response_payload}")
            return jsonify(response_payload)
        except Exception as e:
            logger.error(f"Error in chat endpoint: {e}")
            return jsonify({'error': 'An error occurred processing your message'}), 500


def delete_event(event_id):
        """Delete a calendar event."""
        if not current_user.google_calendar_connected:
            return jsonify({'error': 'Google Calendar not connected'}), 400

        try:
            result = delete_calendar_event(current_user, event_id)
            if result:
                return jsonify({'message': 'Event deleted successfully'})
            else:
                return jsonify({'error': 'Event not found or could not be deleted'}), 404
        except (CalendarPermissionError, ClientCalendarPermissionError) as e:
            logger.error(f"Calendar permission error deleting event: {e}")
            return jsonify({
                'error': 'Calendar permissions required',
                'calendar_permission_error': True,
                'reauthorize_url': url_for('auth.google_calendar_reauthorize', _external=True),
                'details': getattr(e, 'body', None)
            }), 403
        except TokenRefreshError as e:
            logger.error(f"Token refresh failed: {e}")
            return jsonify({'error': 'Google Calendar authentication expired. Please reconnect.'}), 401
        except Exception as e:
            logger.error(f"Error deleting event: {e}")
            return jsonify({'error': f'Failed to delete event: {str(e)}'}), 500
