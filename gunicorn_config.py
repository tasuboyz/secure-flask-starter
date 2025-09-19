import multiprocessing

# Gunicorn configuration file for production
bind = '0.0.0.0:8000'
workers = max(2, multiprocessing.cpu_count() * 2 + 1)
worker_class = 'gthread'
threads = 4
timeout = 30
keepalive = 2
accesslog = '-'  # stdout
errorlog = '-'   # stdout/stderr
loglevel = 'info'

# Graceful timeout for reload
graceful_timeout = 30
