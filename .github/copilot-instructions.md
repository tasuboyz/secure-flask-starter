# AI Agent Instructions - Calendar AI Dashboard

This project implements a **Calendar AI Dashboard** that integrates Google Calendar with an OpenAI-powered assistant. These instructions help AI coding agents understand the project's architecture, current state, and implementation priorities.

## Project Overview

A comprehensive **Calendar AI Dashboard** with:
- **Google Calendar Integration**: OAuth connection with maximum permissions, event management, timezone detection
- **AI Assistant**: OpenAI Responses API with tool-calling for calendar actions
- **Modern UI**: Three-column layout (sidebar + calendar grid + AI panel) replacing tabbed interface
- **Robust Backend**: Calendar API endpoints, comprehensive permission error handling, reauthorization flow
- **Security**: Production-ready authentication, password hashing, CSRF protection, rate limiting

## Tech Stack

- **Backend**: Python 3.11+ with Flask (application factory pattern)
- **Database**: SQLAlchemy with Flask-SQLAlchemy ORM, Alembic migrations
- **Authentication**: Flask-Login + Google OAuth via Authlib with full calendar scope
- **Security**: Argon2 password hashing, Flask-WTF CSRF protection, flask-limiter rate limiting
- **Email**: Flask-Mail for password reset functionality
- **Calendar**: Google Calendar API v3 with comprehensive permission management and error handling
- **AI**: OpenAI Responses API with tool-calling for calendar event creation
- **Testing**: pytest with application/database fixtures, Google OAuth mocking

## Current Project Structure
### Directory Structure

```
app/
├── __init__.py                    # Application factory with create_app()
├── config.py                      # Environment-specific configurations (Dev/Test/Prod)
├── extensions.py                  # Global extension instances
├── models.py                      # User model with Google tokens, AI settings
├── routes.py                      # Main application routes (index, dashboard)
├── ai_assistant.py                # OpenAI Responses API with tool-calling
├── google_calendar.py             # Google Calendar API utilities
├── supabase.py                    # Supabase integration (optional)
├── auth/                          # Authentication blueprint
│   ├── routes.py                  # Login/logout/Google OAuth/reauthorization
│   ├── forms.py                   # WTForms with validation
│   ├── email_utils.py             # Mail utilities
│   └── templates/                 # Auth-specific templates
├── calendar/                      # Calendar blueprint
│   └── __init__.py                # Calendar API endpoints & AI chat
├── settings/                      # Settings blueprint
│   ├── routes.py                  # User settings (profile, AI config)
│   ├── forms.py                   # Settings forms
│   └── templates/settings/        # Settings templates
├── templates/                     # Global templates
│   ├── base.html                  # Base layout (TO BE REDESIGNED)
│   ├── dashboard.html             # Current tabbed UI (TO BE REPLACED)
│   └── index.html                 # Landing page
├── static/                        # Static assets
│   └── css/
│       └── style.css              # Modern responsive styles
└── scripts/                       # Admin utilities and key generation
migrations/                        # Alembic database migrations
tests/                             # pytest test suite
docs/                              # Documentation
    ├── calendar_ui_mission.md      # UI redesign mission plan
    └── project_structure.md        # Complete project structure
```

## Calendar AI Dashboard - UI Redesign Mission

### CRITICAL: What to Remove/Replace in Current UI

The current `app/templates/dashboard.html` implements a **tabbed interface** that must be **completely replaced** with a modern Calendar AI dashboard. Here's what needs to change:

#### Current Structure to Remove:
```html
<!-- REMOVE: Tab navigation system -->
<ul class="nav nav-tabs" id="dashboardTabs">
  <li class="nav-item"><a class="nav-link active" id="overview-tab">Panoramica</a></li>
  <li class="nav-item"><a class="nav-link" id="calendar-tab">Calendario</a></li>
  <li class="nav-item"><a class="nav-link" id="assistant-tab">AI Assistant</a></li>
  <li class="nav-item"><a class="nav-link" id="settings-tab">Impostazioni</a></li>
</ul>

<!-- REMOVE: Tab content containers -->
<div class="tab-content" id="dashboardTabContent">
  <div class="tab-pane fade show active" id="overview">...</div>
  <div class="tab-pane fade" id="calendar">...</div>
  <div class="tab-pane fade" id="assistant">...</div>
  <div class="tab-pane fade" id="settings">...</div>
</div>
```

