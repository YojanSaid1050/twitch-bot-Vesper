# web/webhook.py
"""
Servidor webhook independiente para EventSub de Twitch
- Se ejecuta en su propio proceso/hilo
- Única responsabilidad: recibir y validar webhooks de Twitch
- Reenvía eventos al EventSubService
- No contiene lógica del bot ni de negocio
"""

import os
import sys
import time
import hmac
import hashlib
import json
import threading
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import deque
from typing import Dict, Optional

# Añadir el directorio raíz al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, request, jsonify, Response, abort
from utils.logger import get_logger
from services.log_service import log_service
from services.eventsub_service import eventsub_service
from config import settings

logger = get_logger(__name__)

# ============================================
# CONSTANTES
# ============================================
MAX_MESSAGE_AGE_SECONDS = 600  # 10 minutos
CACHE_SIZE = 1000
TWITCH_SECRET = os.getenv("TWITCH_WEBHOOK_SECRET", "")

# ============================================
# APLICACIÓN FLASK
# ============================================
app = Flask(__name__)

# Variable global para la instancia del bot
_bot_instance = None


def set_bot_instance(bot):
    """Establece la instancia del bot para procesar eventos."""
    global _bot_instance
    _bot_instance = bot
    if bot:
        eventsub_service.set_bot(bot)


# ============================================
# CACHÉ DE DEDUPLICACIÓN
# ============================================
class MessageIdCache:
    """Cache para deduplicación de IDs de mensajes."""
    def __init__(self, maxlen: int = CACHE_SIZE):
        self._maxlen = maxlen
        self._deque = deque(maxlen=maxlen)
        self._set = set()

    def add(self, message_id: str) -> bool:
        if message_id in self._set:
            return False
        if len(self._deque) == self._maxlen:
            oldest = self._deque[0]
            self._set.discard(oldest)
        self._deque.append(message_id)
        self._set.add(message_id)
        return True


_message_cache = MessageIdCache()


# ============================================
# FUNCIONES DE VALIDACIÓN
# ============================================

def verify_signature(message: str, signature: str, secret: str) -> bool:
    """Verifica la firma HMAC SHA256 del webhook."""
    if not secret:
        logger.warning("⚠️ TWITCH_WEBHOOK_SECRET vacío, omitiendo verificación")
        return True
    
    expected = hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    if signature.startswith('sha256='):
        signature = signature[7:]
    
    return hmac.compare_digest(expected, signature)


def is_timestamp_fresh(timestamp_str: str) -> bool:
    """Verifica que el timestamp no sea demasiado antiguo (replay attack)."""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        age = (now - dt).total_seconds()
        if age < 0:
            logger.warning(f"Timestamp futuro: {timestamp_str}")
            return False
        if age > MAX_MESSAGE_AGE_SECONDS:
            logger.warning(f"Mensaje demasiado antiguo: {age:.0f}s")
            return False
        return True
    except ValueError as e:
        logger.error(f"Error parseando timestamp: {e}")
        return False


# ============================================
# RUTAS DEL WEBHOOK
# ============================================

@app.route('/twitch/webhook', methods=['POST'])
def twitch_webhook():
    """
    Endpoint principal para webhooks de Twitch (EventSub).
    Recibe, valida y reenvía eventos.
    """
    start_time = time.time()

    # Validar Content-Type
    if request.content_type != 'application/json':
        abort(415, description="Content-Type debe ser application/json")

    # Obtener headers
    signature = request.headers.get('Twitch-Eventsub-Message-Signature', '')
    message_id = request.headers.get('Twitch-Eventsub-Message-Id', '')
    timestamp = request.headers.get('Twitch-Eventsub-Message-Timestamp', '')
    message_type = request.headers.get('Twitch-Eventsub-Message-Type', '')

    if not message_id or not timestamp or not signature:
        logger.warning("Faltan headers de EventSub")
        abort(400, description="Faltan headers requeridos")

    raw_body = request.get_data(as_text=True)

    # Validar timestamp (replay attack)
    if not is_timestamp_fresh(timestamp):
        logger.warning(f"Mensaje rechazado por timestamp inválido: {timestamp}")
        abort(400, description="Timestamp inválido o expirado")

    # Construir mensaje para firma
    verification_message = message_id + timestamp + raw_body

    # Verificar firma
    if not verify_signature(verification_message, signature, TWITCH_SECRET):
        logger.warning(f"Firma inválida para mensaje {message_id}")
        abort(401, description="Firma HMAC inválida")

    # Deduplicación
    if not _message_cache.add(message_id):
        logger.info(f"⏩ Mensaje duplicado ignorado: {message_id}")
        return jsonify({"status": "duplicate"}), 200

    # Parsear JSON
    try:
        data = request.json
    except Exception as e:
        logger.error(f"Error parseando JSON: {e}")
        abort(400, description="JSON inválido")

    # Manejar según tipo de mensaje
    if message_type == 'webhook_callback_verification':
        challenge = data.get('challenge')
        if not challenge:
            abort(400, description="Falta challenge en verificación")
        logger.info(f"✅ Verificando webhook con challenge: {challenge[:20]}...")
        return Response(challenge, status=200, mimetype='text/plain')

    elif message_type == 'notification':
        event_type = data.get('subscription', {}).get('type', 'unknown')
        event_data = data.get('event', {})
        logger.info(f"📨 Evento {event_type} recibido (ID: {message_id})")

        # Procesar evento directamente (el bot está en el mismo proceso)
        if _bot_instance:
            eventsub_service.process_webhook(message_id, event_type, event_data)
        else:
            logger.warning("⚠️ Bot no disponible para procesar evento")
            log_service.add_log('info', f'Evento recibido sin bot: {event_type}', 'webhook')

        return jsonify({"status": "ok"}), 200

    elif message_type == 'revocation':
        subscription = data.get('subscription', {})
        event_type = subscription.get('type', 'unknown')
        reason = data.get('reason', 'No especificado')
        logger.warning(f"🔄 Revocación de suscripción: {event_type} - Motivo: {reason}")
        log_service.add_log('warning', f'Revocación de {event_type}: {reason}', 'webhook')
        return jsonify({"status": "revoked"}), 200

    else:
        logger.warning(f"Tipo de mensaje desconocido: {message_type}")
        abort(400, description="Tipo de mensaje no soportado")


