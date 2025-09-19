import pytest
from app.models import User
from app.extensions import db


def test_user_password_hashing(app):
    """Test User password hashing and verification."""
    with app.app_context():
        user = User(email='test@example.com')
        
        # Test password setting
        user.set_password('testpassword123')
        assert user.password_hash is not None
        assert user.password_hash != 'testpassword123'  # Should be hashed
        assert user.last_password_change_at is not None
        
        # Test password verification
        assert user.check_password('testpassword123') is True
        assert user.check_password('wrongpassword') is False


def test_user_password_hashing_with_argon2(app):
    """Test password hashing specifically with Argon2."""
    with app.app_context():
        try:
            from argon2 import PasswordHasher
            
            user = User(email='test@example.com')
            user.set_password('testpassword123')
            
            # Should use Argon2 format
            assert user.password_hash.startswith('$argon2')
            assert user.check_password('testpassword123') is True
            
        except ImportError:
            pytest.skip("Argon2 not available, test skipped")


def test_user_reset_token(app):
    """Test password reset token generation and verification."""
    with app.app_context():
        user = User(email='test@example.com')
        user.set_password('testpassword123')
        db.session.add(user)
        db.session.commit()
        
        # Generate reset token
        token = user.get_reset_token()
        assert token is not None
        
        # Verify token
        verified_user = User.verify_reset_token(token)
        assert verified_user is not None
        assert verified_user.id == user.id
        
        # Test invalid token
        invalid_user = User.verify_reset_token('invalid_token')
        assert invalid_user is None


def test_user_repr(app):
    """Test User string representation."""
    with app.app_context():
        user = User(email='test@example.com')
        assert repr(user) == '<User test@example.com>'


def test_user_flask_login_properties(app):
    """Test Flask-Login required properties."""
    with app.app_context():
        user = User(email='test@example.com')
        
        assert user.is_authenticated is True
        assert user.is_anonymous is False
        assert user.is_active is True  # Default value
        
        user.id = 123
        assert user.get_id() == '123'