#### New Structure to Implement:
```html
<!-- NEW: Three-column layout -->
<div class="calendar-dashboard">
  <!-- LEFT: Sidebar Navigation -->
  <aside class="sidebar">
    <div class="logo">Calendar</div>
    <nav class="nav-menu">
      <a href="#" class="nav-item active">Dashboard</a>
      <a href="#" class="nav-item">Calendar</a>
      <a href="#" class="nav-item">Tasks</a>
      <a href="#" class="nav-item">Settings</a>
    </nav>
    <div class="user-profile">...</div>
  </aside>

  <!-- CENTER: Calendar Grid -->
  <main class="calendar-main">
    <header class="calendar-header">
      <h1>May 2024</h1>
      <div class="calendar-controls">
        <input type="search" placeholder="Search events">
        <button class="btn-new-event">+ New Event</button>
      </div>
    </header>
    <div class="calendar-grid">
      <!-- Monthly calendar with events -->
    </div>
  </main>

  <!-- RIGHT: AI Assistant + Summary -->
  <aside class="ai-panel">
    <div class="ai-assistant">...</div>
    <div class="today-events">...</div>
    <div class="upcoming-tasks">...</div>
  </aside>
</div>
```

### Required CSS Architecture Changes

#### Current CSS (app/static/css/style.css) - Modify These Patterns:
1. **Remove**: `.nav-tabs`, `.tab-content`, `.tab-pane` Bootstrap tab styles
2. **Remove**: `.dashboard-card` grid layout for tabbed content
3. **Replace**: `.dashboard-container` with `.calendar-dashboard` grid layout
4. **Add**: Sidebar, calendar grid, and AI panel responsive layout

#### New CSS Structure to Add:
```css
/* Three-column layout */
.calendar-dashboard {
  display: grid;
  grid-template-columns: 250px 1fr 350px;
  height: 100vh;
}

/* Sidebar styling */
.sidebar {
  background: #f8f9fa;
  border-right: 1px solid #e9ecef;
}

/* Calendar main area */
.calendar-main {
  display: flex;
  flex-direction: column;
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  /* Calendar styling */
}

/* AI panel */
.ai-panel {
  background: #ffffff;
  border-left: 1px solid #e9ecef;
  overflow-y: auto;
}

/* Mobile-first guidance */
/* Design all components starting from mobile widths (360-420px). Use off-canvas/drawer patterns for sidebar and AI panel on small screens. Ensure primary actions are reachable with thumb ergonomics. */
```

## Backend API Integration Points

### Existing Endpoints to Use:
- `GET /calendar/events?date=YYYY-MM-DD` → Daily events
- `GET /calendar/events/range?start_date=ISO&end_date=ISO` → Monthly events for calendar grid
- `GET /calendar/slots?start_date=ISO&end_date=ISO&duration=30` → Available time slots
- `POST /calendar/events` → Create new event
- `POST /calendar/chat` → AI assistant chat

### Telegram integration endpoints (suggested)
- `POST /integrations/telegram/webhook/<secret>` → receive Telegram updates (webhook). Translate message -> `POST /calendar/chat` for linked user.
- `GET /settings/integrations/telegram/link` → generate short-lived link/token for linking Telegram account (deep-link to `t.me/<bot>?start=TOKEN`).

Env variables to add when implementing Telegram support:
```bash
TELEGRAM_BOT_TOKEN=<bot-token>
TELEGRAM_WEBHOOK_SECRET=<secret>
TELEGRAM_HOST_URL=https://your.domain
```

### API Response Formats:
```json
// Calendar events
{
  "events": [
    {
      "id": "event123",
      "summary": "Team meeting",
      "start": {"dateTime": "2024-05-23T14:00:00Z"},
      "end": {"dateTime": "2024-05-23T15:00:00Z"},
      "description": "Weekly team sync"
    }
  ]
}

// AI chat response
{
  "response": "I've scheduled your meeting for tomorrow at 10 AM",
  "timestamp": "2024-05-23T10:30:00Z"
}

// Error with reauthorization hint
{
  "error": "Insufficient permissions",
  "calendar_permission_error": true,
  "reauthorize_url": "/auth/google/calendar/reauthorize"
}
```

