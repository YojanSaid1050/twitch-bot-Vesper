# web/webhook.py
"""
Servidor webhook para EventSub de Twitch - Integrado con el dashboard
- Registra las rutas del webhook en la misma aplicación Flask que el dashboard
- Única responsabilidad: recibir y validar webhooks de Twitch
- Reenvía eventos al EventSubService
- No contiene lógica del bot ni de negocio
"""

import os
import sys
import time
import hmac
import hashlib
import requests
from pathlib import Path
from datetime import datetime, timezone
from collections import deque
from typing import Optional

# Añadir el directorio raíz al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import request, jsonify, Response, abort
from utils.logger import get_logger
from services.log_service import log_service
from services.eventsub_service import eventsub_service
from config import settings

# Importar la aplicación del dashboard para registrar las rutas
from web.dashboard import app

logger = get_logger(__name__)

# ============================================
# CONSTANTES
# ============================================
MAX_MESSAGE_AGE_SECONDS = 600  # 10 minutos
CACHE_SIZE = 1000
TWITCH_SECRET = os.getenv("TWITCH_WEBHOOK_SECRET", "")

if not TWITCH_SECRET:
    logger.warning("⚠️ TWITCH_WEBHOOK_SECRET no configurado. Las solicitudes serán rechazadas.")

# ============================================
# VARIABLE GLOBAL PARA LA INSTANCIA DEL BOT
# ============================================
_bot_instance = None


def set_bot_instance(bot):
    """Establece la instancia del bot para procesar eventos."""
    global _bot_instance
    _bot_instance = bot
    if bot:
        eventsub_service.set_bot(bot)
        logger.info("🤖 Bot registrado en el webhook")
        log_service.add_log('info', 'Bot registrado en el webhook', 'webhook')


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


# ============================================================
# RUTAS DEL WEBHOOK (registradas en la app del dashboard)
# ============================================================

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


# ============================================================
# FUNCIÓN PARA ESPERAR QUE EL SERVIDOR ESTÉ LISTO
# ============================================================

def wait_for_webhook_ready(port=None, timeout=60, check_interval=1):
    """
    Espera a que el servidor combinado (webhook + dashboard) esté listo.
    Verifica el endpoint /health que está disponible en la app combinada.
    """
    if port is None:
        port = int(os.getenv("PORT", "10000"))

    # Primero intentar con /health
    url = f"http://localhost:{port}/health"
    logger.info(f"⏳ Esperando que el servidor webhook esté listo en {url}...")

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                logger.info("✅ Webhook está listo y respondiendo")
                return True
        except:
            pass

        # Fallback: intentar con /twitch/webhook
        try:
            webhook_url = f"http://localhost:{port}/twitch/webhook"
            resp = requests.get(webhook_url, timeout=2)
            if resp.status_code == 200:
                logger.info("✅ Webhook está listo y respondiendo")
                return True
        except:
            pass

        time.sleep(check_interval)

    logger.warning(f"⚠️ Timeout esperando webhook después de {timeout}s")
    return False