from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from authlib.integrations.flask_client import OAuth

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
oauth = OAuth()
# Create a Limiter instance that will be initialized with the app.
# The actual storage backend (Redis or in-memory) is chosen during
# app initialization so we can gracefully fall back to in-memory
# rate limiting when Redis is not available in the local/dev env.
limiter = Limiter(key_func=get_remote_address)
csrf = CSRFProtect()

# Configure login manager
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Devi effettuare il login per accedere a questa pagina.'
login_manager.login_message_category = 'info'