# AI Agent Instructions# AI Agent Instructions



This project implements a production-ready Flask web application with secure authentication. These instructions help AI coding agents understand the project's architecture, patterns, and development workflows.This project implements a production-ready Flask web application with secure authentication. These instructions help AI coding agents understand the project's architecture, patterns, and development workflows.



## Project Architecture## Project Architecture



### Tech Stack### Tech Stack

- **Backend**: Python 3.11+ with Flask (application factory pattern)- **Backend**: Python 3.11+ with Flask (application factory pattern)

- **Database**: SQLAlchemy with Flask-SQLAlchemy ORM, Alembic migrations- **Database**: SQLAlchemy with Flask-SQLAlchemy ORM, Alembic migrations

- **Authentication**: Flask-Login + optional OAuth via Flask-Dance- **Authentication**: Flask-Login + optional OAuth via Flask-Dance

- **Security**: Argon2 password hashing, Flask-WTF CSRF protection, flask-limiter rate limiting- **Security**: Argon2 password hashing, Flask-WTF CSRF protection, flask-limiter rate limiting

- **Email**: Flask-Mail for password reset functionality- **Email**: Flask-Mail for password reset functionality

- **Testing**: pytest with application/database fixtures- **Testing**: pytest with application/database fixtures



### Directory Structure### Directory Structure

``````

app/app/

├── __init__.py          # Application factory with create_app()├── __init__.py          # Application factory with create_app()

├── config.py           # Environment-specific configurations (Dev/Test/Prod)├── config.py           # Environment-specific configurations (Dev/Test/Prod)

├── extensions.py       # Global extension instances├── extensions.py       # Global extension instances

├── models.py          # User model with security features├── models.py          # User model with security features

├── auth/              # Authentication blueprint├── auth/              # Authentication blueprint

│   ├── routes.py      # Login/logout/password reset endpoints│   ├── routes.py      # Login/logout/password reset endpoints

│   ├── forms.py       # WTForms with validation│   ├── forms.py       # WTForms with validation

│   ├── email_utils.py # Mail utilities│   ├── email_utils.py # Mail utilities

│   └── templates/     # Auth-specific templates│   └── templates/     # Auth-specific templates

├── templates/         # Jinja2 templates├── templates/         # Jinja2 templates

├── static/           # CSS/JS/images├── static/           # CSS/JS/images

└── scripts/          # Admin utilities and key generation└── scripts/          # Admin utilities and key generation

migrations/           # Alembic database migrationsmigrations/           # Alembic database migrations

tests/               # pytest test suitetests/               # pytest test suite

``````



## Security Implementation## Security Implementation



### Authentication & Password Security### Authentication & Password Security

- **Password hashing**: Primary Argon2 (`argon2-cffi`), fallback to Werkzeug PBKDF2- **Password hashing**: Primary Argon2 (`argon2-cffi`), fallback to Werkzeug PBKDF2

- **User model** includes security tracking: `last_login_at`, `last_login_ip`, `last_password_change_at`- **User model** includes security tracking: `last_login_at`, `last_login_ip`, `last_password_change_at`

- **Session management**: Flask-Login with secure cookie configuration in production- **Session management**: Flask-Login with secure cookie configuration in production



### Security Patterns

```python```python

# User model password methods (app/models.py)# User model password methods (app/models.py)

def set_password(self, password: str):
    try:
        from argon2 import PasswordHasher
        ph = PasswordHasher()
        self.password_hash = ph.hash(password)        self.password_hash = ph.hash(password)

    except Exception:
        from werkzeug.security import generate_password_hash

        self.password_hash = generate_password_hash(password)
    self.last_password_change_at = datetime.utcnow()



# Authentication routes with rate limiting (app/auth/routes.py)# Authentication routes with rate limiting (app/auth/routes.py)

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('6 per minute')
def login():

    # CSRF protection enabled by default via Flask-WTF 

```



### Required Environment Variables### Required Environment Variables

```bash
SECRET_KEY=<32-byte-hex>           # Session security
SECURITY_PASSWORD_SALT=<32-byte-hex>  # Password reset tokens

DATABASE_URL=postgresql://...      # Database connection
MAIL_SERVER=smtp.example.com      # Email configuration

``````



### Production Security Settings### Production Security Settings

- All cookies: `SECURE=True`, `HTTPONLY=True`

- CSRF protection on all POST endpoints
- Rate limiting on sensitive routes (`/auth/login`, `/auth/forgot-password`)
- Password reset tokens expire in 1 hour using `itsdangerous.URLSafeTimedSerializer`


## Development Workflows## Development Workflows


### Application Factory Pattern### Application Factory Pattern

- Use `create_app(config_name=None)` in `app/__init__.py`
- Extensions initialized in `app/extensions.py`: `db`, `migrate`, `login_manager`, `mail`, `limiter`, `csrf`
- Configuration classes in `app/config.py`: `DevelopmentConfig`, `TestingConfig`, `ProductionConfig`


### Database Operations### Database Operations

```bash
flask db init       # Initialize migrations (first time)
flask db migrate    # Generate migration
flask db upgrade    # Apply migrations
```bash

# Generate secret keys# Generate secret keys

