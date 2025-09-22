"""AI Assistant service for processing natural language calendar requests."""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from flask import current_app, url_for
from dataclasses import dataclass
from app.google_calendar import get_primary_calendar_timezone
from app.services.calendar_service import CalendarService

logger = logging.getLogger(__name__)

# Expose openai module if available so tests can patch app.ai_assistant.openai
try:
    import openai
except Exception:
    openai = None


@dataclass
class CalendarIntent:
    """Represents a parsed calendar intent from user message."""
    action: str  # 'create_event', 'find_slot', 'list_events', 'cancel_event'
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[str] = None  # ISO format
    end_time: Optional[str] = None    # ISO format
    duration_minutes: Optional[int] = None
    date: Optional[str] = None        # For date-based queries
    participants: Optional[List[str]] = None
    location: Optional[str] = None
    confidence: float = 0.0
    raw_message: str = ""
    errors: Optional[List[str]] = None


class AIAssistantService:
    """Service for AI-powered calendar assistance."""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        """Initialize the AI service with OpenAI API key."""
        self.api_key = api_key
        self.model = model
        self._client = None
    
    @property
    def client(self):
        """Modern OpenAI client initialization."""
        if self._client is None:
            try:
                # Prefer the module-level `openai` (so tests can patch app.ai_assistant.openai)
                if openai is not None and hasattr(openai, 'OpenAI'):
                    self._client = openai.OpenAI(api_key=self.api_key)
                else:
                    from openai import OpenAI
                    self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("OpenAI package not installed. Run: pip install openai")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                raise
        return self._client
    
    @property
    def _tools(self):
        """Get tools definition for OpenAI function calling."""
        return self._define_calendar_tools()
    
    def process_chat(self, message: str, user):
        """Process a chat message and return AI response with tool calling support."""
        try:
            # Safely read user preferences (may not exist on older User models)
            language = getattr(user, 'ai_language', None) or getattr(user, 'ai_language_preference', None) or 'English'
            model_name = getattr(user, 'ai_model', None) or getattr(user, 'ai_model_preference', None) or self.model or 'gpt-4o-mini'

            # Debug log incoming request
            try:
                _log_debug('process_chat called for user %s, model=%s, language=%s', getattr(user, 'id', '<anon>'), model_name, language)
                _log_debug('Incoming message: %s', message)
            except Exception:
                logger.debug('Incoming message (logging helper failed)')

            # Detect user's calendar timezone (fall back to UTC)
            try:
                user_tz = get_primary_calendar_timezone(user)
            except Exception:
                user_tz = 'UTC'

            # Build basic prompt for conversation and include user's timezone
            prompt = [
                {
                    "role": "system",
                    "content": f"You are a helpful assistant with access to Google Calendar functions. The user's timezone is {user_tz}. Current time is {datetime.now().isoformat()}. Respond in {language}."
                },
                {
                    "role": "user",
                    "content": message
                }
            ]

            # Make request to OpenAI with tools
            response = self._create_chat_completion(
                model=model_name,
                messages=prompt,
                tools=self._tools
            )
            _log_debug('Raw AI response object/dict: %s', str(response)[:2000])
            
            # Check for tool calls first
            tool_calls = self._find_tool_calls(response)
            _log_debug('Tool calls found: %s', tool_calls)
            if tool_calls:
                # Execute all tool calls
                tool_results = []
                for tool_call in tool_calls:
                    _log_debug('Executing tool call: %s with args: %s', tool_call.get('name'), tool_call.get('arguments'))
                    result = self._execute_tool_call(
                        tool_call['name'], 
                        tool_call['arguments'], 
                        user
                    )
                    _log_debug('Tool result: %s', result)
                    tool_results.append(result)

                # If any tool indicated a calendar permission error, return early with reauthorization hint
                for tr in tool_results:
                    if isinstance(tr, dict) and tr.get('calendar_permission_error'):
                        # Return structured message so the HTTP handler / UI can prompt reauthorization
                        try:
                            msg = "I don't have permission to access your Google Calendar. Please reauthorize the calendar connection."
                            reauth = tr.get('reauthorize_url') or (url_for('auth.google_calendar_reauthorize', _external=True) if 'url_for' in globals() else '/auth/google/calendar/reauthorize')
                        except Exception:
                            msg = "I don't have permission to access your Google Calendar. Please reauthorize the calendar connection."
                            reauth = tr.get('reauthorize_url') if isinstance(tr, dict) else '/auth/google/calendar/reauthorize'
                        # Return a special structured payload that callers can detect
                        return {"error": "calendar_permission_error", "message": msg, "reauthorize_url": reauth}
                
                # Create follow-up request with tool results
                # Add an assistant message indicating progress and include tool results
                # Use 'assistant' role for compatibility with Responses and Chat APIs
                prompt.append({
                    "role": "assistant",
                    "content": f"I'll help you with that. Let me check your calendar..."
                })

                # Some OpenAI APIs expect function/tool call results to be provided as
                # assistant messages. Avoid using a 'function' role here because some
                # models and the Responses API reject it. Provide a structured JSON
                # blob inside the assistant content so both Responses and legacy chat
                # endpoints can consume it.
                try:
                    tool_results_payload = json.dumps(tool_results)
                except Exception:
                    tool_results_payload = str(tool_results)

                prompt.append({
                    "role": "assistant",
                    "content": f"Tool execution results: {tool_results_payload}"
                })
                
                # Get final response from AI
                response = self._create_chat_completion(
                    model=model_name,
                    messages=prompt
                )
                final = self._extract_content(response)
                _log_debug('Final AI response after tools: %s', final)
                return final
            else:
                # No tools called, return direct response
                final = self._extract_content(response)
                _log_debug('Final AI response (no tools): %s', final)
                return final
                
        except Exception as e:
            logger.error(f"Error in process_chat: {e}")
            # Use the resolved language in the error message when possible
            try:
                lang = language
            except Exception:
                lang = getattr(user, 'ai_language', None)

            if lang and isinstance(lang, str) and lang.lower() == 'italian':
                return "Mi dispiace, si è verificato un errore nell'elaborazione della richiesta."
            else:
                return "Sorry, I encountered an error processing your request."
    
    def _define_calendar_tools(self):
        """Define calendar tools that AI can call."""
        return [
            {
                "type": "function",
                "name": "create_calendar_event",
                "description": "Create a new event in the user's Google Calendar",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Event title/summary"
                        },
                        "start_time": {
                            "type": "string",
                            "description": "Event start time in ISO format (e.g., 2025-09-22T15:00:00)"
                        },
                        "end_time": {
                            "type": "string", 
                            "description": "Event end time in ISO format (e.g., 2025-09-22T16:00:00)"
                        },
                        "description": {
                            "type": "string",
                            "description": "Optional event description"
                        },
                        "attendees": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of attendee email addresses"
                        },
                        "location": {
                            "type": "string",
                            "description": "Optional event location"
                        }
                    },
                    "required": ["title", "start_time", "end_time"],
                    "additionalProperties": False
                },
                "strict": True
            },
            {
                "type": "function", 
                "name": "find_free_slots",
                "description": "Find available time slots in the user's calendar",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": "Search start date in ISO format (e.g., 2025-09-22)"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "Search end date in ISO format (e.g., 2025-09-22)"
                        },
                        "duration_minutes": {
                            "type": "integer",
                            "description": "Required duration in minutes (default: 60)"
                        }
                    },
                    "required": ["start_date", "end_date"],
                    "additionalProperties": False
                },
                "strict": True
            },
            {
                "type": "function",
                "name": "get_calendar_events",
                "description": "Get events from the user's calendar for a specific date or date range",
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "Date to get events for in ISO format (e.g., 2025-09-22)"
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Start date for date range search"
                        },
                        "end_date": {
                            "type": "string", 
                            "description": "End date for date range search"
                        }
                    },
                    "additionalProperties": False
                },
                "strict": True
            }
        ]
    
    def _http_fallback(self, **kwargs):
        """HTTP fallback for OpenAI API calls."""
        try:
            import requests
            import os
            api_base = os.environ.get('OPENAI_API_BASE', 'https://api.openai.com')
            url = api_base.rstrip('/') + '/v1/chat/completions'
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            logger.warning('Using HTTP fallback for OpenAI API call')
            resp = requests.post(url, headers=headers, json=kwargs, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"HTTP fallback failed: {e}")
            raise

    def _http_fallback_responses(self, **kwargs):
        """HTTP fallback using the Responses API (/v1/responses)."""
        try:
            import requests
            import os
            api_base = os.environ.get('OPENAI_API_BASE', 'https://api.openai.com')
            url = api_base.rstrip('/') + '/v1/responses'
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            logger.warning('Using HTTP fallback to /v1/responses for OpenAI API call')
            resp = requests.post(url, headers=headers, json=kwargs, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"HTTP responses fallback failed: {e}")
            raise

    def _extract_content(self, response):
        """Extract message content from OpenAI response (handles both object and dict formats)."""
        # Responses API (new): prefer output_text if present
        if hasattr(response, 'output_text'):
            val = getattr(response, 'output_text')
            if isinstance(val, str):
                return val
            try:
                # if it's JSON-like, serialize
                if isinstance(val, (dict, list)):
                    return json.dumps(val)
            except Exception:
                pass

        if isinstance(response, dict) and 'output_text' in response:
            if isinstance(response['output_text'], str):
                return response['output_text']
            try:
                return json.dumps(response['output_text'])
            except Exception:
                pass

        # Responses API dict-style: response['output'] -> list of items with 'content'
        if isinstance(response, dict) and 'output' in response:
            try:
                out = response['output']
                if isinstance(out, list) and out:
                    first = out[0]
                    # content may be list of dicts
                    content = first.get('content') or first.get('text')
                    if isinstance(content, list) and content:
                        # find text pieces
                        for c in content:
                            if isinstance(c, dict) and c.get('type') == 'output_text' and 'text' in c:
                                return c['text']
                        # fallback to first item's text
                        if isinstance(content[0], dict) and 'text' in content[0]:
                            return content[0]['text']
                        if isinstance(content[0], str):
                            return content[0]
                    elif isinstance(content, str):
                        return content
            except Exception:
                pass

        # Chat completions object response
        if hasattr(response, 'choices'):
            try:
                choice = response.choices[0]
                # Safe access to nested message content
                content = None
                if hasattr(choice, 'message'):
                    msg = getattr(choice, 'message')
                    content = getattr(msg, 'content', None)
                # Only return if it's a string or serializable
                if isinstance(content, str):
                    return content
                if content is not None:
                    try:
                        return json.dumps(content)
                    except Exception:
                        return str(content)
            except Exception:
                pass

        # Dict-style chat completions
        if isinstance(response, dict) and 'choices' in response:
            try:
                content = response['choices'][0]['message']['content']
                if isinstance(content, str):
                    return content
                if content is not None:
                    try:
                        return json.dumps(content)
                    except Exception:
                        return str(content)
            except Exception:
                pass
        # Fallback: if the response can be stringified to JSON, return that
        try:
            text = str(response).strip()
            if text.startswith('{') or text.startswith('['):
                return text
        except Exception:
            pass

        raise ValueError(f"Unexpected response format: {type(response)}")

    def _find_tool_calls(self, response):
        """Extract tool calls from OpenAI response."""
        tool_calls = []
        
        # Handle Responses API format (dict-style)
        if isinstance(response, dict) and 'output' in response:
            try:
                for item in response['output']:
                    itype = item.get('type') if isinstance(item, dict) else None
                    # Accept both legacy 'tool_call' and newer 'function_call'
                    if itype in ('tool_call', 'function_call'):
                        name = item.get('name')
                        args = item.get('arguments', {})
                        # arguments may be a JSON string in some Responses outputs
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except Exception:
                                logger.debug('Could not parse tool arguments string; keeping raw')
                        tool_calls.append({'name': name, 'arguments': args or {}})
                    # Sometimes tool calls are nested inside 'content' lists
                    elif 'content' in item and isinstance(item['content'], list):
                        for content_item in item['content']:
                            ctype = content_item.get('type') if isinstance(content_item, dict) else None
                            if ctype in ('tool_call', 'function_call'):
                                name = content_item.get('name')
                                args = content_item.get('arguments', {})
                                if isinstance(args, str):
                                    try:
                                        args = json.loads(args)
                                    except Exception:
                                        logger.debug('Could not parse nested tool arguments string; keeping raw')
                                tool_calls.append({'name': name, 'arguments': args or {}})
            except Exception as e:
                logger.debug(f"Error extracting tool calls: {e}")
        
        # Handle object format (client SDK Response objects)
        if hasattr(response, 'output'):
            try:
                for item in response.output:
                    itype = getattr(item, 'type', None)
                    # The SDK may use 'function_call' for function invocations
                    if itype in ('tool_call', 'function_call'):
                        name = getattr(item, 'name', None)
                        args = getattr(item, 'arguments', None)
                        # If arguments is a JSON string, parse it
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except Exception:
                                logger.debug('Could not parse object tool arguments string; keeping raw')
                        tool_calls.append({'name': name, 'arguments': args or {}})
            except Exception as e:
                logger.debug(f"Error extracting tool calls from object: {e}")
                
        return tool_calls

    def _execute_tool_call(self, tool_name: str, arguments: dict, user) -> dict:
        """Execute a tool call and return the result."""
        try:
            _log_debug('Executing tool %s with arguments: %s for user %s', tool_name, arguments, getattr(user, 'id', '<anon>'))
            if tool_name == "create_calendar_event":
                return self._execute_create_event(arguments, user)
            elif tool_name == "find_free_slots":
                return self._execute_find_slots(arguments, user)
            elif tool_name == "get_calendar_events":
                return self._execute_get_events(arguments, user)
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            # If the error arises from Google Calendar insufficient scopes,
            # detect the CalendarPermissionError or the 'ACCESS_TOKEN_SCOPE_INSUFFICIENT'
            # sentinel returned by google_calendar helpers and return a structured
            # response so the caller (AI flow / HTTP handler) can prompt reauthorization.
            logger.error(f"Tool execution failed for {tool_name}: {e}")
            current_app.logger.debug('Tool execution exception for %s: %s', tool_name, str(e))
            # CalendarPermissionError detection by exception type name (avoid import cycles)
            if e.__class__.__name__ == 'CalendarPermissionError' or 'ACCESS_TOKEN_SCOPE_INSUFFICIENT' in str(e):
                # Provide a standardized response signaling the need to reauthorize
                try:
                    from flask import url_for
                    reauth_url = url_for('auth.google_calendar_reauthorize', _external=True)
                except Exception:
                    reauth_url = '/auth/google/calendar/reauthorize'
                return {"success": False, "error": "ACCESS_TOKEN_SCOPE_INSUFFICIENT", "calendar_permission_error": True, "reauthorize_url": reauth_url}
            return {"error": f"Tool execution failed: {str(e)}"}

    def _execute_create_event(self, args: dict, user) -> dict:
        """Execute create_calendar_event tool."""
        try:
            from datetime import datetime, timezone
            # Parse datetime strings robustly, allowing timezone offsets
            def _parse_iso(dt_str: str):
                if not dt_str:
                    return None
                # If contains Z or explicit offset, parse directly
                if 'Z' in dt_str or ('+' in dt_str and dt_str.rfind('+') > 8) or ('-' in dt_str and dt_str.rfind('-') > 8):
                    try:
                        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                    except Exception:
                        # Last-resort: try to parse without modifications
                        return datetime.fromisoformat(dt_str)

                # No offset present: interpret in user's calendar timezone
                try:
                    cal_tz_info = get_primary_calendar_timezone(user)
                    cal_tz_name = cal_tz_info.get('timezone') if isinstance(cal_tz_info, dict) else (cal_tz_info or 'UTC')
                except Exception:
                    cal_tz_name = 'UTC'

                from app.google_calendar import _tzinfo_from_name
                tz = _tzinfo_from_name(cal_tz_name)
                try:
                    naive = datetime.fromisoformat(dt_str)
                except Exception:
                    return datetime.fromisoformat(dt_str)
                try:
                    return naive.replace(tzinfo=tz)
                except Exception:
                    return naive.replace(tzinfo=timezone.utc)

            start_time = _parse_iso(args.get('start_time'))
            end_time = _parse_iso(args.get('end_time'))

            # Create the event via CalendarService
            svc = CalendarService(user)
            event = svc.create_event(start_time, end_time, args['title'], args.get('description', ''), args.get('attendees', []))
            
            return {
                "success": True,
                "event_id": event.get('id'),
                "title": event.get('summary'),
                "start": event.get('start', {}).get('dateTime'),
                "end": event.get('end', {}).get('dateTime'),
                "html_link": event.get('htmlLink')
            }
        except Exception as e:
            # Propagate calendar permission errors up so the caller can trigger reauthorization
            if e.__class__.__name__ == 'CalendarPermissionError' or 'ACCESS_TOKEN_SCOPE_INSUFFICIENT' in str(e):
                raise
            return {"success": False, "error": str(e)}

    def _execute_find_slots(self, args: dict, user) -> dict:
        """Execute find_free_slots tool."""
        try:
            from datetime import datetime
            start_date = datetime.fromisoformat(args['start_date']).replace(hour=9, minute=0)
            end_date = datetime.fromisoformat(args['end_date']).replace(hour=17, minute=0)
            duration = args.get('duration_minutes', 60)

            svc = CalendarService(user)
            slots = svc.find_available_slots(start_date, end_date, duration)
            
            return {
                "success": True,
                "slots": [
                    {
                        "start": slot['start'].isoformat() if hasattr(slot['start'], 'isoformat') else slot['start'],
                        "end": slot['end'].isoformat() if hasattr(slot['end'], 'isoformat') else slot['end']
                    }
                    for slot in slots[:5]  # Limit to 5 slots
                ],
                "total_found": len(slots)
            }
        except Exception as e:
            if e.__class__.__name__ == 'CalendarPermissionError' or 'ACCESS_TOKEN_SCOPE_INSUFFICIENT' in str(e):
                raise
            return {"success": False, "error": str(e)}

    def _execute_get_events(self, args: dict, user) -> dict:
        """Execute get_calendar_events tool."""
        try:
            from datetime import datetime
            svc = CalendarService(user)
            if 'date' in args:
                # Single date -> fetch events for that day
                date_obj = datetime.fromisoformat(args['date']).date()
                start_dt = datetime.combine(date_obj, datetime.min.time())
                end_dt = datetime.combine(date_obj, datetime.max.time())
                events = svc.get_events(start_dt, end_dt, max_results=250)
            else:
                # Date range
                start_time = datetime.fromisoformat(args.get('start_date', ''))
                end_time = datetime.fromisoformat(args.get('end_date', ''))
                events = svc.get_events(start_time, end_time)
            
            return {
                "success": True,
                "events": [
                    {
                        "title": event.get('summary', 'Untitled'),
                        "start": event.get('start', {}).get('dateTime') or event.get('start', {}).get('date'),
                        "end": event.get('end', {}).get('dateTime') or event.get('end', {}).get('date'),
                        "description": event.get('description', ''),
                        "location": event.get('location', '')
                    }
                    for event in events[:10]  # Limit to 10 events
                ],
                "total_found": len(events)
            }
        except Exception as e:
            if e.__class__.__name__ == 'CalendarPermissionError' or 'ACCESS_TOKEN_SCOPE_INSUFFICIENT' in str(e):
                raise
            return {"success": False, "error": str(e)}

    def _create_chat_completion(self, **kwargs):
        """Modern OpenAI chat completion call.

        Translate legacy parameters (e.g. max_tokens) to newer parameter
        names if required by the API and retry with sensible fallbacks.
        """
        # Prepare payload and translate compatibility keys
        payload = dict(kwargs)

        # Translate legacy param name to Responses API param
        if 'max_tokens' in payload:
            payload['max_output_tokens'] = payload.pop('max_tokens')

        # Translate `messages` -> `input` expected by Responses API
        if 'messages' in payload:
            msgs = payload.pop('messages')
            try:
                # Expecting a list of {'role', 'content'} dicts
                payload['input'] = [
                    {'role': m.get('role', 'user'), 'content': m.get('content') if isinstance(m.get('content'), str) else m.get('content')}
                    for m in msgs
                ]
            except Exception:
                # Fallback: join text parts into a single input string
                payload['input'] = ' '.join([str(m) for m in msgs])

        # Normalize tools: keep only name/description/parameters for Responses API
        if 'tools' in payload:
            tools = payload.pop('tools')
            normalized = []
            for t in tools:
                norm = {}
                if isinstance(t, dict):
                    if 'name' in t:
                        norm['name'] = t['name']
                    if 'description' in t:
                        norm['description'] = t['description']
                    if 'parameters' in t:
                        norm['parameters'] = t['parameters']
                    # Preserve explicit type (e.g., 'function') if provided
                    if 'type' in t:
                        norm['type'] = t['type']
                    # Some tool schemas use 'function' key for legacy compatibility
                    if 'function' in t:
                        norm['function'] = t['function']
                # Ensure a type is present for Responses API
                if 'type' not in norm:
                    norm['type'] = 'function'
                normalized.append(norm)
            payload['tools'] = normalized

        # Try the Responses API first (preferred)
        try:
            _log_debug('Calling OpenAI responses with payload keys: %s', list(payload.keys()))
            if hasattr(self.client, 'responses') and hasattr(self.client.responses, 'create'):
                return self.client.responses.create(**payload)
        except TypeError as te:
            logger.warning('Responses API call failed (type error): %s', te)
        except Exception as e:
            logger.warning('Responses API call failed: %s', e)

        # Support legacy openai client shape where chat completions are used (tests may mock this)
        try:
            if hasattr(self.client, 'chat') and hasattr(self.client.chat, 'completions') and hasattr(self.client.chat.completions, 'create'):
                # Map payload back to legacy parameters
                legacy = {}
                if 'model' in payload:
                    legacy['model'] = payload.get('model')
                if 'input' in payload:
                    inp = payload.get('input')
                    if isinstance(inp, list):
                        legacy['messages'] = [{'role': m.get('role', 'user'), 'content': m.get('content') if isinstance(m.get('content'), str) else m.get('content')} for m in inp]
                    else:
                        legacy['messages'] = [{'role': 'user', 'content': str(inp)}]
                if 'max_output_tokens' in payload:
                    legacy['max_tokens'] = payload.get('max_output_tokens')
                for k in ('temperature', 'top_p'):
                    if k in payload:
                        legacy[k] = payload[k]
                _log_debug('Calling legacy chat completions with keys: %s', list(legacy.keys()))
                return self.client.chat.completions.create(**legacy)
        except Exception as legacy_err:
            logger.warning('Legacy chat completions call failed: %s', legacy_err)

        # HTTP fallback to Responses endpoint
        try:
            return self._http_fallback_responses(**payload)
        except Exception as http_err:
            logger.error('HTTP fallback (responses) failed: %s', http_err)

        # As a last resort, try legacy chat completions via HTTP
        try:
            return self._http_fallback(**kwargs)
        except Exception as e_final:
            logger.error('HTTP fallback (chat completions) failed: %s', e_final)
            raise

    
    def parse_calendar_message(self, message: str, user_timezone: str = "UTC") -> CalendarIntent:
        """Parse a natural language message into calendar intent."""
        try:
            system_prompt = self._get_system_prompt(user_timezone)
            user_prompt = f"Parse this calendar request: '{message}'"
            
            response = self._create_chat_completion(
                model=self.model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_output_tokens=800
            )
            
            # Extract content from response (works with both client object and dict)
            content = self._extract_content(response)
            result = json.loads(content)
            
            # Convert to CalendarIntent
            intent = CalendarIntent(
                action=result.get("action", "unknown"),
                title=result.get("title"),
                description=result.get("description"),
                start_time=result.get("start_time"),
                end_time=result.get("end_time"),
                duration_minutes=result.get("duration_minutes"),
                date=result.get("date"),
                participants=result.get("participants"),
                location=result.get("location"),
                confidence=result.get("confidence", 0.0),
                raw_message=message,
                errors=result.get("errors")
            )
            
            logger.info(f"Parsed intent: {intent.action} with confidence {intent.confidence}")
            return intent
            
        except Exception as e:
            logger.error(f"Error parsing calendar message: {e}")
            return CalendarIntent(
                action="error",
                raw_message=message,
                errors=[f"Failed to parse message: {str(e)}"],
                confidence=0.0
            )
    
    def suggest_event_details(self, intent: CalendarIntent) -> Dict[str, Any]:
        """Suggest complete event details based on parsed intent."""
        try:
            system_prompt = """You are a calendar assistant. Given a parsed intent, 
            suggest complete and reasonable event details. Return JSON with:
            - title: Clear, professional event title
            - description: Helpful description with context
            - suggested_duration: Duration in minutes if not specified
            - location_suggestions: List of possible locations if relevant
            - preparation_time: Minutes to arrive early if needed
            """
            
            user_prompt = f"""
            Intent: {intent.action}
            Title: {intent.title}
            Description: {intent.description}
            Duration: {intent.duration_minutes} minutes
            Location: {intent.location}
            
            Suggest improvements and missing details.
            """
            
            response = self._create_chat_completion(
                model=self.model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_output_tokens=600
            )
            
            # Extract content from response
            content = self._extract_content(response)
            suggestions = json.loads(content)
            logger.info("Generated event suggestions")
            return suggestions
            
        except Exception as e:
            logger.error(f"Error generating suggestions: {e}")
            return {"error": str(e)}
    
    def generate_smart_response(self, intent: CalendarIntent, calendar_result: Optional[Dict] = None) -> str:
        """Generate a natural language response based on intent and results."""
        try:
            system_prompt = """You are a helpful calendar assistant. Generate natural, 
            friendly responses about calendar operations. Be concise but informative.
            If there were errors, explain them clearly with suggested solutions."""
            
            context = {
                "intent": intent.action,
                "success": calendar_result is not None and "error" not in calendar_result,
                "result": calendar_result,
                "original_message": intent.raw_message
            }
            
            user_prompt = f"Generate a response for this calendar operation: {json.dumps(context, indent=2)}"
            
            response = self._create_chat_completion(
                model=self.model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_output_tokens=300
            )
            
            # Extract content from response
            content = self._extract_content(response)
            return content.strip()
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return f"I processed your request, but encountered an issue generating a response: {str(e)}"
    
    def _get_system_prompt(self, user_timezone: str) -> str:
        """Get the system prompt for calendar parsing."""
        current_time = datetime.now().isoformat()
        
        return f"""You are a calendar parsing assistant. Parse natural language messages into structured calendar intents.

Current time: {current_time}
User timezone: {user_timezone}

Return JSON with these fields:
- action: One of "create_event", "find_slot", "list_events", "cancel_event", "unknown"
- title: Event title (if creating event)
- description: Event description (optional)
- start_time: ISO datetime string (if specific time mentioned)
- end_time: ISO datetime string (if end time mentioned)
- duration_minutes: Integer duration (if mentioned or inferred)
- date: ISO date string (if date mentioned without specific time)
- participants: Array of email addresses or names (if mentioned)
- location: Location string (if mentioned)
- confidence: Float 0-1 indicating parsing confidence
- errors: Array of parsing issues or ambiguities

Examples:
"Meeting tomorrow at 2pm for 1 hour" -> action: "create_event", start_time: "<tomorrow 2pm ISO>", duration_minutes: 60
"Book lunch with John next Friday" -> action: "create_event", title: "Lunch with John", date: "<next Friday ISO>"
"When am I free this week?" -> action: "find_slot", date: "<this week start ISO>"
"What's on my calendar today?" -> action: "list_events", date: "<today ISO>"

Be precise with datetime parsing. Consider relative dates, times, and durations.
Set confidence based on clarity and completeness of the parsed information."""


