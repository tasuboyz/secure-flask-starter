from app.email import send_email, send_email_async


def test_send_email_sync(client, app):
    # Configure a simple sender in test config
    with app.app_context():
        result = send_email('test@example.com', 'Test Subject', template_name=None, html='<p>hi</p>')
        assert result is True


def test_send_email_async(client, app):
    with app.app_context():
        result = send_email_async('test@example.com', 'Async Subject', template_name=None, context=None)
        assert result is True
