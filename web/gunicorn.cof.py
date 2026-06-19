"""
Configuración de Gunicorn para Render
Optimizada para el servidor EventSub
"""

import os
import multiprocessing

# Puerto desde variable de entorno
port = os.getenv("PORT", "10000")
bind = f"0.0.0.0:{port}"

# ============================================
# WORKERS Y THREADS
# ============================================
# - Un solo worker es suficiente porque Flask no guarda estado pesado
#   y el webhook solo reenvía eventos sin procesamiento pesado.
# - threads=4 permite manejar hasta 4 peticiones concurrentes.
workers = 1
threads = 4

# ============================================
# TIMEOUTS
# ============================================
# - timeout=30: tiempo máximo para procesar una solicitud.
# - graceful_timeout=30: tiempo para finalizar workers en reinicio.
# - keepalive=5: tiempo que una conexión keep-alive permanece abierta.
timeout = 30
graceful_timeout = 30
keepalive = 5

# ============================================
# PRELOAD Y MEMORIA
# ============================================
# - preload_app: carga la aplicación antes de fork, ahorra memoria y tiempo.
# - max_requests: reinicia workers después de 1000 peticiones para evitar memory leaks.
preload_app = True
max_requests = 1000
max_requests_jitter = 100  # Evita que todos reinicien a la vez

# ============================================
# LOGGING
# ============================================
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = "info"

# ============================================
# OTRAS OPCIONES
# ============================================
# - worker_class: 'gthread' es eficiente para I/O con threads.
worker_class = "gthread"

# - Algunas opciones adicionales de seguridad
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# ============================================
# NOTA SOBRE RENDER
# ============================================
# Render asigna automáticamente WEB_CONCURRENCY. Si se define,
# se puede usar para ajustar workers dinámicamente:
# web_concurrency = os.getenv("WEB_CONCURRENCY", 1)
# workers = int(web_concurrency) * 2 + 1  # (no recomendado para 1 CPU)