"""
Configuración de Gunicorn para Render
"""

import multiprocessing

bind = "0.0.0.0:8080"
workers = 1
threads = 2
timeout = 30
accesslog = "-"
errorlog = "-"