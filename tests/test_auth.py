import pytest
from flask import url_for
from app.models import User
from app.extensions import db


def test_index_page(client):
    """Test home page."""
    response = client.get('/')
    assert response.status_code == 200
    assert 'Benvenuto in Pro Project' in response.get_data(as_text=True)


def test_login_page(client):
    """Test login page."""
    response = client.get('/auth/login')
    assert response.status_code == 200
    assert 'Accedi al tuo account' in response.get_data(as_text=True)


def test_register_page(client):
    """Test registration page."""
    response = client.get('/auth/register')
    assert response.status_code == 200
    assert 'Crea un nuovo account' in response.get_data(as_text=True)


def test_login_flow(client, app):
    """Test login flow with valid credentials."""
    with app.app_context():
        # Create test user
        user = User(email='test@example.com')
        user.set_password('testpassword123')
        db.session.add(user)
        db.session.commit()
        
        # Test login
        response = client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'testpassword123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert 'Dashboard' in response.get_data(as_text=True)
        
        # Check that last_login_at was updated
        updated_user = User.query.filter_by(email='test@example.com').first()
        assert updated_user.last_login_at is not None


def test_login_invalid_credentials(client, app):
    """Test login with invalid credentials."""
    with app.app_context():
        # Create test user
        user = User(email='test@example.com')
        user.set_password('testpassword123')
        db.session.add(user)
        db.session.commit()
        
        # Test login with wrong password
        response = client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'wrongpassword'
        })
        
        assert response.status_code == 200
        assert 'Email o password non validi' in response.get_data(as_text=True)


def test_registration_flow(client, app):
    """Test user registration."""
    with app.app_context():
        response = client.post('/auth/register', data={
            'email': 'newuser@example.com',
            'password': 'newpassword123',
            'password2': 'newpassword123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert 'Registrazione completata' in response.get_data(as_text=True)
        
        # Check user was created
        user = User.query.filter_by(email='newuser@example.com').first()
        assert user is not None
        assert user.check_password('newpassword123') is True


def test_registration_password_mismatch(client):
    """Test registration with password mismatch."""
    response = client.post('/auth/register', data={
        'email': 'newuser@example.com',
        'password': 'password123',
        'password2': 'differentpassword'
    })
    
    assert response.status_code == 200
    assert 'Le password non corrispondono' in response.get_data(as_text=True)


def test_registration_duplicate_email(client, app):
    """Test registration with existing email."""
    with app.app_context():
        # Create existing user
        user = User(email='existing@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        
        # Try to register with same email
        response = client.post('/auth/register', data={
            'email': 'existing@example.com',
            'password': 'newpassword123',
            'password2': 'newpassword123'
        })
        
        assert response.status_code == 200
        assert 'Questo email è già registrato' in response.get_data(as_text=True)


def test_logout_requires_login(client):
    """Test that logout requires being logged in."""
    response = client.post('/auth/logout')
    assert response.status_code == 302  # Redirect to login


def test_dashboard_requires_login(client):
    """Test that dashboard requires login."""
    response = client.get('/dashboard')
    assert response.status_code == 302  # Redirect to login


def test_forgot_password_page(client):
    """Test forgot password page."""
    response = client.get('/auth/forgot-password')
    assert response.status_code == 200
    assert 'Reset Password' in response.get_data(as_text=True)


def test_forgot_password_flow(client, app):
    """Test forgot password submission."""
    with app.app_context():
        # Create test user
        user = User(email='test@example.com')
        user.set_password('testpassword123')
        db.session.add(user)
        db.session.commit()
        
        # Submit forgot password form
        response = client.post('/auth/forgot-password', data={
            'email': 'test@example.com'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert 'riceverai le istruzioni' in response.get_data(as_text=True)