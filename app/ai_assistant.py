"""AI Assistant service for processing natural language calendar requests."""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from flask import current_app
from dataclasses import dataclass

logger = logging.getLogger(__name__)


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
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            try:
                import openai
                self._client = openai.OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("OpenAI package not installed. Run: pip install openai")
        return self._client
    
    def parse_calendar_message(self, message: str, user_timezone: str = "UTC") -> CalendarIntent:
        """Parse a natural language message into calendar intent."""
        try:
            system_prompt = self._get_system_prompt(user_timezone)
            user_prompt = f"Parse this calendar request: '{message}'"
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=800,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
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
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=600,
                response_format={"type": "json_object"}
            )
            
            suggestions = json.loads(response.choices[0].message.content)
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
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            return response.choices[0].message.content.strip()
            
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