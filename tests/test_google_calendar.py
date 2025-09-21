"""Tests for Google Calendar integration and token management."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from app.google_calendar import ensure_valid_token, TokenRefreshError, create_event
from app.models import User


def test_ensure_valid_token_with_valid_token(app, db):
    """Test that ensure_valid_token returns existing token if not expired."""
    with app.app_context():
        # Create user with valid token
        user = User(email='test@example.com')
        user.google_access_token = 'valid_token'
        user.google_refresh_token = 'refresh_token'
        user.google_token_expires_at = datetime.utcnow() + timedelta(hours=1)
        
        db.session.add(user)
        db.session.commit()
        
        # Should return existing token without API call
        token = ensure_valid_token(user)
        assert token == 'valid_token'


def test_ensure_valid_token_with_expired_token(app, db):
    """Test token refresh when access token is expired."""
    with app.app_context():
        # Create user with expired token
        user = User(email='test@example.com')
        user.google_access_token = 'expired_token'
        user.google_refresh_token = 'refresh_token'
        user.google_token_expires_at = datetime.utcnow() - timedelta(hours=1)
        
        db.session.add(user)
        db.session.commit()
        
        # Mock the requests.post call for token refresh
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'new_access_token',
            'expires_in': 3600
        }
        mock_response.raise_for_status.return_value = None
        
        with patch('app.google_calendar.requests.post', return_value=mock_response):
            token = ensure_valid_token(user)
            
            assert token == 'new_access_token'
            assert user.google_access_token == 'new_access_token'
            # Check that expiry was updated
            assert user.google_token_expires_at > datetime.utcnow()


def test_ensure_valid_token_no_refresh_token(app, db):
    """Test that TokenRefreshError is raised when no refresh token available."""
    with app.app_context():
        user = User(email='test@example.com')
        user.google_access_token = 'expired_token'
        user.google_refresh_token = None  # No refresh token
        user.google_token_expires_at = datetime.utcnow() - timedelta(hours=1)
        
        db.session.add(user)
        db.session.commit()
        
        with pytest.raises(TokenRefreshError, match="No refresh token available"):
            ensure_valid_token(user)


def test_ensure_valid_token_refresh_fails(app, db):
    """Test that TokenRefreshError is raised when refresh API call fails."""
    with app.app_context():
        user = User(email='test@example.com')
        user.google_access_token = 'expired_token'
        user.google_refresh_token = 'refresh_token'
        user.google_token_expires_at = datetime.utcnow() - timedelta(hours=1)
        
        db.session.add(user)
        db.session.commit()
        
        # Mock failed API call
        with patch('app.google_calendar.requests.post') as mock_post:
            mock_post.side_effect = Exception("Network error")
            
            with pytest.raises(TokenRefreshError, match="Failed to refresh token"):
                ensure_valid_token(user)


@patch('app.google_calendar.make_calendar_request')
def test_create_event(mock_request, app, db):
    """Test creating a calendar event."""
    with app.app_context():
        user = User(email='test@example.com')
        user.google_access_token = 'valid_token'
        user.google_token_expires_at = datetime.utcnow() + timedelta(hours=1)
        
        db.session.add(user)
        db.session.commit()
        
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            'id': 'event123',
            'summary': 'Test Meeting',
            'start': {'dateTime': '2025-09-22T10:00:00Z'},
            'end': {'dateTime': '2025-09-22T11:00:00Z'}
        }
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response
        
        start_time = datetime(2025, 9, 22, 10, 0, 0)
        end_time = datetime(2025, 9, 22, 11, 0, 0)
        
        result = create_event(
            user,
            start_time,
            end_time,
            'Test Meeting',
            'Test description',
            ['attendee@example.com']
        )
        
        assert result['id'] == 'event123'
        assert result['summary'] == 'Test Meeting'
        
        # Verify the API was called with correct data
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[0][1] == 'POST'  # method
        assert call_args[0][2] == 'calendars/primary/events'  # endpoint
        
        # Check event data structure
        event_data = call_args[1]['json']
        assert event_data['summary'] == 'Test Meeting'
        assert event_data['description'] == 'Test description'
        assert event_data['attendees'] == [{'email': 'attendee@example.com'}]