"""Send a test email using the app's send_email helper.

Usage:
  python scripts/send_test_email.py [recipient] [--verbose]

Reads mail config from environment variables. If recipient is not provided, reads TEST_EMAIL env var.
This script prints detailed output and traceback on failure to ease debugging.
"""
import sys
import os
import argparse
import traceback
from pathlib import Path

# Ensure project root is on sys.path so `from app import create_app` works
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
  sys.path.insert(0, str(project_root))

from app import create_app


def mask_secret(s):
  if not s:
    return None
  if len(s) <= 4:
    return '****'
  return s[:2] + '****' + s[-2:]


def main():
  parser = argparse.ArgumentParser(description='Send a test email using the app email helper')
  parser.add_argument('recipient', nargs='?', help='Recipient email address')
  parser.add_argument('--verbose', '-v', action='store_true', help='Show verbose output')
  args = parser.parse_args()

  recipient = args.recipient or os.environ.get('TEST_EMAIL')
  if not recipient:
    print('Usage: python scripts/send_test_email.py recipient@example.com')
    sys.exit(1)

  env = os.environ.get('FLASK_ENV', 'development')
  app = create_app(env)

  with app.app_context():
    # Print a summary of mail config (never print password)
    mail_cfg = {
      'MAIL_PROVIDER': app.config.get('MAIL_PROVIDER'),
      'MAIL_SERVER': app.config.get('MAIL_SERVER'),
      'MAIL_PORT': app.config.get('MAIL_PORT'),
      'MAIL_USE_TLS': app.config.get('MAIL_USE_TLS'),
      'MAIL_USE_SSL': app.config.get('MAIL_USE_SSL'),
      'MAIL_USERNAME': app.config.get('MAIL_USERNAME'),
      'MAIL_DEFAULT_SENDER': app.config.get('MAIL_DEFAULT_SENDER'),
    }

    print('Environment:', env)
    print('Mail config:')
    for k, v in mail_cfg.items():
      if k == 'MAIL_USERNAME' and v:
        print(f'  {k}: {mask_secret(v)}')
      else:
        print(f'  {k}: {v}')

    from app.email import send_email
    try:
      print(f"Sending test email to: {recipient}")
      ok = send_email(recipient, 'Test email from secure-flask-starter', html='<p>Questo è un test.</p>')
      print('Send result:', ok)
      if not ok:
        print('send_email returned False; check application logs for details')
        sys.exit(2)
    except Exception as e:
      print('Exception while sending email:')
      traceback.print_exc()
      sys.exit(3)


if __name__ == '__main__':
  main()
