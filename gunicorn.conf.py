"""
Gunicorn production configuration.
Use with: gunicorn app.main:app -c gunicorn.conf.py
"""
from app.config import settings

# Bind
bind = f"{settings.HOST}:{settings.PORT}"

# Workers (MUST be 1 for WebSocket apps without sticky sessions)
workers = 1
worker_class = "uvicorn.workers.UvicornWorker"

# Logging
accesslog = "-"
errorlog = "-"
loglevel = settings.LOG_LEVEL.lower()

# Timeouts (important for voice calls)
timeout = 1000  # 5 minutes max call duration
keepalive = 65
graceful_timeout = 30

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190