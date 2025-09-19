from flask import current_app, url_for
from flask_mail import Message
from app.extensions import mail
import logging


def send_password_reset_email(user):
    """Send password reset email to user."""
    try:
        token = user.get_reset_token()
        
        msg = Message(
            subject='Reset Password - Pro Project',
            sender=current_app.config['MAIL_DEFAULT_SENDER'],
            recipients=[user.email]
        )
        
        reset_url = url_for('auth.reset_password', token=token, _external=True)
        
        msg.body = f'''Ciao,

Hai richiesto un reset della password per il tuo account.

Clicca sul link seguente per reimpostare la password:
{reset_url}

Questo link è valido per 1 ora.

Se non hai richiesto questo reset, ignora questa email.

Saluti,
Il team di Pro Project
'''
        
        msg.html = f'''
        <p>Ciao,</p>
        <p>Hai richiesto un reset della password per il tuo account.</p>
        <p><a href="{reset_url}">Clicca qui per reimpostare la password</a></p>
        <p>Questo link è valido per 1 ora.</p>
        <p>Se non hai richiesto questo reset, ignora questa email.</p>
        <p>Saluti,<br>Il team di Pro Project</p>
        '''
        
        mail.send(msg)
        current_app.logger.info(f'Password reset email sent to {user.email}')
        
    except Exception as e:
        # Log error but don't raise exception to prevent information disclosure
        current_app.logger.error(f'Failed to send password reset email to {user.email}: {str(e)}')
        
        # In development, log the reset URL
        if current_app.config.get('DEBUG'):
            token = user.get_reset_token()
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            current_app.logger.info(f'DEBUG: Password reset URL for {user.email}: {reset_url}')