## JavaScript Functions to Preserve/Modify

### Keep These Functions (from dashboard.html):
```javascript
// Preserve core calendar functionality
function loadEvents() { /* fetch /calendar/events */ }
function sendMessage() { /* POST /calendar/chat */ }
function addMessageToChat(sender, message) { /* chat UI */ }

// Modify for new UI
function displayEvents(events) { /* adapt for calendar grid */ }
function createQuickEvent() { /* integrate with new modal */ }
```

### Remove These Functions:
```javascript
// Remove all Bootstrap tab initialization
const tabTrigger = new bootstrap.Tab(tab);

// Remove tab switching logic
document.querySelectorAll('#dashboardTabs a');
```

## Google Calendar Integration Status

### ✅ IMPLEMENTED & WORKING
- **OAuth Connection**: Maximum permission scope (`https://www.googleapis.com/auth/calendar`) by default
- **Permission Management**: User preference persistence in `User.google_permission_mode` field
- **Reauthorization Flow**: Forced consent with token revocation for scope upgrades
- **Token Management**: Automatic refresh with comprehensive error handling
- **Simplified API Calls**: Eliminated problematic `calendars/primary` requests that required extra permissions
- **Error Detection**: `ACCESS_TOKEN_SCOPE_INSUFFICIENT` detection with structured responses
- **UI Integration**: Permission dropdown reflecting saved preferences, reauthorization banners

### Core Functions Available:
- `ensure_valid_token(user)` - Token validation and refresh with scope error detection
- `create_event(user, event_data)` - Event creation with timezone awareness
- `get_events(user, start_date, end_date)` - Event retrieval with error handling
- `find_available_slots(user, start_date, end_date, duration)` - Availability search
- `get_primary_calendar_timezone(user)` - Timezone detection with UTC fallback

### Permission Error Handling:
Backend automatically detects permission issues and returns:
```json
{
  "error": "Calendar permissions required",
  "calendar_permission_error": true,
  "reauthorize_url": "/auth/google/calendar/reauthorize"
}
```

UI displays reauthorization banner with one-click fix when this error is detected.

## AI Assistant Integration Status

### ✅ IMPLEMENTED & WORKING
- **OpenAI Integration**: `app/ai_assistant.py` with Responses API and tool-calling
- **Calendar Tool Integration**: Direct event creation via AI function calls
- **User Preferences**: Model selection (GPT-4, GPT-4o-mini), language preference storage
- **Chat Endpoint**: `app/calendar/__init__.py` - `POST /calendar/chat` with full error handling
- **Timezone Awareness**: AI uses detected calendar timezone in prompts
- **Permission Error Propagation**: AI gracefully handles calendar permission errors

### AI Chat Flow:
1. User sends message → `POST /calendar/chat`
2. Backend processes with `ai_service.process_chat(message, user)`
3. AI may call tools (e.g., `create_calendar_event`) 
4. Calendar permission errors are caught and returned as structured responses
5. UI can detect errors and trigger reauthorization flow

## Development Workflow for UI Redesign

### Phase 1: Layout Structure
1. **Update `app/templates/base.html`**:
   - Remove Bootstrap tab dependencies
   - Add CSS Grid support
   - Keep CSRF meta tags and core navigation

2. **Replace `app/templates/dashboard.html`**:
   - Remove entire tab system
   - Implement three-column grid layout
   - Preserve existing JavaScript functions for API calls

3. **Update `app/static/css/style.css`**:
   - Remove `.nav-tabs`, `.tab-content` styles
   - Add `.calendar-dashboard`, `.sidebar`, `.calendar-main`, `.ai-panel`
   - Implement responsive design

### Phase 2: Calendar Grid Integration
1. **Choose Calendar Library**:
   - **Recommended**: FullCalendar.js for robust calendar functionality
   - **Alternative**: Custom grid using CSS Grid + JavaScript

