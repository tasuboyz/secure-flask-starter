"""Google Calendar HTTP client wrapper.

Handles authenticated requests and permission error detection.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import requests
from flask import current_app

from app.services.google_token import TokenManager, TokenRefreshError


class CalendarPermissionError(Exception):
    """Raised when access token lacks required Calendar scopes."""
    def __init__(self, message: str = "ACCESS_TOKEN_SCOPE_INSUFFICIENT", body: Any = None):
        super().__init__(message)
        self.body = body


@dataclass
class GoogleCalendarClient:
    user: object
    http: object = field(default=requests)

    def request(self, method: str, endpoint: str, **kwargs):
        """Make an authenticated request to the Google Calendar API.

        Raises CalendarPermissionError on 403 insufficient scope.
        Propagates TokenRefreshError as-is.
        """
        token = TokenManager(self.user, http=self.http).ensure_valid_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        if 'headers' in kwargs and isinstance(kwargs['headers'], dict):
            headers.update(kwargs['headers'])
        kwargs['headers'] = headers

        url = f"https://www.googleapis.com/calendar/v3/{endpoint}"
        resp = self.http.request(method, url, timeout=30, **kwargs)

        if resp.status_code == 403:
            try:
                body = resp.json()
            except Exception:
                body = resp.text
            current_app.logger.debug('Google Calendar permission error: %s', body)
            raise CalendarPermissionError('ACCESS_TOKEN_SCOPE_INSUFFICIENT', body=body)

        return resp
