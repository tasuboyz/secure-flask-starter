import os
from datetime import timedelta


class Config:
    """Base configuration class."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-me'
    SECURITY_PASSWORD_SALT = os.environ.get('SECURITY_PASSWORD_SALT') or 'dev-salt-change-me'
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Mail settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'localhost'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'false').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@example.com'
    
    # Security settings
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    AUTH_TEMPLATE_VARIANT = os.environ.get('AUTH_TEMPLATE_VARIANT', 'modern')
    
    # Rate limiting
    RATELIMIT_STORAGE_URI = os.environ.get('REDIS_URL') or 'memory://'
    
    # Google OAuth
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    
    # Less strict security for development
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = False
    REMEMBER_COOKIE_HTTPONLY = True
    SESSION_PROTECTION = 'strong'


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Disable rate limiting for tests
    RATELIMIT_ENABLED = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    
    # Strict security for production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True
    SESSION_PROTECTION = 'strong'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
    
    # Force HTTPS
    PREFERRED_URL_SCHEME = 'https'


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}