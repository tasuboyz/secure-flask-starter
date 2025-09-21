"""Tests for AI Assistant service."""
import pytest
import json
from unittest.mock import Mock, patch
from datetime import datetime

from app.ai_assistant import AIAssistantService, CalendarIntent, process_calendar_message


class TestAIAssistantService:
    """Test cases for AIAssistantService."""
    
    def test_init(self):
        """Test service initialization."""
        service = AIAssistantService("test-key", "gpt-3.5-turbo")
        assert service.api_key == "test-key"
        assert service.model == "gpt-3.5-turbo"
    
    @patch.object(AIAssistantService, '_create_chat_completion')
    def test_parse_calendar_message_success(self, mock_create_completion):
        """Test successful message parsing."""
        # Mock OpenAI response
        # Simulate the responses API dict that _extract_content can parse
        mock_create_completion.return_value = {
            'output_text': json.dumps({
                'action': 'create_event',
                'title': 'Team Meeting',
                'start_time': '2025-09-22T14:00:00Z',
                'duration_minutes': 60,
                'confidence': 0.9
            })
        }
        
        service = AIAssistantService("test-key")
        intent = service.parse_calendar_message("Schedule team meeting tomorrow at 2pm")
        
        assert intent.action == "create_event"
        assert intent.title == "Team Meeting"
        assert intent.confidence == 0.9
        assert intent.duration_minutes == 60
    
    @patch.object(AIAssistantService, '_create_chat_completion')
    def test_parse_calendar_message_error(self, mock_create_completion):
        """Test error handling in message parsing."""
        # Mock OpenAI to raise an exception
        mock_create_completion.side_effect = Exception("API Error")

        service = AIAssistantService("test-key")
        intent = service.parse_calendar_message("Schedule meeting")
        
        assert intent.action == "error"
        assert intent.confidence == 0.0
        assert "Failed to parse message" in intent.errors[0]
    
    def test_calendar_intent_dataclass(self):
        """Test CalendarIntent dataclass creation."""
        intent = CalendarIntent(
            action="create_event",
            title="Test Event",
            confidence=0.8,
            raw_message="test message"
        )
        
        assert intent.action == "create_event"
        assert intent.title == "Test Event"
        assert intent.confidence == 0.8
        assert intent.raw_message == "test message"
    
    def test_create_ai_service_for_user_enabled(self):
        """Test creating AI service for user with AI enabled."""
        from app.ai_assistant import create_ai_service_for_user
        
        # Mock user with AI enabled
        user = Mock()
        user.ai_assistant_enabled = True
        user.openai_api_key = "test-key"
        user.ai_model_preference = "gpt-4"
        
        service = create_ai_service_for_user(user)
        
        assert service is not None
        assert service.api_key == "test-key"
        assert service.model == "gpt-4"
    
    def test_create_ai_service_for_user_disabled(self):
        """Test creating AI service for user with AI disabled."""
        from app.ai_assistant import create_ai_service_for_user
        
        # Mock user with AI disabled
        user = Mock()
        user.ai_assistant_enabled = False
        user.openai_api_key = "test-key"
        
        service = create_ai_service_for_user(user)
        
        assert service is None
    
    def test_create_ai_service_for_user_no_key(self):
        """Test creating AI service for user without API key."""
        from app.ai_assistant import create_ai_service_for_user
        
        # Mock user without API key
        user = Mock()
        user.ai_assistant_enabled = True
        user.openai_api_key = None
        
        service = create_ai_service_for_user(user)
        
        assert service is None
    
    @patch('app.ai_assistant.create_ai_service_for_user')
    def test_process_calendar_message_no_service(self, mock_create_service):
        """Test processing message when AI service is not available."""
        mock_create_service.return_value = None
        
        user = Mock()
        intent, response = process_calendar_message(user, "test message")
        
        assert intent.action == "error"
        assert "AI assistant not configured" in intent.errors[0]
        assert "configure your AI assistant" in response
    
    @patch('app.ai_assistant.create_ai_service_for_user')
    def test_process_calendar_message_success(self, mock_create_service):
        """Test successful message processing."""
        # Mock AI service
        mock_service = Mock()
        mock_intent = CalendarIntent(
            action="create_event",
            title="Test Event",
            confidence=0.9,
            raw_message="test message"
        )
        mock_service.parse_calendar_message.return_value = mock_intent
        mock_service.generate_smart_response.return_value = "Event parsed successfully"
        mock_create_service.return_value = mock_service
        
        user = Mock()
        intent, response = process_calendar_message(user, "Schedule meeting tomorrow")
        
        assert intent.action == "create_event"
        assert intent.title == "Test Event"
        assert response == "Event parsed successfully"