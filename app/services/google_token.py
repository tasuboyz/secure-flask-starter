"""Token management service for Google OAuth tokens.

Extracted from app.google_calendar to improve separation of concerns.
Provides a simple TokenManager API to refresh tokens and ensure validity.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import requests
from flask import current_app
from app.extensions import db


class TokenRefreshError(Exception):
    """Raised when token refresh fails."""
    pass


@dataclass
class TokenManager:
    """Service to handle Google OAuth token lifecycle for a user."""
    user: object  # Expecting app.models.User-like object
    http: object = field(default=requests)  # Injectable HTTP client (must provide .post)

    def ensure_valid_token(self) -> str:
        """Return a valid access token, refreshing if necessary.

        Raises TokenRefreshError if refresh is required but fails.
        """
        now = datetime.utcnow()
        buffer = timedelta(minutes=5)

        # If token exists and has not expired (with buffer), reuse
        if getattr(self.user, 'google_token_expires_at', None) and self.user.google_token_expires_at > (now + buffer):
            return getattr(self.user, 'google_access_token', None)

        # Need to refresh
        refresh_token = getattr(self.user, 'google_refresh_token', None)
        if not refresh_token:
            raise TokenRefreshError("No refresh token available")

        token_url = "https://oauth2.googleapis.com/token"
        data = {
            'client_id': current_app.config.get('GOOGLE_CLIENT_ID'),
            'client_secret': current_app.config.get('GOOGLE_CLIENT_SECRET'),
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token'
        }

        try:
            resp = self.http.post(token_url, data=data, timeout=10)
            resp.raise_for_status()
            payload = resp.json()

            access_token = payload['access_token']
            expires_in = payload.get('expires_in', 3600)

            # Persist updates
            self.user.google_access_token = access_token
            self.user.google_token_expires_at = now + timedelta(seconds=int(expires_in))
            if 'refresh_token' in payload:
                self.user.google_refresh_token = payload['refresh_token']

            db.session.commit()
            return access_token
        except requests.RequestException as e:
            current_app.logger.error("Token refresh failed for user %s: %s", getattr(self.user, 'id', 'unknown'), str(e))
            raise TokenRefreshError(f"Failed to refresh token: {str(e)}")
        except KeyError as e:
            current_app.logger.error("Invalid token response for user %s: missing %s", getattr(self.user, 'id', 'unknown'), str(e))
            raise TokenRefreshError(f"Invalid token response: {str(e)}")
        except Exception as e:
            current_app.logger.error("Unexpected error refreshing token for user %s: %s", getattr(self.user, 'id', 'unknown'), str(e))
            raise TokenRefreshError(f"Failed to refresh token: {str(e)}")
