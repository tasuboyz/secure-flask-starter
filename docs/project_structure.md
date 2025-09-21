# Secure Flask Starter - Project Structure

This document provides a complete overview of the project structure for the Calendar AI Dashboard application.

## Root Directory Structure

```
secure-flask-starter/
├── .env.example                           # Environment variables template
├── .github/
│   └── copilot-instructions.md            # AI agent development instructions
├── .gitignore                             # Git ignore patterns
├── docker-compose.yml                     # Development container setup
├── docker-compose.prod.yml                # Production container setup
├── Dockerfile                             # Development Docker image
├── Dockerfile.prod                        # Production Docker image
├── gunicorn_config.py                     # Gunicorn WSGI server config
├── pytest.ini                             # Pytest configuration
├── README.md                              # Project documentation
├── requirements.txt                       # Python dependencies
├── run_dev.py                             # Development server entry point
├── run.py                                 # Production server entry point
└── client_secret_*.json                   # Google OAuth credentials (ignored in git)
```

## Application Structure (`app/`)

```
app/
├── __init__.py                            # Application factory (create_app)
├── config.py                              # Environment-specific configurations
├── extensions.py                          # Global extension instances
├── models.py                              # SQLAlchemy User model
├── routes.py                              # Main application routes
├── ai_assistant.py                        # OpenAI Responses API integration
├── google_calendar.py                     # Google Calendar API utilities
├── supabase.py                            # Supabase integration (optional)
├── auth/                                  # Authentication blueprint
│   ├── __init__.py                        # Blueprint registration
│   ├── routes.py                          # Auth routes (login, OAuth, reauth)
│   ├── forms.py                           # WTForms for auth
│   ├── email_utils.py                     # Password reset emails
│   └── templates/                         # Auth-specific templates
│       ├── login.html                     # Login form
│       ├── register.html                  # Registration form
│       ├── forgot_password.html           # Password reset request
│       └── reset_password.html            # Password reset form
├── calendar/                              # Calendar blueprint
│   └── __init__.py                        # Calendar API endpoints & chat
├── settings/                              # Settings blueprint
│   ├── __init__.py                        # Blueprint registration
│   ├── routes.py                          # Settings routes
│   ├── forms.py                           # Settings forms
│   └── templates/settings/                # Settings templates
│       ├── index.html                     # Settings overview
│       ├── profile.html                   # User profile settings
│       └── ai_assistant.html              # AI configuration
├── scripts/                               # Admin utilities
│   ├── create_admin.py                    # Create admin user
│   └── generate_secrets.py                # Generate secret keys
├── static/                                # Static assets
│   └── css/
│       └── style.css                      # Application styles
└── templates/                             # Global templates
    ├── base.html                          # Base template with nav/footer
    ├── index.html                         # Landing page
    └── dashboard.html                     # Main dashboard (current tabs UI)
```

## Database & Migrations (`migrations/`)

```
migrations/
├── alembic.ini                            # Alembic configuration
├── env.py                                 # Migration environment
├── README                                 # Migration instructions
├── script.py.mako                         # Migration template
└── versions/                              # Database migration files
    ├── cabd280c39d5_initial_migration_sqlite.py
    ├── 4d53b6a79454_add_ai_assistant_settings_fields.py
    └── 5c69053ed761_add_ai_assistant_settings_with_defaults.py
```

## Tests (`tests/`)

```
tests/
├── conftest.py                            # Pytest fixtures (app, client, user, db)
├── test_auth.py                           # Authentication tests
├── test_models.py                         # User model tests
├── test_google_auth.py                    # Google OAuth tests
├── test_google_calendar.py                # Calendar integration tests
├── test_ai_assistant.py                   # AI assistant tests
├── test_ai_tool_calls.py                  # Tool-calling flow tests
└── test_chat.py                           # Chat endpoint tests (CSRF bypass)
```

## Documentation (`docs/`)

```
docs/
├── calendar_ui_mission.md                 # UI redesign mission plan
├── project_structure.md                   # This document
├── google_auth_setup.md                   # Google OAuth setup guide
├── google_calendar_assistant.md           # Calendar AI features
├── gunicorn.md                            # Production deployment
├── production_setup.md                    # Server deployment guide
└── project_ideas.md                       # Feature roadmap
```

## Deployment (`deploy/`)

```
deploy/
├── gunicorn.service                       # Systemd service file
└── nginx.conf                            # Nginx reverse proxy config
```

## Instance (`instance/`)

```
instance/
└── app.db                                 # SQLite database (development)
```

