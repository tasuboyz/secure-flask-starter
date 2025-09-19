from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm, ForgotPasswordForm, ResetPasswordForm
from app.auth.email_utils import send_password_reset_email
from app.extensions import db, limiter
from app.models import User


@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('6 per minute')
def login():
    """Login route with rate limiting."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        
        if user and user.check_password(form.password.data) and user.is_active:
            # Update login tracking
            user.last_login_at = datetime.utcnow()
            user.last_login_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            db.session.commit()
            
            # Log in user
            login_user(user, remember=form.remember_me.data)
            
            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('main.dashboard')
            
            flash('Login effettuato con successo!', 'success')
            return redirect(next_page)
        else:
            flash('Email o password non validi', 'danger')
    
    return render_template('login.html', title='Accedi', form=form)


@bp.route('/register', methods=['GET', 'POST'])
@limiter.limit('3 per minute')
def register():
    """Registration route with rate limiting."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Create new user
        user = User(email=form.email.data.lower())
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registrazione completata! Ora puoi accedere.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html', title='Registrati', form=form)


@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Logout route (POST only for CSRF protection)."""
    logout_user()
    flash('Logout effettuato con successo.', 'info')
    return redirect(url_for('main.index'))


@bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit('3 per minute')
def forgot_password():
    """Forgot password route with rate limiting."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        
        # Always show success message to prevent email enumeration
        if user:
            send_password_reset_email(user)
        
        flash('Se l\'email esiste nel sistema, riceverai le istruzioni per il reset.', 'info')
        return redirect(url_for('auth.login'))
    
    return render_template('forgot_password.html', title='Reset Password', form=form)


@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
@limiter.limit('3 per minute')
def reset_password(token):
    """Reset password with token verification."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    user = User.verify_reset_token(token)
    if not user:
        flash('Token non valido o scaduto.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        
        flash('Password aggiornata con successo!', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('reset_password.html', title='Reset Password', form=form)