@app.route('/twitch/webhook', methods=['GET'])
def twitch_webhook_get():
    """Método GET para verificación inicial del webhook."""
    return jsonify({"status": "ready", "service": "VesperBot Webhook"}), 200


# ============================================
# RUTAS DE HEALTH CHECK
# ============================================

@app.route('/health', methods=['GET'])
def health():
    """Health check del webhook."""
    return jsonify({
        "status": "healthy",
        "service": "VesperBot Webhook",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0",
        "bot_available": _bot_instance is not None,
        "cache_size": len(_message_cache._set),
        "twitch_secret_configured": bool(TWITCH_SECRET)
    }), 200


@app.route('/', methods=['GET'])
def index():
    """Raíz del servicio webhook."""
    return jsonify({
        "service": "VesperBot Webhook Service",
        "status": "running",
        "version": "2.0",
        "endpoints": {
            "webhook": "/twitch/webhook",
            "health": "/health"
        },
        "documentation": "https://dev.twitch.tv/docs/eventsub"
    }), 200


# ============================================
# ERROR HANDLERS
# ============================================

@app.errorhandler(400)
def bad_request(e):
    return jsonify({"error": "Bad Request", "description": str(e.description)}), 400


@app.errorhandler(401)
def unauthorized(e):
    return jsonify({"error": "Unauthorized", "description": str(e.description)}), 401


@app.errorhandler(415)
def unsupported_media(e):
    return jsonify({"error": "Unsupported Media Type", "description": str(e.description)}), 415


@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Error interno: {e}")
    return jsonify({"error": "Internal Server Error"}), 500


# ============================================
# FUNCIÓN PARA INICIAR EL SERVIDOR
# ============================================

def run_webhook(port=None, host='0.0.0.0', debug=False):
    """
    Inicia el servidor webhook.
    
    Args:
        port: Puerto donde escuchar (por defecto usa PORT de entorno o 10000)
        host: Host donde escuchar (por defecto 0.0.0.0)
        debug: Modo debug (por defecto False)
    """
    if port is None:
        port = int(os.getenv("PORT", "10000"))
    
    logger.info(f"🚀 Iniciando servidor webhook en {host}:{port}")
    logger.info(f"📡 Endpoint: /twitch/webhook")
    
    app.config['START_TIME'] = datetime.now()
    app.run(host=host, port=port, debug=debug, use_reloader=False)


def run_webhook_in_thread(port=None, host='0.0.0.0', debug=False):
    """
    Inicia el servidor webhook en un hilo separado.
    
    Returns:
        threading.Thread: Hilo donde se ejecuta el servidor
    """
    if port is None:
        port = int(os.getenv("PORT", "10000"))
    
    thread = threading.Thread(
        target=run_webhook,
        args=(port, host, debug),
        daemon=True,
        name="WebhookServer"
    )
    thread.start()
    
    logger.info(f"⏳ Webhook iniciado en hilo separado (puerto {port})")
    
    return thread


# ============================================
# FUNCIÓN PARA ESPERAR QUE EL WEBHOOK ESTÉ LISTO
# ============================================

def wait_for_webhook_ready(port=None, timeout=60, check_interval=1):
    """
    Espera a que el webhook esté listo para recibir peticiones.
    
    Args:
        port: Puerto donde escucha el webhook
        timeout: Tiempo máximo de espera en segundos
        check_interval: Intervalo entre verificaciones en segundos
    
    Returns:
        bool: True si el webhook está listo, False si timeout
    """
    if port is None:
        port = int(os.getenv("PORT", "10000"))
    
    url = f"http://localhost:{port}/health"
    
    logger.info(f"⏳ Esperando que el webhook esté listo en {url}...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            import requests
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                logger.info("✅ Webhook está listo y respondiendo")
                return True
        except:
            pass
        time.sleep(check_interval)
    
    logger.warning(f"⚠️ Timeout esperando webhook después de {timeout}s")
    return False


# ============================================
# INSTANCIA GLOBAL DE LA APP (para Gunicorn)
# ============================================

# Si se ejecuta con Gunicorn, se usa esta instancia
application = app


# ============================================
# EJECUCIÓN DIRECTA
# ============================================

if __name__ == "__main__":
    run_webhook()