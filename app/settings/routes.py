"""Settings routes."""
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.settings import settings_bp
from app.settings.forms import AIAssistantSettingsForm, ProfileSettingsForm
import logging

logger = logging.getLogger(__name__)


@settings_bp.route('/')
@login_required
def index():
    """Settings overview page."""
    return render_template('settings/index.html')


@settings_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Profile settings page."""
    form = ProfileSettingsForm()
    
    if request.method == 'GET':
        form.email.data = current_user.email
    
    if form.validate_on_submit():
        flash('Profile settings saved successfully', 'success')
        return redirect(url_for('settings.profile'))
    
    return render_template('settings/profile.html', form=form)


@settings_bp.route('/ai-assistant', methods=['GET', 'POST'])
@login_required
def ai_assistant():
    """AI Assistant settings page."""
    form = AIAssistantSettingsForm()
    
    if request.method == 'GET':
        # Populate form with current values
        form.ai_assistant_enabled.data = current_user.ai_assistant_enabled
        form.ai_model_preference.data = current_user.ai_model_preference
        # Populate language preference if available
        try:
            form.ai_language.data = current_user.ai_language_preference
        except Exception:
            form.ai_language.data = 'it'
        # Don't populate API key for security
    
    if form.validate_on_submit():
        try:
            # Update user settings
            current_user.ai_assistant_enabled = form.ai_assistant_enabled.data
            current_user.ai_model_preference = form.ai_model_preference.data
            current_user.ai_language_preference = form.ai_language.data
            
            # Only update API key if provided
            if form.openai_api_key.data and form.openai_api_key.data.strip():
                current_user.openai_api_key = form.openai_api_key.data.strip()
                logger.info(f"User {current_user.id} updated OpenAI API key")
            
            db.session.commit()
            flash('AI Assistant settings saved successfully', 'success')
            logger.info(f"User {current_user.id} updated AI assistant settings")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving AI settings for user {current_user.id}: {e}")
            flash('Error saving settings. Please try again.', 'danger')
        
        return redirect(url_for('settings.ai_assistant'))
    
    return render_template('settings/ai_assistant.html', form=form)