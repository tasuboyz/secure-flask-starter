import pytest
from unittest.mock import patch, MagicMock
from app.models import User


def test_google_login_redirect(client):
    """Test that Google login redirects to OAuth provider."""
    # Without Google OAuth configured, should redirect to login with error
    response = client.get('/auth/google', follow_redirects=True)
    assert b'Google OAuth non' in response.data


def test_google_callback_without_config(client):
    """Test Google callback without OAuth configuration."""
    response = client.get('/auth/google/callback', follow_redirects=True)
    assert b'Google OAuth non' in response.data


@patch('app.auth.routes.oauth')
def test_google_callback_creates_new_user(mock_oauth, client, app):
    """Test that Google callback creates new user."""
    # Mock OAuth response
    mock_google = MagicMock()
    mock_oauth.google = mock_google
    
    # Mock token response
    mock_token = {'access_token': 'test_token'}
    mock_google.authorize_access_token.return_value = mock_token
    
    # Mock userinfo response
    mock_userinfo = {
        'sub': '123456789',
        'email': 'test@example.com',
        'email_verified': True,
        'name': 'Test User'
    }
    mock_google.parse_id_token.return_value = mock_userinfo
    
    with app.app_context():
        # Test callback
        response = client.get('/auth/google/callback', follow_redirects=True)
        
        # Check user was created
        user = User.query.filter_by(email='test@example.com').first()
        assert user is not None
        assert user.google_id == '123456789'
        assert user.is_active is True
        assert user.is_admin is False


@patch('app.auth.routes.oauth')
def test_google_callback_links_existing_user(mock_oauth, client, app):
    """Test that Google callback links to existing user account."""
    # Create existing user
    with app.app_context():
        existing_user = User(email='existing@example.com')
        existing_user.set_password('password123')
        from app.extensions import db
        db.session.add(existing_user)
        db.session.commit()
        user_id = existing_user.id
    
    # Mock OAuth response
    mock_google = MagicMock()
    mock_oauth.google = mock_google
    
    mock_token = {'access_token': 'test_token'}
    mock_google.authorize_access_token.return_value = mock_token
    
    mock_userinfo = {
        'sub': '987654321',
        'email': 'existing@example.com',
        'email_verified': True,
        'name': 'Existing User'
    }
    mock_google.parse_id_token.return_value = mock_userinfo
    
    with app.app_context():
        response = client.get('/auth/google/callback', follow_redirects=True)

        # Check user was linked
        from app.extensions import db
        user = db.session.get(User, user_id)
        assert user.google_id == '987654321'
        assert user.email == 'existing@example.com'


@patch('app.auth.routes.oauth')
def test_google_callback_unverified_email(mock_oauth, client):
    """Test that unverified email is rejected."""
    mock_google = MagicMock()
    mock_oauth.google = mock_google
    
    mock_token = {'access_token': 'test_token'}
    mock_google.authorize_access_token.return_value = mock_token
    
    # Unverified email
    mock_userinfo = {
        'sub': '123456789',
        'email': 'unverified@example.com',
        'email_verified': False,
        'name': 'Unverified User'
    }
    mock_google.parse_id_token.return_value = mock_userinfo
    
    response = client.get('/auth/google/callback', follow_redirects=True)
    assert b'email non verificata' in response.data