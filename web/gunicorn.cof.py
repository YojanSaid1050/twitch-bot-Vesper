"""
Configuración de Gunicorn para Render
"""

import os
import multiprocessing

# Puerto desde variable de entorno o por defecto 10000
port = os.getenv("PORT", "10000")
bind = f"0.0.0.0:{port}"
workers = 1
threads = 2
timeout = 30
accesslog = "-"
errorlog = "-"
loglevel = "info"
graceful_timeout = 30
keepalive = 2