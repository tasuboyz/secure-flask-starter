## Production deployment artifacts

This repository includes example production artifacts to run the Flask app with Gunicorn, PostgreSQL, and Redis. These are intended as a starting point — adjust paths, users, and environment variables to match your infrastructure.

Included files:

- `gunicorn_config.py` - Gunicorn configuration (bind, workers, threads, logs).
- `Dockerfile.prod` - Dockerfile tailored for production using Gunicorn.
- `docker-compose.prod.yml` - Compose file to run app + Postgres + Redis for quick production-like stacks.
- `deploy/gunicorn.service` - Example `systemd` unit to run Gunicorn as a service.
- `deploy/nginx.conf` - Example Nginx reverse-proxy configuration.

Quick start (Docker Compose):

1. Create a `.env.prod` file with the required values (see `.env.example`):

```
POSTGRES_DB=appdb
POSTGRES_USER=app
POSTGRES_PASSWORD=supersecret
DATABASE_URL=postgresql://app:supersecret@db:5432/appdb
REDIS_URL=redis://redis:6379/0
SECRET_KEY=... # generate with python -c "import secrets; print(secrets.token_hex(32))"
SECURITY_PASSWORD_SALT=... # generate similarly
```

2. Build and start the production stack:

```powershell
docker-compose -f docker-compose.prod.yml up --build -d
```

3. Run database migrations (once):

```powershell
docker-compose -f docker-compose.prod.yml run --rm web flask db upgrade
```

4. Check logs:

```powershell
docker-compose -f docker-compose.prod.yml logs -f web
```

Using `systemd` + virtualenv on a VM

1. Place your app at `/srv/myapp` and create a virtualenv at `/srv/myapp/venv`.
2. Install requirements: `/srv/myapp/venv/bin/pip install -r requirements.txt`.
3. Copy `deploy/gunicorn.service` to `/etc/systemd/system/gunicorn.service` and edit paths and user.
4. Reload systemd and start the service:

```powershell
sudo systemctl daemon-reload; sudo systemctl enable --now gunicorn
```

5. Configure Nginx using `deploy/nginx.conf` and reload Nginx.

Security notes:

- Ensure `SECRET_KEY` and `SECURITY_PASSWORD_SALT` are stored securely (not in the repo).
- Use TLS termination at the load balancer or Nginx. Keep cookies `Secure` and `HttpOnly`.
- Prefer running Gunicorn behind a reverse proxy (Nginx) for static file serving and connection management.
