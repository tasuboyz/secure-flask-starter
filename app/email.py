from flask import current_app, render_template
from threading import Thread
from app.extensions import mail
from flask_mail import Message
import logging


def _send_async_email(app, msg):
    """Send email in a background thread (development/low-volume)."""
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            current_app.logger.error('Async email send failed: %s', str(e))


def send_email(to, subject, template_name=None, context=None, html=None, cc=None, bcc=None, sender=None):
    """Send an email synchronously using Flask-Mail.

    - `to`: str or list
    - `template_name`: template basename (without extension) under `templates/emails/`
    - `context`: dict for rendering template
    """
    app = current_app._get_current_object()

    recipients = to if isinstance(to, (list, tuple)) else [to]

    sender_addr = sender or app.config.get('MAIL_DEFAULT_SENDER')

    msg = Message(subject=subject, sender=sender_addr, recipients=recipients, cc=cc, bcc=bcc)

    # Render text/html from templates if provided
    if template_name:
        context = context or {}
        try:
            msg.html = render_template(f'emails/{template_name}.html', **context)
        except Exception:
            # if HTML template not found, ignore
            msg.html = None
        try:
            msg.body = render_template(f'emails/{template_name}.txt', **context)
        except Exception:
            msg.body = None

    if html:
        msg.html = html

    try:
        mail.send(msg)
        app.logger.info('Email sent to %s (subject=%s)', recipients, subject)
        return True
    except Exception as e:
        app.logger.error('Failed to send email to %s: %s', recipients, str(e))
        return False


def send_email_async(*args, **kwargs):
    """Enqueue an email send operation in a background thread (dev helper)."""
    app = current_app._get_current_object()
    msg_kwargs = kwargs.copy()

    # Build Message object synchronously to pass to thread
    to = args[0] if args else msg_kwargs.get('to')
    subject = args[1] if len(args) > 1 else msg_kwargs.get('subject')
    template_name = msg_kwargs.get('template_name')
    context = msg_kwargs.get('context')

    recipients = to if isinstance(to, (list, tuple)) else [to]
    sender_addr = msg_kwargs.get('sender') or app.config.get('MAIL_DEFAULT_SENDER')

    msg = Message(subject=subject, sender=sender_addr, recipients=recipients)
    if template_name:
        try:
            msg.html = render_template(f'emails/{template_name}.html', **(context or {}))
        except Exception:
            msg.html = None
        try:
            msg.body = render_template(f'emails/{template_name}.txt', **(context or {}))
        except Exception:
            msg.body = None

    thr = Thread(target=_send_async_email, args=(app, msg))
    thr.daemon = True
    thr.start()
    return True