2. **Integrate with Backend**:
   - Call `/calendar/events/range` for monthly view
   - Handle event clicks, navigation, today highlighting
   - Implement event colors and categorization

3. **Add Event Creation Modal**:
   - "New Event" button → modal form
   - Form validation (title, start/end times, attendees)
   - Submit → `POST /calendar/events` → refresh calendar

### Phase 3: AI Panel & Features
1. **AI Chat Interface**:
   - Preserve existing chat functionality from current dashboard
   - Style for sidebar layout
   - Handle permission errors with reauthorization prompts

2. **Today's Events Summary**:
   - Call `/calendar/events?date=today`
   - Display condensed list in right panel

3. **Upcoming Tasks**:
   - Start with localStorage-based task management
   - Consider future integration with task management APIs

### Phase 4: Navigation & Settings
1. **Sidebar Navigation**:
   - Dashboard → main calendar view (current page)
   - Calendar → detailed calendar view (same page, different view mode)
   - Tasks → task management (future feature)
   - Settings → link to `/settings/`

2. **Settings Integration**:
   - Preserve existing settings pages
   - Add calendar-specific settings (default view, notification preferences)
   - Google Calendar connection status with reauthorization

## Testing Strategy for UI Redesign

### Preserve Existing Tests:
- `tests/test_auth.py` - Authentication flows
- `tests/test_google_auth.py` - Google OAuth
- `tests/test_google_calendar.py` - Calendar API integration
- `tests/test_chat.py` - AI chat endpoint
- `tests/test_ai_assistant.py` - AI assistant functionality

### Add New UI Tests:
```python
def test_dashboard_calendar_grid_loads():
    # Test calendar grid renders with events
    
def test_new_event_modal_creation():
    # Test event creation modal workflow
    
def test_ai_panel_permission_error_handling():
    # Test reauthorization prompts in UI
```

## Key Implementation Files

### Files to Modify Heavily:
- `app/templates/dashboard.html` → **Complete replacement** with three-column layout
- `app/static/css/style.css` → **Major modifications** for new layout system
- `app/templates/base.html` → **Minor updates** for CSS Grid and navigation

### Files to Keep/Extend:
- `app/calendar/__init__.py` → **Extend** with availability endpoint alias
- `app/google_calendar.py` → **Extend** permission error responses
- `app/ai_assistant.py` → **Keep** as-is, working well
- All `tests/` → **Preserve** and extend with UI tests

### New Files to Create:
- `app/templates/calendar/` → Calendar-specific templates if needed
- `app/static/js/calendar.js` → Calendar grid JavaScript (if custom implementation)

## Security & Production Considerations

### Maintain Security Patterns:
- CSRF protection on all forms (preserved in base.html meta tags)
- Rate limiting on calendar endpoints
- Secure token storage and refresh for Google OAuth
- Input validation on event creation

### Environment Variables (unchanged):
```bash
SECRET_KEY=<32-byte-hex>
SECURITY_PASSWORD_SALT=<32-byte-hex>
DATABASE_URL=postgresql://...
GOOGLE_CLIENT_ID=<google-oauth-client>
GOOGLE_CLIENT_SECRET=<google-oauth-secret>
MAIL_SERVER=smtp.example.com
```

### Production Deployment:
- Use existing Docker setup (`docker-compose.prod.yml`)
- Gunicorn configuration unchanged
- Nginx reverse proxy configuration preserved

## Documentation References

- **Mission Plan**: `docs/calendar_ui_mission.md` - Detailed implementation steps
- **Project Structure**: `docs/project_structure.md` - Complete file organization
- **Google Setup**: `docs/google_auth_setup.md` - OAuth configuration guide

## Quick Start for UI Development

1. **Understand Current State**: Review current `dashboard.html` and `style.css`
2. **Plan the Redesign**: Follow `docs/calendar_ui_mission.md` step-by-step
3. **Preserve Functionality**: Keep all existing JavaScript API calls
4. **Test Continuously**: Use existing test suite to verify backend integration
5. **Deploy Incrementally**: Test layout → calendar grid → AI panel → navigation
6. **Telegram integration (optional)**: after UI is stable, implement `app/integrations/telegram.py`, add webhook route, and a Settings link to generate linking tokens. Add tests to mock Telegram updates and validate message-to-chat flow.

