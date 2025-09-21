import os
from flask import Flask
from dotenv import load_dotenv

from app.config import config
from app.extensions import db, migrate, login_manager, mail, limiter, csrf, oauth


def create_app(config_name=None):
    """Application factory pattern."""
    
    # Load environment variables
    load_dotenv()
    
    # Create Flask app
    app = Flask(__name__)
    
    # Load configuration
    config_name = config_name or os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)

    # Initialize OAuth and register Google provider
    oauth.init_app(app)
    google_client_id = app.config.get('GOOGLE_CLIENT_ID')
    google_client_secret = app.config.get('GOOGLE_CLIENT_SECRET')
    
    if google_client_id and google_client_secret:
        app.logger.info('Registering Google OAuth provider')
        oauth.register(
            name='google',
            client_id=google_client_id,
            client_secret=google_client_secret,
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'},
        )
    else:
        app.logger.warning(f'Google OAuth not configured - client_id: {bool(google_client_id)}, client_secret: {bool(google_client_secret)}')

    # Initialize rate limiter with storage backend from config.
    # If `RATELIMIT_STORAGE_URI` points to Redis, try a quick PING to
    # validate reachability. If Redis isn't reachable, fall back to
    # in-memory storage to avoid runtime ConnectionErrors when handling
    # requests (this improves developer experience).
    storage_uri = app.config.get('RATELIMIT_STORAGE_URI', 'memory://')
    try:
        # If the configured storage looks like Redis, test connectivity
        if isinstance(storage_uri, str) and storage_uri.startswith('redis'):
            try:
                # Import redis here to avoid hard dependency at module import
                # time — if redis isn't installed, we'll fallback to memory.
                import redis as _redis
                # Parse URL and create a short-lived client for a ping.
                # redis.from_url supports redis:// and rediss://
                client = _redis.from_url(storage_uri, socket_connect_timeout=1)
                client.ping()
            except Exception:
                try:
                    app.logger.warning('Redis unreachable at %s, falling back to in-memory rate limit storage', storage_uri)
                except Exception:
                    pass
                app.config['RATELIMIT_STORAGE_URI'] = 'memory://'
                # Initialize limiter — it will read `RATELIMIT_STORAGE_URI` from app.config
                # If Redis was unreachable, prefer to explicitly set an in-memory
                # storage backend to guarantee no redis calls at request time.
                try:
                    from limits.storage import MemoryStorage
                    limiter.storage = MemoryStorage()
                except Exception:
                    # If limits isn't available or something goes wrong, still call init_app
                    pass
                limiter.init_app(app)
    except Exception:
        # Any error here should not prevent the app from starting in dev —
        # fallback to in-memory storage and re-init the limiter.
        try:
            app.logger.warning('Rate limit init failed, falling back to in-memory storage')
        except Exception:
            pass
        app.config['RATELIMIT_STORAGE_URI'] = 'memory://'
        try:
            from limits.storage import MemoryStorage
            limiter.storage = MemoryStorage()
        except Exception:
            pass
        limiter.init_app(app)

    csrf.init_app(app)

    # Initialize Supabase client if configured
    try:
        # Only initialize Supabase if explicitly enabled in config. This
        # prevents attempts to contact Supabase in environments where it's not
        # used (for example CI, local dev without Supabase, or production
        # deployments that don't require Supabase).
        if app.config.get('SUPABASE_ENABLED'):
            from app.supabase import init_supabase
            init_supabase(app)
        else:
            app.logger.debug('Supabase disabled via SUPABASE_ENABLED flag')
    except Exception:
        # If anything goes wrong, don't prevent the app from starting
        app.logger.debug('Supabase init skipped or failed')
    
    # Register user loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        try:
            return db.session.get(User, int(user_id))
        except Exception:
            # Fallback for older SQLAlchemy versions
            return User.query.get(int(user_id))
    
    # Register blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    # Register calendar blueprint
    from app.calendar import bp as calendar_bp
    app.register_blueprint(calendar_bp, url_prefix='/calendar')
    
    # Register settings blueprint
    from app.settings import settings_bp
    app.register_blueprint(settings_bp)
    
    # Register main routes
    from app import routes
    routes.register_routes(app)
    
    return app