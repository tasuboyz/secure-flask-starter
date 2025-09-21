import json


def test_chat_endpoint_bypass_csrf(client, app, user, monkeypatch):
    """POST to /calendar/chat with CSRF disabled and a mocked AI service to verify JSON response shape."""
    # Ensure the test user has calendar and AI enabled by re-querying a session-bound user
    with app.app_context():
        from app.extensions import db
        from app.models import User as UserModel
        db_user = UserModel.query.filter_by(email='test@example.com').first()
        if not db_user:
            # create if missing
            db_user = UserModel(email='test@example.com')
            db_user.set_password('testpassword123')
            db.session.add(db_user)
        db_user.google_calendar_connected = True
        db_user.ai_assistant_enabled = True
        db_user.openai_api_key = 'test-key'
        db_user.ai_model_preference = 'gpt-3.5-turbo'
        db.session.commit()

    # Monkeypatch the AI service creator to return a fake service with deterministic output
    class FakeAIService:
        def process_chat(self, message, current_user):
            # Return a predictable response without calling external APIs
            return "Mocked AI response: non sono sicuro, ma sembra che tu abbia una riunione alle 10:00."

    monkeypatch.setattr('app.ai_assistant.create_ai_service_for_user', lambda u: FakeAIService())

    # Login the user using the password from conftest fixture
    # Use the known test email
    login_resp = client.post('/auth/login', data={'email': 'test@example.com', 'password': 'testpassword123'}, follow_redirects=True)
    assert login_resp.status_code in (200, 302)

    # Send the chat request
    payload = {'message': 'che cosa ho da fare domani?'}
    resp = client.post('/calendar/chat', json=payload)

    # Assert
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    # Required keys
    assert 'timestamp' in data
    assert 'response' in data
    assert data.get('response') is not None

    # Basic shape checks
    assert data['timestamp'] != ''
    assert isinstance(data['response'], str)