The goal is a modern, responsive Calendar AI dashboard that integrates seamlessly with the existing robust backend while providing an intuitive three-column interface for calendar management and AI assistance.



## Implementation Checklist

### ✅ Phase 1: Layout Structure (Current Priority)
- [ ] Update `app/templates/base.html` - Remove Bootstrap tabs, add CSS Grid
- [ ] Replace `app/templates/dashboard.html` - Implement three-column layout
- [ ] Update `app/static/css/style.css` - Add calendar dashboard styles
- [ ] Test responsive layout on mobile/desktop

### ✅ Phase 2: Calendar Grid Integration
- [ ] Choose calendar library (FullCalendar.js recommended)
- [ ] Integrate `/calendar/events/range` API
- [ ] Implement monthly navigation and event display
- [ ] Add "New Event" modal with form validation
- [ ] Handle event colors and categorization

### ✅ Phase 3: AI Panel & Features  
- [ ] Adapt existing chat interface for sidebar layout
- [ ] Implement Today's Events summary (call `/calendar/events?date=today`)
- [ ] Add Upcoming Tasks with localStorage persistence
- [ ] Handle permission errors with reauthorization prompts

### ✅ Phase 4: Navigation & Polish
- [ ] Implement sidebar navigation between views
- [ ] Connect Settings link to existing `/settings/` pages
- [ ] Add calendar-specific settings (view preferences)
- [ ] Mobile responsive testing and optimization

## Security Implementation

### Authentication & Password Security
- **Password hashing**: Primary Argon2 (`argon2-cffi`), fallback to Werkzeug PBKDF2
- **User model** includes security tracking: `last_login_at`, `last_login_ip`, `last_password_change_at`
- **Session management**: Flask-Login with secure cookie configuration in production
- **Google OAuth**: Authlib with calendar.events scope and reauthorization flow

### Security Patterns
```python
# User model password methods (app/models.py)
def set_password(self, password: str):
    try:
        from argon2 import PasswordHasher
        ph = PasswordHasher()
        self.password_hash = ph.hash(password)
    except Exception:
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)
    self.last_password_change_at = datetime.utcnow()

# Authentication routes with rate limiting (app/auth/routes.py)
@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('6 per minute')
def login():
    # CSRF protection enabled by default via Flask-WTF
```

### Required Environment Variables
```bash
SECRET_KEY=<32-byte-hex>           # Session security
SECURITY_PASSWORD_SALT=<32-byte-hex>  # Password reset tokens
DATABASE_URL=postgresql://...      # Database connection
GOOGLE_CLIENT_ID=<google-oauth-client> # Google OAuth
GOOGLE_CLIENT_SECRET=<google-oauth-secret> # Google OAuth
MAIL_SERVER=smtp.example.com      # Email configuration
```

### Production Security Settings
- All cookies: `SECURE=True`, `HTTPONLY=True`
- CSRF protection on all POST endpoints
- Rate limiting on sensitive routes (`/auth/login`, `/auth/forgot-password`)
- Password reset tokens expire in 1 hour using `itsdangerous.URLSafeTimedSerializer`

## Development Workflows

### Application Factory Pattern
- Use `create_app(config_name=None)` in `app/__init__.py`
- Extensions initialized in `app/extensions.py`: `db`, `migrate`, `login_manager`, `mail`, `limiter`, `csrf`, `oauth`
- Configuration classes in `app/config.py`: `DevelopmentConfig`, `TestingConfig`, `ProductionConfig`

### Database Operations
```bash
# Generate secret keys
python -c "import secrets; print(secrets.token_hex(32))"

# Database migrations
flask db init       # Initialize migrations (first time)
flask db migrate    # Generate migration
flask db upgrade    # Apply migrations

# Development setup
docker-compose up   # Start PostgreSQL + app
```

### Blueprint Registration
- Authentication blueprint in `app/auth/` (login, Google OAuth, reauthorization)
- Calendar blueprint in `app/calendar/` (events, chat, availability)
- Settings blueprint in `app/settings/` (profile, AI assistant config)
- Routes use decorators: `@login_required`, `@limiter.limit()`, CSRF protection
- Forms use Flask-WTF with validation

