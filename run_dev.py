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
from app.extensions import db

# Ensure instance directory exists (create parent dirs if needed)
instance_path = pathlib.Path('instance')
instance_path.mkdir(parents=True, exist_ok=True)

# Compute an absolute SQLite path to avoid 'unable to open database file' on Windows
db_file = instance_path / 'app.db'
abs_db_uri = f"sqlite:///{db_file.resolve()}"

# Force environment variables for development
os.environ['FLASK_ENV'] = 'development'
os.environ['FLASK_APP'] = 'run.py'
# Force the app to use local SQLite in development to avoid trying to connect to Postgres
os.environ['DATABASE_URL'] = abs_db_uri

app = create_app()

if __name__ == '__main__':
    # Debug True for development convenience
    try:
        # Ensure database tables exist for local development. This makes it
        # easier for contributors who don't run migrations: when using the
        # bundled SQLite instance, create all tables if missing.
        with app.app_context():
            # Create parent dir for sqlite file just in case
            db_path = db.engine.url.database
            if db_path:
                db_dir = pathlib.Path(db_path).parent
                db_dir.mkdir(parents=True, exist_ok=True)
            db.create_all()

        app.run(debug=True, host='127.0.0.1', port=5000)
    except Exception:
        # Print exception to stderr for debugging
        import traceback
        traceback.print_exc(file=sys.stderr)
        raise
