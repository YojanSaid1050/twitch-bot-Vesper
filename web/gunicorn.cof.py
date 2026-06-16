"""
Configuración de Gunicorn para Render
"""

import os

bind = f"0.0.0.0:{os.getenv('PORT', '8080')}"
workers = 1
threads = 2
timeout = 30
accesslog = "-"
errorlog = "-"
loglevel = "info"