### Testing Patterns
```python
# Essential tests (tests/)
def test_user_password_hashing():
    # Test User.set_password() and User.check_password()

def test_login_flow():
    # Test login route returns 302 on success
    # Verify last_login_at is updated

def test_google_calendar_integration():
    # Test calendar API endpoints with mocked Google responses

def test_ai_assistant_tool_calling():
    # Test OpenAI tool calling for event creation
```

## Key Code Patterns

### User Model (app/models.py)
```python
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.extensions import db

class User(db.Model):
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    last_login_at = Column(DateTime)
    last_login_ip = Column(String(45))
    last_password_change_at = Column(DateTime)
    
    # Google Calendar integration
    google_id = Column(String(255), unique=True)
    google_access_token = Column(String(512))
    google_refresh_token = Column(String(512))
    google_token_expires_at = Column(DateTime)
    google_calendar_connected = Column(Boolean, default=False, nullable=False)
    google_permission_mode = Column(String(20), default='events', nullable=False)  # NEW: tracks user permission choice
    
    # AI Assistant settings
    ai_assistant_enabled = Column(Boolean, default=False, nullable=False)
    openai_api_key = Column(String(255))
    ai_model_preference = Column(String(50), default='gpt-4o-mini')
    ai_language_preference = Column(String(10), default='English')

    def set_password(self, password: str):
        # Prefer Argon2 if available
        try:
            from argon2 import PasswordHasher
            ph = PasswordHasher()
            self.password_hash = ph.hash(password)
        except Exception:
            from werkzeug.security import generate_password_hash
            self.password_hash = generate_password_hash(password)
        self.last_password_change_at = datetime.utcnow()

    def check_password(self, password: str) -> bool:
        try:
            from argon2 import PasswordHasher
            ph = PasswordHasher()
            return ph.verify(self.password_hash, password)
        except Exception:
            from werkzeug.security import check_password_hash
            return check_password_hash(self.password_hash, password)
```

### Calendar API Routes (app/calendar/__init__.py)
```python
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app.google_calendar import get_events, create_event, find_available_slots
from app.ai_assistant import create_ai_service_for_user

bp = Blueprint('calendar', __name__, url_prefix='/calendar')

@bp.route('/events', methods=['GET'])
@login_required
def get_events_endpoint():
    """Get calendar events for a specific date."""
    if not current_user.google_calendar_connected:
        return jsonify({'error': 'Google Calendar not connected'}), 400
    
    # Implementation with error handling and timezone support
    
@bp.route('/chat', methods=['POST'])
@login_required 
def chat_message():
    """Handle chat messages for calendar assistant with AI integration."""
    if not current_user.google_calendar_connected:
        return jsonify({'error': 'Google Calendar not connected'}), 400
    
    # AI assistant integration with tool calling for calendar actions
```

## Environment Configuration

Example `.env` file:
```bash
SECRET_KEY=change-me-32-bytes-hex
SECURITY_PASSWORD_SALT=change-me-too-32-bytes
DATABASE_URL=postgresql://user:pass@db:5432/appdb
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USERNAME=you@example.com
MAIL_PASSWORD=super-secret
```

Generate secrets with: `python -c "import secrets; print(secrets.token_hex(32))"`

## Important Security Notes

- Never log secrets or tokens in production
- Never store passwords in plaintext or send via email
- Never commit `.env` files with actual secrets
- Use proper secret management in production (Vault, cloud secrets)
- Implement session server-side storage (Redis) for high-scale deployments
- Google OAuth tokens are automatically refreshed when expired
- Calendar API calls include proper error handling for permission issues

## Calendar AI Features

### Google Calendar Integration
- **OAuth Flow**: `/auth/google/calendar` for initial connection
- **Reauthorization**: `/auth/google/calendar/reauthorize` for scope issues
- **Event Management**: Create, read, delete calendar events
- **Timezone Detection**: Automatic timezone detection with fallback
- **Availability Search**: Find free time slots in calendar

### AI Assistant Capabilities
- **Natural Language Processing**: Parse calendar requests in multiple languages
- **Tool Calling**: Direct calendar event creation via OpenAI function calls
- **Context Awareness**: Uses user's calendar timezone and preferences
- **Error Handling**: Graceful handling of API failures and permission issues