python -c "import secrets; print(secrets.token_hex(32))"

# Database migrations# Database migrations

flask db init       # Initialize migrations (first time)
flask db migrate    # Generate migration
flask db upgrade    # Apply migrations

```


# Development setup# Development setup

docker-compose up   # Start PostgreSQL + app

```


### Blueprint Registration

- Authentication blueprint in `app/auth/`
- Routes use decorators: `@login_required`, `@limiter.limit()`, CSRF protection
- Forms use Flask-WTF with validation in `app/auth/forms.py`


### Testing Patterns

```python

# Essential tests (tests/)
def test_user_password_hashing():
    # Test User.set_password() and User.check_password()
    user = User(email='test@example.com')
    user.set_password('password123')
    assert user.check_password('password123')
    assert not user.check_password('wrongpassword')


def test_login_flow():

    # Test login route returns 302 on success
    response = client.post('/auth/login', data={
        'email': 'test@example.com',
        'password': 'password123'
    })
    assert response.status_code == 302

    # Verify last_login_at is updated
    user = User.query.filter_by(email='test@example.com').first()
    assert user.last_login_at is not None

```

## Key Code Patterns

### User Model (app/models.py)

```python
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime

from app.extensions import dbfrom app.extensions import db

class User(db.Model):

    id = Column(Integer, primary_key=True)

    email = Column(String(255), unique=True, index=True, nullable=False)

    password_hash = Column(String(255), nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)

    is_admin = Column(Boolean, default=False, nullable=False)

    last_login_at = Column(DateTime)

    last_login_ip = Column(String(45))

    last_password_change_at = Column(DateTime)

    def set_password(self, password: str):

        # Prefer Argon2 if available
        try:

            from argon2 import PasswordHasher
            ph = PasswordHasher()

            self.password_hash = ph.hash(password)            self.password_hash = ph.hash(password)

        except Exception:
            from werkzeug.security import generate_password_hash            from werkzeug.security import generate_password_hash

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

### Authentication Routes (app/auth/routes.py)### Authentication Routes (app/auth/routes.py)

```python
from flask import Blueprint, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.auth.forms import LoginForm
from app.extensions import db, limiter

from app.models import Userfrom app.models import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('6 per minute')

def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            user.last_login_at = datetime.utcnow()

            user.last_login_ip = request.remote_addr
            db.session.commit()
            return redirect(url_for('dashboard.index'))

        flash('Invalid credentials', 'danger')

    return render_template('auth/login.html', form=form)

```

## Environment ConfigurationTesting minimo

--------------

```



## Environment ConfigurationTesting minimo

--------------

Example `.env` file:- Testare `User.set_password` / `User.check_password` (happy + wrong password)

```bash
SECRET_KEY=change-me-32-bytes-hex
SECURITY_PASSWORD_SALT=change-me-too-32-bytes
DATABASE_URL=postgresql://user:pass@db:5432/appdb
```



## Environment ConfigurationTesting minimo

```bash
SECRET_KEY=change-me-32-bytes-hex
SECURITY_PASSWORD_SALT=change-me-too-32-bytes
DATABASE_URL=postgresql://user:pass@db:5432/appdb
--------------

Example `.env` file:- Testare `User.set_password` / `User.check_password` (happy + wrong password)

```



## Environment ConfigurationTesting minimo

--------------

Example `.env` file:- Testare `User.set_password` / `User.check_password` (happy + wrong password)

```bash
# Testare che il login route ritorni 302 su successo e che `last_login_at` sia impostato.

SECRET_KEY=change-me-32-bytes-hex

SECURITY_PASSWORD_SALT=change-me-too-32-bytes
DATABASE_URL=postgresql://user:pass@db:5432/appdb

MAIL_SERVER=smtp.example.com
SECRET_KEY=change-me-32-bytes-hex
MAIL_PORT=587
SECURITY_PASSWORD_SALT=change-me-too-32-bytes
MAIL_USERNAME=you@example.com

DATABASE_URL=postgresql://user:pass@db:5432/appdb

MAIL_PASSWORD=super-secret
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USERNAME=you@example.com

Generate secrets with: `python -c "import secrets; print(secrets.token_hex(32))"`MAIL_PASSWORD=super-secret



## Important Security NotesCosa non fare

-------------

- Never log secrets or tokens in production- Non usare `print` per secret o token su log in produzione.

- Never store passwords in plaintext or send via email- Non memorizzare password in chiaro né inviarle via email.

- Never commit `.env` files with actual secrets- Non commitare `.env` o file con segreti.

- Use proper secret management in production (Vault, cloud secrets)

- Implement session server-side storage (Redis) for high-scale deploymentsOutput atteso dalla scaffolding request
-------------------------------------
- Repo con struttura file come sopra, funzionante in sviluppo con `docker-compose up` (Postgres+app), e con test base.
- Documentazione `README.md` che spiega come creare segreti, migrare DB e avviare in dev/prod.

Note finali
-----------
Questo prompt è pensato per generare un progetto solido e minimo che segua le best practice per autenticazione e la sicurezza. Puoi estendere l'implementazione con 2FA, SSO, o session store server-side quando il prodotto richiederà maggiori garanzie.
