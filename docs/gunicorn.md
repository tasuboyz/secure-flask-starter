# Running with Gunicorn

This document explains how to run the Flask application with Gunicorn in development and production. Gunicorn is a production-ready WSGI HTTP server for UNIX. On Windows, prefer the built-in Flask dev server for local development and use a Linux-based production host (VM/container) for Gunicorn.

## Why Gunicorn

- Handles multiple workers and concurrency models (sync/async/eventlet/gevent)
- Integrates well with process supervisors (systemd, supervisord)
- Works cleanly behind a reverse-proxy like Nginx

## Install Gunicorn

Activate your virtualenv and install Gunicorn (and optionally gevent):

```bash
.venv/bin/activate
pip install gunicorn
# Optional for async workers
pip install gevent
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
pip install gunicorn
```

> Note: Gunicorn does not run on native Windows. Use a Linux VM/container for production Gunicorn.

## Quick development run (Linux/macOS)

From project root (recommended to use a separate virtualenv for production):

```bash
export FLASK_APP=run.py
export FLASK_ENV=development
export DATABASE_URL=sqlite:///instance/app.db
gunicorn -w 1 -b 127.0.0.1:8000 run:app
```

- `-w 1`: single worker for simple testing; in production you should increase workers.
- `run:app` references the `app` callable exported by `run.py` (or `app/__init__.py` create_app pattern if used differently).

## Recommended Gunicorn configuration for production

A good base command (tune values to your CPU/RAM and load):

```bash
# Example: 3 workers, 2 threads per worker
gunicorn -w 3 --threads 2 -k gthread -b 127.0.0.1:8000 run:app \
  --timeout 30 --keep-alive 2 --log-level info --access-logfile - --error-logfile -
```

- Workers: `2 * CPU + 1` is a common heuristic for sync workers. Use `gthread` or `gevent` for concurrency if appropriate.
- `--timeout`: request timeout (seconds) — tune per expected slow requests.
- Logging: `--access-logfile -` prints to stdout (useful in containers); otherwise point to log files.

## Running behind Nginx (recommended architecture)

1. Configure Gunicorn to bind to `127.0.0.1:8000` or a UNIX socket.
2. Setup Nginx as a reverse proxy to handle TLS, client buffering, static files, and security headers.

Example Nginx site config (Debian/Ubuntu `/etc/nginx/sites-available/proproject`):

```
server {
    listen 80;
    server_name example.com;

    client_max_body_size 20M;

    location /static/ {
        alias /path/to/pro-project/app/static/;
        expires 30d;
        add_header Cache-Control "public";
    }

    location / {
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass http://127.0.0.1:8000;
        proxy_redirect off;
    }
}
```

After editing, enable and reload Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/proproject /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## systemd service for Gunicorn

Create `/etc/systemd/system/proproject.service` with:

```
[Unit]
Description=Gunicorn instance for Pro Project
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/pro-project
Environment="PATH=/path/to/venv/bin"
Environment=DATABASE_URL=postgresql://user:pass@db:5432/proproject
ExecStart=/path/to/venv/bin/gunicorn -w 3 --threads 2 -k gthread -b 127.0.0.1:8000 run:app

[Install]
WantedBy=multi-user.target
```

Then enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable proproject
sudo systemctl start proproject
sudo journalctl -u proproject -f
```

## Docker Compose (production)

Example snippet for a `docker-compose.prod.yml` service:

```yaml
services:
  web:
    build: .
    command: gunicorn -w 3 --threads 2 -k gthread -b 0.0.0.0:8000 run:app
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - db
    ports:
      - 8000:8000

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: proproject
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: example
```

## Logging

- In containers, prefer writing logs to stdout/stderr (Gunicorn `--access-logfile - --error-logfile -`) and collect them with your container platform.
- If using systemd, logs appear in `journalctl -u proproject`.

## Health checks & monitoring

- Configure a lightweight `/health` route (returns 200) behind Gunicorn for orchestration health checks.
- Monitor Gunicorn workers (restarts on crashes), memory usage, and request latency — use Prometheus/Datadog/Sentry as needed.

## Windows notes

- Gunicorn does not run on native Windows. For local Windows development, continue using the Flask dev server. For production, deploy to Linux (VM or container) and run Gunicorn there.

## Troubleshooting

- If you see `ModuleNotFoundError` in production, ensure the virtualenv PATH is set in the `systemd` service or Dockerfile installs dependencies.
- Ensure `DATABASE_URL` is set and the DB is reachable before starting Gunicorn to avoid migration/runtime failures.

---

If you want, I can also add:
- A `systemd` unit file in the repo under `deploy/` for templating.
- A `Dockerfile.prod` tuned for production with an explicit `gunicorn` entrypoint.
- A `make` target or `start-prod.ps1` script to help with common tasks.
