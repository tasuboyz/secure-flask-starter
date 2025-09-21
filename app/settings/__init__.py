"""Settings blueprint for user preferences."""
from flask import Blueprint

settings_bp = Blueprint('settings', __name__, url_prefix='/settings', template_folder='templates')

from . import routes