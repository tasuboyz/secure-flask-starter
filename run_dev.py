"""Run the app in development mode with SQLite as the database.

This script sets sensible defaults for local development so you don't need
to run Postgres or Redis. It sets `DATABASE_URL` to `sqlite:///instance/app.db`
and enables Flask debug mode.

Usage (PowerShell):
    .venv\Scripts\python.exe run_dev.py

"""
import os
import pathlib
import sys
from app import create_app

# Ensure instance directory exists (create parent dirs if needed)
instance_path = pathlib.Path('instance')
instance_path.mkdir(parents=True, exist_ok=True)

# Compute an absolute SQLite path to avoid 'unable to open database file' on Windows
db_file = instance_path / 'app.db'
abs_db_uri = f"sqlite:///{db_file.resolve()}"

# Set environment variables if not already set
os.environ.setdefault('FLASK_ENV', 'development')
os.environ.setdefault('FLASK_APP', 'run.py')
os.environ.setdefault('DATABASE_URL', abs_db_uri)

app = create_app()

if __name__ == '__main__':
    # Debug True for development convenience
    try:
        app.run(debug=True, host='127.0.0.1', port=5000)
    except Exception:
        # Print exception to stderr for debugging
        import traceback
        traceback.print_exc(file=sys.stderr)
        raise