## Key File Responsibilities

### Core Application Files

- **`app/__init__.py`**: Application factory with create_app(), extension initialization, blueprint registration
- **`app/config.py`**: Environment configurations (Development, Testing, Production)
- **`app/extensions.py`**: Global instances (db, migrate, login_manager, mail, oauth, limiter, csrf)
- **`app/models.py`**: User model with security features, Google tokens, AI settings

### Authentication & Security

- **`app/auth/routes.py`**: Login/logout, Google OAuth, calendar connect/reauthorize
- **`app/auth/forms.py`**: WTForms with CSRF protection and validation
- **`app/auth/email_utils.py`**: Password reset email utilities

### Calendar Integration

- **`app/calendar/__init__.py`**: Calendar API endpoints (events, slots, chat)
- **`app/google_calendar.py`**: Google Calendar API wrappers, token management, timezone detection
- **`app/ai_assistant.py`**: OpenAI Responses API with tool-calling for calendar actions

### Settings & Configuration

- **`app/settings/routes.py`**: User profile, AI assistant configuration
- **`app/settings/forms.py`**: Settings forms with validation

### Frontend

- **`app/templates/base.html`**: Base layout with navigation, CSRF meta tags
- **`app/templates/dashboard.html`**: Current tabbed dashboard UI (to be redesigned)
- **`app/static/css/style.css`**: Modern responsive styles
 - Mobile-first: UI must be implemented mobile-first. The three-column layout should collapse to a stacked/drawer layout on small viewports; consider adding `app/static/js/drawer.js` for off-canvas behavior.

### Development & Testing

- **`run_dev.py`**: Development server with debug mode
- **`tests/conftest.py`**: Pytest fixtures for app, database, users
- **`pytest.ini`**: Test configuration and markers

### Deployment

- **`docker-compose.yml`**: Development environment (PostgreSQL + app)
- **`gunicorn_config.py`**: Production WSGI server configuration
- **`requirements.txt`**: Python dependencies

## Architecture Patterns

### Application Factory Pattern
- `create_app(config_name=None)` in `app/__init__.py`
- Configuration classes in `app/config.py`
- Extension initialization in `app/extensions.py`

### Blueprint Organization
- **auth**: Authentication and OAuth (`/auth/`)
- **calendar**: Calendar API and chat (`/calendar/`)
- **settings**: User settings (`/settings/`)
- **main**: Core routes (`/`, `/dashboard`)

### Security Implementation
- Argon2 password hashing with Werkzeug fallback
- Flask-WTF CSRF protection on all forms
- Flask-Limiter rate limiting on sensitive endpoints
- Secure session management with Flask-Login
- Environment-based configuration for secrets

### Database Design
- SQLAlchemy ORM with Flask-SQLAlchemy
- Alembic migrations for schema changes
- User model with security tracking fields
- Google OAuth token storage with refresh capability

### Testing Strategy
- Pytest with application and database fixtures
- Authentication flow testing
- Google OAuth mocking and integration tests
- AI assistant tool-calling validation
- CSRF bypass for API endpoint testing

## Environment Configuration

### Required Environment Variables
```bash
SECRET_KEY=<32-byte-hex>                   # Session security
SECURITY_PASSWORD_SALT=<32-byte-hex>       # Password reset tokens
DATABASE_URL=postgresql://...              # Database connection
GOOGLE_CLIENT_ID=<google-oauth-client>     # Google OAuth
GOOGLE_CLIENT_SECRET=<google-oauth-secret> # Google OAuth
MAIL_SERVER=smtp.example.com               # Email configuration
```

### Optional Environment Variables
```bash
SUPABASE_ENABLED=true                      # Enable Supabase integration
RATELIMIT_STORAGE_URI=redis://...          # Redis for rate limiting
TELEGRAM_BOT_TOKEN=<bot-token>              # Telegram Bot API token (required for Telegram integration)
TELEGRAM_WEBHOOK_SECRET=<secret>            # Secret for webhook path or HMAC validation (recommended)
```

## Development Workflow

1. **Environment Setup**: Copy `.env.example` to `.env` and configure
2. **Database**: `flask db upgrade` to apply migrations
3. **Development Server**: `python run_dev.py` for local development
4. **Testing**: `pytest` to run the test suite
5. **Production**: `docker-compose -f docker-compose.prod.yml up` for production deployment

This structure supports a production-ready Flask application with secure authentication, Google Calendar integration, AI assistant capabilities, and comprehensive testing coverage.