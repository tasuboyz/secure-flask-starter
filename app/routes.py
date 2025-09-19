from flask import render_template, redirect, url_for
from flask_login import login_required, current_user


def register_routes(app):
    """Register main application routes."""
    
    @app.route('/')
    def index():
        """Home page."""
        if current_user.is_authenticated:
            return redirect(url_for('main.dashboard'))
        return render_template('index.html', title='Benvenuto')
    
    @app.route('/dashboard')
    @login_required
    def dashboard():
        """User dashboard."""
        return render_template('dashboard.html', title='Dashboard', user=current_user)
    
    # Create main blueprint for cleaner organization
    from flask import Blueprint
    main_bp = Blueprint('main', __name__)
    
    @main_bp.route('/')
    def index():
        """Home page."""
        if current_user.is_authenticated:
            return redirect(url_for('main.dashboard'))
        return render_template('index.html', title='Benvenuto')
    
    @main_bp.route('/dashboard')
    @login_required
    def dashboard():
        """User dashboard."""
        return render_template('dashboard.html', title='Dashboard', user=current_user)
    
    app.register_blueprint(main_bp)