"""
Gunicorn configuration for Cash Flow Optimizer
Production deployment
"""
import multiprocessing

# Server socket
bind = "0.0.0.0:8080"

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 5

# Logging
accesslog = "/var/www/cashflow-optimizer/logs/access.log"
errorlog = "/var/www/cashflow-optimizer/logs/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "cashflow-optimizer"

# Server mechanics
daemon = False
pidfile = "/var/www/cashflow-optimizer/gunicorn.pid"
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
# keyfile = "/path/to/key.pem"
# certfile = "/path/to/cert.pem"