def create_ai_service_for_user(user) -> Optional[AIAssistantService]:
    """Create AI service instance for a user if they have it configured."""
    if not user.ai_assistant_enabled or not user.openai_api_key:
        return None
    
    try:
        return AIAssistantService(
            api_key=user.openai_api_key,
            model=user.ai_model_preference or "gpt-3.5-turbo"
        )
    except Exception as e:
        logger.error(f"Failed to create AI service for user {user.id}: {e}")
        return None


def _log_debug(msg, *args, **kwargs):
    """Try to use Flask current_app logger, fallback to module logger if not in app context."""
    try:
        from flask import current_app
        current_app.logger.debug(msg, *args, **kwargs)
    except Exception:
        logger.debug(msg % args if args else msg)


def process_calendar_message(user, message: str) -> Tuple[CalendarIntent, Optional[str]]:
    """Process a calendar message for a user and return intent + response."""
    ai_service = create_ai_service_for_user(user)
    
    if not ai_service:
        intent = CalendarIntent(
            action="error",
            raw_message=message,
            errors=["AI assistant not configured. Please set up your OpenAI API key in settings."],
            confidence=0.0
        )
        return intent, "Please configure your AI assistant in Settings before using this feature."
    
    # Parse the message
    intent = ai_service.parse_calendar_message(message)
    
    # Generate a response
    if intent.action == "error":
        response = f"I couldn't understand your request: {intent.errors[0] if intent.errors else 'Unknown error'}"
    else:
        response = ai_service.generate_smart_response(intent)
    
    return intent, response