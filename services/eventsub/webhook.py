# services/eventsub/webhook.py
"""
Manejo de webhook de Twitch: verificación, firma HMAC, etc.
"""

import hmac
import hashlib
from typing import Optional
from datetime import datetime, timezone
from flask import request, Response, abort, jsonify
from config import settings
from .exceptions import WebhookUnavailableError
from utils.logger import get_logger

logger = get_logger(__name__)


class WebhookHandler:
    MAX_MESSAGE_AGE_SECONDS = 600

    def verify_signature(self, message: str, signature: str, secret: str) -> bool:
        if not secret:
            logger.warning("TWITCH_WEBHOOK_SECRET vacío, omitiendo verificación")
            return True

        expected = hmac.new(
            secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        if signature.startswith('sha256='):
            signature = signature[7:]

        return hmac.compare_digest(expected, signature)

    def is_timestamp_fresh(self, timestamp_str: str) -> bool:
        try:
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            age = (now - dt).total_seconds()
            return 0 <= age <= self.MAX_MESSAGE_AGE_SECONDS
        except ValueError:
            return False

    def handle_verification(self, data: dict) -> Response:
        challenge = data.get('challenge')
        if not challenge:
            abort(400, description="Falta challenge en verificación")
        logger.info(f"Verificando webhook con challenge: {challenge[:20]}...")
        return Response(challenge, status=200, mimetype='text/plain')

    def handle_notification(self, message_id: str, event_type: str, event_data: dict):
        # Este método será llamado desde el dispatcher después de validar
        pass


webhook_handler = WebhookHandler()