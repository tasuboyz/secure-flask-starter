# Google Calendar Assistant - Implementation Plan

This document lists the practical steps to prepare and implement a Google Calendar-powered AI assistant integrated into this Flask app. It covers Google Cloud setup, environment variables, OAuth details (including refresh tokens), backend endpoints, security considerations, testing, and optional Telegram integration.

## Goal

Allow users to:
- Log in with Google (OpenID Connect)
- Link their Google Calendar (OAuth with Calendar scopes and refresh tokens)
- Use a chat UI (or Telegram) to instruct the assistant to create/modify events
- Have background workers handle token refresh, retries, and asynchronous tasks

## Overview / Components

- Flask backend (current project)
  - Handles OAuth and token storage (we've added token fields to `User`)
  - Provides API endpoints for availability and event creation
- AI service
  - Parse user messages into intents/slots (e.g., date, time, duration, attendees)
  - Could be OpenAI, Llama, or other NLP backend
- Background worker
  - RQ/Celery/Redis for async token refresh and heavy tasks
- Telegram connector (optional)
  - Bot to receive user messages and link them to user accounts in the web app

## Prerequisites

- A Google Cloud project with OAuth 2.0 Client credentials
- Google Calendar API enabled
- The app's OAuth redirect URLs registered in the Google Console
- `.env` (or secrets) configured in local/dev and production (see below)

## Google Cloud Console setup

1. Create or choose a Google Cloud Project
2. Enable APIs: "Google Calendar API"
3. In "APIs & Services > Credentials" create an OAuth 2.0 Client ID
   - Application type: Web application
   - Add redirect URIs used by your app. Example local URIs:
     - `http://127.0.0.1:5000/auth/google/callback`
     - `http://127.0.0.1:5000/auth/google/calendar/callback`
4. Download the JSON credentials (client secret JSON) and do NOT commit it to the repo

## Environment variables

Store these securely (use `.env` in dev, secret manager in prod):

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `SECRET_KEY`, `SECURITY_PASSWORD_SALT`
- `DATABASE_URL`
- `REDIS_URL` (if using background workers)
- `OPENAI_API_KEY` (or other AI provider keys) — optional

Example `.env` snippet (do not commit real values):

```
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://user:pass@db:5432/appdb
REDIS_URL=redis://localhost:6379/0
```

## OAuth details (important)

To receive a `refresh_token` so your backend can act on behalf of the user later, request offline access and explicit consent at authorize time. Use the following parameters when redirecting to Google's authorization endpoint (Authlib supports passing these):

- `scope`: include `https://www.googleapis.com/auth/calendar.events`
- `access_type=offline`
- `prompt=consent`

Example with Authlib in `authorize_redirect`:

```python
redirect_uri = url_for('auth.google_calendar_callback', _external=True)
return google_client.authorize_redirect(
    redirect_uri,
    scope='openid email profile https://www.googleapis.com/auth/calendar.events',
    access_type='offline',
    prompt='consent'
)
```

Note: Google will only return `refresh_token` the first time a user consents unless you use `prompt=consent`.

## Token storage & refresh

We store:
- `google_access_token`
- `google_refresh_token`
- `google_token_expires_at`

Implement a helper to check expiry and refresh tokens automatically before making Calendar API calls.

Example helper (high level):

```python
def ensure_valid_token(user):
    if token_expired(user.google_token_expires_at):
        new_token = refresh_token_with_google(user.google_refresh_token)
        user.google_access_token = new_token['access_token']
        user.google_token_expires_at = epoch_to_datetime(new_token['expires_at'])
        if new_token.get('refresh_token'):
            user.google_refresh_token = new_token['refresh_token']
        db.session.commit()
    return user.google_access_token
```

Prefer running the refresh logic in a background worker when possible.

## Suggested API endpoints

- GET `/calendar/availability?start=...&end=...&duration=30` — returns candidate free slots
- POST `/calendar/events` — body: {start, end, title, attendees, description} -> creates event
- GET `/calendar/events?range=...` — list events
- POST `/chat/message` — accepts a text message; backend uses AI parser to transform into an intent and calls `/calendar/events` after confirmation

## Minimal Web UI

- Dashboard with "Connect Google Calendar" button (points to `/auth/google/calendar`).
- Calendar view (month/week) or list of upcoming events.
- Chat UI (small text box) where user writes commands and gets suggested times/confirmations.

## Telegram integration (optional)

- Create a Telegram Bot and set webhook to your app endpoint (or poll).
- Authentication pattern:
  - Link Telegram user to web user via a one-time code or deep link.
  - After linking, messages to bot are forwarded to the user's chat session on the backend.
- The bot forwards responses and confirmations back to the user.

## AI assistant design (very simple MVP)

- Use OpenAI or a small NL parser to extract:
  - Intent: create_event / modify_event / cancel_event / show_availability
  - Slots: date, start_time, duration, attendees (emails), title, description
- Validate slots (e.g., parse dates into timezone-aware datetimes)
- Query availability, generate 1–3 candidate slots, ask user to confirm
- Create event upon confirmation

## Worker / background tasks

- Use Redis + RQ or Celery for:
  - Token refresh
  - Long-running API calls
  - Periodic syncs (optional)

## Security & privacy checklist

- Never log access/refresh tokens
- Use HTTPS in production
- Store sensitive secrets in a managed secrets store
- Provide an explicit opt-in for calendar access
- Implement per-user rate limits and global rate limits

## Testing

- Unit tests for NLP parser and intent extraction
- Integration tests for OAuth flows (mocking Google endpoints)
- End-to-end tests (optional) using a test Google account

## Quick implementation plan (first 2 days)

1. Ensure OAuth flow requests `access_type=offline` + `prompt=consent` and stores refresh token.
2. Implement helper to `ensure_valid_token(user)` and a small test for token refresh logic (mocking the token endpoint).
3. Create endpoints: availability and create-event + simple UI (dashboard with connect button and chat box).
4. Hook a basic OpenAI prompt to parse commands into a JSON intent (local mock if key missing).
5. Add a minimal Telegram bot bridge (link + forward messages).

## Next steps I can take for you
- Implement steps 1 & 2 now (OAuth update + refresh helper + unit tests) — recommended first.
- Or scaffold the chat UI + endpoints (priority if you want a quick demo).

---

If you want, I will now implement the first step: update the `/auth/google/calendar` route to include `access_type=offline` and `prompt=consent`, and add a token refresh helper plus a small unit test mocking Google token endpoint. Which should I do now?