"""Forms for user settings."""
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SelectField, SubmitField, PasswordField
from wtforms.validators import Optional, Length
from wtforms.widgets import PasswordInput


class PasswordFieldWithToggle(StringField):
    """Custom password field that can be toggled to show/hide."""
    widget = PasswordInput(hide_value=False)


class AIAssistantSettingsForm(FlaskForm):
    """Form for AI Assistant settings."""
    openai_api_key = PasswordFieldWithToggle(
        'OpenAI API Key',
        validators=[Optional(), Length(max=512)],
        description='Your personal OpenAI API key for the AI assistant',
        render_kw={"placeholder": "sk-..."}
    )
    
    ai_assistant_enabled = BooleanField(
        'Enable AI Assistant',
        description='Enable the AI assistant features'
    )
    
    ai_model_preference = SelectField(
        'AI Model',
        choices=[
            ('gpt-3.5-turbo', 'GPT-3.5 Turbo (Faster, cheaper)'),
            ('gpt-4', 'GPT-4 (More capable, slower)'),
            ('gpt-4-turbo-preview', 'GPT-4 Turbo (Latest, balanced)'),
        ],
        default='gpt-3.5-turbo',
        description='Choose the AI model to use'
    )
    
    submit = SubmitField('Save Settings')


class ProfileSettingsForm(FlaskForm):
    """Form for basic profile settings."""
    email = StringField(
        'Email',
        validators=[Optional(), Length(max=255)],
        render_kw={"readonly": True},
        description='Your email address (cannot be changed)'
    )
    
    submit = SubmitField('Save Profile')