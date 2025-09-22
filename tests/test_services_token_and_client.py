import pytest
from datetime import datetime, timedelta
from types import SimpleNamespace

import requests

from app.services.google_token import TokenManager, TokenRefreshError
from app.services.google_client import GoogleCalendarClient, CalendarPermissionError


class DummyResponse:
    def __init__(self, status_code=200, json_data=None, text=''):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class DummyHTTP:
    def __init__(self):
        self.posts = []
        self.requests = []
        self.next_post_response = None
        self.next_request_response = None

    def post(self, url, data=None, timeout=None):
        self.posts.append((url, data))
        return self.next_post_response

    def request(self, method, url, **kwargs):
        self.requests.append((method, url, kwargs))
        return self.next_request_response


def make_user_with_refresh():
    user = SimpleNamespace()
    user.id = 1
    user.google_access_token = None
    user.google_refresh_token = 'refresh-token-abc'
    user.google_token_expires_at = datetime.utcnow() - timedelta(hours=1)
    return user


def test_token_manager_refresh_success(app, monkeypatch):
    user = make_user_with_refresh()
    http = DummyHTTP()
    http.next_post_response = DummyResponse(200, json_data={
        'access_token': 'new-access-token',
        'expires_in': 3600,
        'refresh_token': 'new-refresh-token'
    })

    # monkeypatch db.session.commit to no-op
    class DummySession:
        @staticmethod
        def commit():
            pass

    class DummyDB:
        session = DummySession()

    monkeypatch.setattr('app.services.google_token.db', DummyDB)
    tm = TokenManager(user, http=http)

    token = tm.ensure_valid_token()
    assert token == 'new-access-token'
    assert user.google_access_token == 'new-access-token'
    assert user.google_refresh_token == 'new-refresh-token'
    assert user.google_token_expires_at > datetime.utcnow()


def test_token_manager_no_refresh_token_raises(app):
    user = SimpleNamespace()
    user.id = 2
    user.google_access_token = None
    user.google_refresh_token = None
    user.google_token_expires_at = None

    tm = TokenManager(user, http=DummyHTTP())
    with pytest.raises(TokenRefreshError):
        tm.ensure_valid_token()


def test_google_client_403_raises(app, monkeypatch):
    user = make_user_with_refresh()
    http = DummyHTTP()
    http.next_request_response = DummyResponse(403, json_data={'error': 'insufficient_scope'})

    # Make TokenManager.ensure_valid_token return a token without doing network calls
    class FakeTM:
        def __init__(self, user, http=None):
            pass

        def ensure_valid_token(self):
            return 'fake-token'

    monkeypatch.setattr('app.services.google_client.TokenManager', FakeTM)

    client = GoogleCalendarClient(user, http=http)
    with pytest.raises(CalendarPermissionError) as exc:
        client.request('GET', 'calendars/primary/events')

    assert 'ACCESS_TOKEN_SCOPE_INSUFFICIENT' in str(exc.value)
    assert exc.value.body == {'error': 'insufficient_scope'}