### Frontend Integration
- **Real-time Chat**: WebSocket-style chat interface with AI
- **Calendar Grid**: Interactive monthly calendar view
- **Event Creation**: Modal-based event creation with validation
- **Responsive Design**: Mobile-friendly three-column layout

This architecture provides a production-ready Calendar AI dashboard with robust security, comprehensive testing, and modern UI patterns.

## CURRENT STATUS & NEXT OBJECTIVES

### ✅ COMPLETED FEATURES
- **UI Redesign**: Three-column dashboard layout implemented (sidebar + calendar grid + AI panel)
- **Google Calendar Permission Management**: 
  - Full scope reauthorization flow (`https://www.googleapis.com/auth/calendar`)
  - User permission preference persistence (`User.google_permission_mode`)
  - Permission dropdown in UI with "Accesso completo calendar" option
  - Token revocation before reauthorization to force consent screen
- **Error Handling**: Calendar permission errors detected and reauthorization banner shown
- **AI Assistant Integration**: Tool-calling with structured error responses for permission issues
- **Database Schema**: Migration for `google_permission_mode` column

### 🎯 PRIORITY OBJECTIVE: Code Modularization & Architecture Cleanup

**Goal**: Separate responsibilities and improve testability by extracting Google Calendar integration into modular services.

**Why**: Current monolithic structure in `app/google_calendar.py` and `app/ai_assistant.py` mixes token management, HTTP client logic, domain business rules, and error handling. This makes testing difficult and coupling high.

**Target Architecture**:
```
app/services/
├── google_token.py        # TokenManager: refresh/revoke/ensure_valid_token
├── google_client.py       # GoogleCalendarClient: HTTP wrapper with auth
├── calendar_service.py    # CalendarService: business logic (get_events, create_event, find_slots)
├── ai_service.py         # AIService: OpenAI orchestration with tool calling
└── auth_service.py       # AuthService: connect/reauthorize/disconnect flows
```

**Acceptance Criteria**:
- [ ] `TokenManager` extracted with unit tests (mock `requests.post`)
- [ ] `GoogleCalendarClient` extracted with 200/403 scenario tests
- [ ] `CalendarService` implements domain logic using TokenManager + GoogleClient
- [ ] Existing endpoints maintain same JSON contracts (backward compatibility)
- [ ] Unit test coverage >80% for new service modules
- [ ] No regression in `/calendar/events`, `/calendar/chat`, reauthorization flows

**Migration Plan** (Incremental):
1. **Phase 1**: Extract `TokenManager` (3-6h)
   - Create `app/services/google_token.py`
   - Move `ensure_valid_token`, token refresh logic
   - Add unit tests with mocked HTTP calls
   - Update `app/google_calendar.py` to use TokenManager

2. **Phase 2**: Extract `GoogleCalendarClient` (3-6h)
   - Create `app/services/google_client.py` 
   - Move `make_calendar_request` logic
   - Handle 403 `ACCESS_TOKEN_SCOPE_INSUFFICIENT` detection
   - Add tests for HTTP scenarios

3. **Phase 3**: Extract `CalendarService` (1-2 days)
   - Create `app/services/calendar_service.py`
   - Move domain logic: `get_events`, `create_event`, `find_available_slots`
   - Update blueprint routes to use CalendarService
   - Maintain timezone handling and error propagation

4. **Phase 4**: Extract `AuthService` & cleanup (1-2 days)
   - Move connect/reauthorize/disconnect orchestration
   - Final cleanup of legacy code
   - Documentation and integration tests

### 📋 IMMEDIATE TASKS
- [ ] Implement PoC: `TokenManager` extraction
- [ ] Add unit tests for token refresh scenarios
- [ ] Verify backward compatibility with existing endpoints
- [ ] Create PR template for incremental refactoring

### 🔧 TECHNICAL DEBT TO ADDRESS
- Remove unused imports and dead code after modularization
- Add retry logic and circuit breaker for Google API calls
- Implement proper logging and monitoring for service modules
- Add integration tests with `requests-mock` for full flow coverage
