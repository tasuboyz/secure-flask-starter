from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from flask_login import UserMixin
from app.extensions import db


class User(UserMixin, db.Model):
    """User model with security features."""
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    
    # Security tracking fields
    last_login_at = Column(DateTime)
    last_login_ip = Column(String(45))
    last_password_change_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.email}>'

    def __init__(self, *args, **kwargs):
        # Ensure Python-side default for is_active so new instances
        # created in tests or in memory have the expected truthy value
        if 'is_active' not in kwargs:
            kwargs['is_active'] = True
        super().__init__(*args, **kwargs)

    def set_password(self, password: str):
        """Set password using Argon2 if available, fallback to Werkzeug."""
        try:
            from argon2 import PasswordHasher
            ph = PasswordHasher()
            self.password_hash = ph.hash(password)
        except Exception:
            from werkzeug.security import generate_password_hash
            self.password_hash = generate_password_hash(password)
        
        self.last_password_change_at = datetime.utcnow()

    def check_password(self, password: str) -> bool:
        """Check password using Argon2 if available, fallback to Werkzeug."""
        try:
            from argon2 import PasswordHasher
            from argon2.exceptions import VerifyMismatchError, VerificationError
            ph = PasswordHasher()
            try:
                # ph.verify returns True or raises VerifyMismatchError
                return ph.verify(self.password_hash, password)
            except VerifyMismatchError:
                # Wrong password
                return False
            except VerificationError:
                # Some other verification error — do not attempt to
                # fallback to Werkzeug on argon2-specific verification errors.
                return False
        except ImportError:
            # Argon2 not available — fallback to Werkzeug's check
            from werkzeug.security import check_password_hash
            return check_password_hash(self.password_hash, password)

    def get_id(self):
        """Return user ID as string for Flask-Login."""
        return str(self.id)

    @property
    def is_authenticated(self):
        """Return True if user is authenticated."""
        return True

    @property
    def is_anonymous(self):
        """Return False as this is a real user."""
        return False

    def get_reset_token(self, expires_sec=3600):
        """Generate password reset token."""
        from itsdangerous import URLSafeTimedSerializer
        from flask import current_app
        
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return s.dumps(
            {'user_id': self.id}, 
            salt=current_app.config['SECURITY_PASSWORD_SALT']
        )

    @staticmethod
    def verify_reset_token(token, expires_sec=3600):
        """Verify password reset token."""
        from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
        from flask import current_app
        
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(
                token, 
                salt=current_app.config['SECURITY_PASSWORD_SALT'],
                max_age=expires_sec
            )
            user_id = data['user_id']
        except (SignatureExpired, BadSignature):
            return None

        # Use Session.get() to avoid SQLAlchemy 2.0 Query.get() deprecation
        return db.session.get(User, user_id)