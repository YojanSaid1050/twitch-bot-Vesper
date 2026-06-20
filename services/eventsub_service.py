# services/eventsub_service.py
"""
Servicio EventSub profesional para Twitch Helix API (2026)
- Suscripciones normales: App Access Token
- Suscripciones de moderación (ban, unban, etc.): User Access Token del broadcaster
- Verifica scopes del broadcaster antes de suscribir
- Espera a que el webhook esté activo
- Dispatcher central con handlers específicos
- LOGS DETALLADOS para depuración
"""

import os
import asyncio
import time
import json
import requests
import sys
import io
from collections import deque
from threading import Lock
from typing import Dict, Set, Tuple, Optional, Any, List, Callable
from dataclasses import dataclass, field

from config import settings
from services.notification_service import notification_service
from services.log_service import log_service
from utils.logger import get_logger

# Forzar UTF-8 para emojis
try:
    if hasattr(sys.stdout, 'encoding') and sys.stdout.encoding != 'UTF-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    if hasattr(sys.stderr, 'encoding') and sys.stderr.encoding != 'UTF-8':
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
except (AttributeError, TypeError, ValueError):
    pass

logger = get_logger(__name__)


# ============================================================
# DEFINICIÓN DE EVENTOS (Estructura central)
# ============================================================

@dataclass
class EventDefinition:
    """Define un evento EventSub con todos sus requisitos."""
    type: str
    version: str
    condition_builder: Callable  # (broadcaster_id, moderator_id, user_id) -> dict
    required_scopes: List[str] = field(default_factory=list)
    requires_moderator: bool = False
    requires_user: bool = False
    handler: Optional[str] = None
    # 'app' = App Access Token, 'user' = User Access Token (broadcaster)
    auth_type: str = 'app'

    def __post_init__(self):
        if self.handler is None:
            self.handler = self.type.replace('.', '_')


# Funciones de construcción de condiciones
def _build_condition(broadcaster_id: str, moderator_id: str = None, user_id: str = None) -> Dict:
    cond = {"broadcaster_user_id": broadcaster_id}
    if moderator_id:
        cond["moderator_user_id"] = moderator_id
    if user_id:
        cond["user_id"] = user_id
    return cond


# Lista completa de eventos según documentación oficial 2026
EVENTS = [
    # ===== Stream (App Token) =====
    EventDefinition("stream.online", "1", lambda b, m, u: {"broadcaster_user_id": b}),
    EventDefinition("stream.offline", "1", lambda b, m, u: {"broadcaster_user_id": b}),
    EventDefinition("channel.update", "2", lambda b, m, u: {"broadcaster_user_id": b}),

    # ===== Suscripciones (App Token) =====
    EventDefinition("channel.subscribe", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:subscriptions"]),
    EventDefinition("channel.subscription.end", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:subscriptions"]),
    EventDefinition("channel.subscription.gift", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:subscriptions"]),
    EventDefinition("channel.subscription.message", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:subscriptions"]),

    # ===== Cheers (App Token) =====
    EventDefinition("channel.cheer", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["bits:read"]),

    # ===== Raid (App Token) =====
    EventDefinition("channel.raid", "1", lambda b, m, u: {"to_broadcaster_user_id": b}),

    # ===== VIP (App Token) =====
    EventDefinition("channel.vip.add", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:vips"]),
    EventDefinition("channel.vip.remove", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:vips"]),

    # ===== Predicciones (App Token) =====
    EventDefinition("channel.prediction.begin", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:predictions"]),
    EventDefinition("channel.prediction.progress", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:predictions"]),
    EventDefinition("channel.prediction.lock", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:predictions"]),
    EventDefinition("channel.prediction.end", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:predictions"]),

    # ===== Encuestas (App Token) =====
    EventDefinition("channel.poll.begin", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:polls"]),
    EventDefinition("channel.poll.progress", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:polls"]),
    EventDefinition("channel.poll.end", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:polls"]),

    # ===== Metas (App Token) =====
    EventDefinition("channel.goal.begin", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:goals"]),
    EventDefinition("channel.goal.progress", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:goals"]),
    EventDefinition("channel.goal.end", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:goals"]),

    # ===== Hype Train (App Token) =====
    EventDefinition("channel.hype_train.begin", "2", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:hype_train"]),
    EventDefinition("channel.hype_train.progress", "2", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:hype_train"]),
    EventDefinition("channel.hype_train.end", "2", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:hype_train"]),

    # ===== Redenciones (App Token) =====
    EventDefinition("channel.channel_points_custom_reward_redemption.add", "1",
                    lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:redemptions"]),
    EventDefinition("channel.channel_points_custom_reward_redemption.update", "1",
                    lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:redemptions"]),

    # ============================================================
    # EVENTOS CON MODERATOR_USER_ID (USER TOKEN)
    # ============================================================
    EventDefinition("channel.follow", "2",
                    lambda b, m, u: _build_condition(b, moderator_id=m),
                    required_scopes=["moderator:read:followers"],
                    requires_moderator=True,
                    auth_type='user'),

    EventDefinition("channel.moderator.add", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m),
                    required_scopes=["channel:manage:moderators"],
                    requires_moderator=True,
                    auth_type='user'),
    EventDefinition("channel.moderator.remove", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m),
                    required_scopes=["channel:manage:moderators"],
                    requires_moderator=True,
                    auth_type='user'),

    # Chat
    EventDefinition("channel.chat.message_delete", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m, user_id=b),
                    required_scopes=["moderator:manage:chat_messages"],
                    requires_moderator=True, requires_user=True,
                    auth_type='user'),
    EventDefinition("channel.chat.clear", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m, user_id=b),
                    required_scopes=["moderator:manage:chat_messages"],
                    requires_moderator=True, requires_user=True,
                    auth_type='user'),
    EventDefinition("channel.chat.clear_user_messages", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m, user_id=b),
                    required_scopes=["moderator:manage:chat_messages"],
                    requires_moderator=True, requires_user=True,
                    auth_type='user'),

    # Shoutout
    EventDefinition("channel.shoutout.create", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m),
                    required_scopes=["moderator:manage:shoutouts"],
                    requires_moderator=True,
                    auth_type='user'),
    EventDefinition("channel.shoutout.receive", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m),
                    required_scopes=["moderator:manage:shoutouts"],
                    requires_moderator=True,
                    auth_type='user'),

    # ============================================================
    # ⚠️ BAN / UNBAN - CRÍTICO: USER TOKEN OBLIGATORIO
    # ============================================================
    EventDefinition("channel.ban", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m),
                    required_scopes=["moderator:manage:banned_users"],
                    requires_moderator=True,
                    auth_type='user'),
    EventDefinition("channel.unban", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m),
                    required_scopes=["moderator:manage:banned_users"],
                    requires_moderator=True,
                    auth_type='user'),

    # ============================================================
    # OTROS EVENTOS DE MODERACIÓN (USER TOKEN)
    # ============================================================
    EventDefinition("channel.shield_mode.begin", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m),
                    required_scopes=["moderator:manage:shield_mode"],
                    requires_moderator=True,
                    auth_type='user'),
    EventDefinition("channel.shield_mode.end", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m),
                    required_scopes=["moderator:manage:shield_mode"],
                    requires_moderator=True,
                    auth_type='user'),

    EventDefinition("channel.unban_request.create", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m),
                    required_scopes=["moderator:manage:unban_requests"],
                    requires_moderator=True,
                    auth_type='user'),
    EventDefinition("channel.unban_request.resolve", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m),
                    required_scopes=["moderator:manage:unban_requests"],
                    requires_moderator=True,
                    auth_type='user'),

    EventDefinition("channel.suspicious_user.message", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m),
                    required_scopes=["moderator:read:suspicious_users"],
                    requires_moderator=True,
                    auth_type='user'),
    EventDefinition("channel.suspicious_user.update", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m),
                    required_scopes=["moderator:read:suspicious_users"],
                    requires_moderator=True,
                    auth_type='user'),

    EventDefinition("automod.message.hold", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m),
                    required_scopes=["moderator:manage:automod"],
                    requires_moderator=True,
                    auth_type='user'),
    EventDefinition("automod.message.update", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m),
                    required_scopes=["moderator:manage:automod"],
                    requires_moderator=True,
                    auth_type='user'),
]


# ============================================================
# SERVICIO PRINCIPAL
# ============================================================

class EventSubService:
    def __init__(self):
        self.bot = None
        self.channel = None
        self._webhook_ready = False
        self._webhook_checked = False

        # Deduplicación
        self._lock = Lock()
        self._processed_ids = set()
        self._processed_queue = deque(maxlen=5000)

        # Estadísticas
        self.stats = {
            "subscriptions_created": 0,
            "subscriptions_skipped": 0,
            "subscription_errors": 0,
            "subscriptions_failed_scopes": 0,
            "events_processed": 0,
            "events_duplicated": 0,
        }

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "VesperBotx/1.0"})
        self.HTTP_TIMEOUT = (5, 15)

        # Cache de scopes del broadcaster
        self._broadcaster_scopes = None
        self._scopes_cache_time = 0
        self._scopes_cache_ttl = 300  # 5 minutos

        # Handlers
        self._handlers = {}
        self._register_handlers()

    def set_bot(self, bot):
        """Establece la instancia del bot para procesar eventos y obtener el canal."""
        self.bot = bot
        if bot and bot.connected_channels:
            self.channel = bot.connected_channels[0]
            logger.info(f"📺 Canal establecido: {self.channel.name}")
            log_service.add_log('info', f'Canal establecido: {self.channel.name}', 'bot')
        else:
            logger.info("🤖 Bot registrado en EventSubService")

    def _register_handlers(self):
        """Registra los handlers para cada tipo de evento."""
        for event in EVENTS:
            handler_name = f"_on_{event.handler}"
            if hasattr(self, handler_name):
                self._handlers[event.type] = getattr(self, handler_name)
            else:
                logger.debug(f"No se encontró handler para {event.type}, se usará el genérico")
                self._handlers[event.type] = self._on_generic_event

    # ============================================================
    # ESPERA DEL WEBHOOK
    # ============================================================

    def wait_for_webhook(self, timeout: int = 60, check_interval: int = 2):
        """Espera a que el webhook esté activo en la ruta /twitch/webhook."""
        if self._webhook_checked and self._webhook_ready:
            return True

        callback_url = settings.EVENTSUB_CALLBACK_URL
        if not callback_url:
            logger.error("❌ EVENTSUB_CALLBACK_URL no configurado")
            return False

        webhook_url = f"{callback_url}/twitch/webhook"
        logger.info(f"⏳ Esperando que el webhook esté activo: {webhook_url}")

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                resp = requests.get(webhook_url, timeout=5)
                if resp.status_code == 200:
                    logger.info("✅ Webhook activo y respondiendo")
                    self._webhook_ready = True
                    self._webhook_checked = True
                    return True
            except:
                pass

            # Fallback a localhost (para desarrollo)
            try:
                port = os.getenv("PORT", "10000")
                local_url = f"http://localhost:{port}/twitch/webhook"
                resp = requests.get(local_url, timeout=2)
                if resp.status_code == 200:
                    logger.info("✅ Webhook local activo")
                    self._webhook_ready = True
                    self._webhook_checked = True
                    return True
            except:
                pass

            time.sleep(check_interval)

        logger.warning(f"⚠️ Timeout esperando webhook después de {timeout}s.")
        self._webhook_checked = True
        return False

    # ============================================================
    # VERIFICACIÓN DE SCOPES DEL BROADCASTER
    # ============================================================

    def _get_broadcaster_scopes(self) -> List[str]:
        """Obtiene los scopes del token del broadcaster desde la API de Twitch."""
        now = time.time()
        if self._broadcaster_scopes and (now - self._scopes_cache_time) < self._scopes_cache_ttl:
            logger.debug("📋 Scopes del broadcaster desde caché")
            return self._broadcaster_scopes

        token = settings.BROADCASTER_TOKEN
        if not token:
            logger.warning("⚠️ No hay BROADCASTER_TOKEN disponible")
            return []

        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "Client-Id": settings.CLIENT_ID
            }

            r = self.session.get(
                "https://id.twitch.tv/oauth2/validate",
                headers=headers,
                timeout=10
            )

            if r.status_code == 200:
                data = r.json()
                self._broadcaster_scopes = data.get("scopes", [])
                self._scopes_cache_time = now
                logger.info(f"📋 Scopes del broadcaster obtenidos: {len(self._broadcaster_scopes)}")
                
                # Log de scopes críticos para debug
                critical_scopes = ["moderator:manage:banned_users", "moderator:manage:chat_messages"]
                for scope in critical_scopes:
                    if scope in self._broadcaster_scopes:
                        logger.info(f"   ✅ {scope} presente")
                    else:
                        logger.warning(f"   ⚠️ {scope} FALTANTE")
                
                return self._broadcaster_scopes
            else:
                logger.warning(f"⚠️ No se pudieron obtener scopes: {r.status_code} - {r.text[:200]}")
                return []

        except Exception as e:
            logger.error(f"❌ Error obteniendo scopes: {e}")
            return []

    def _has_required_scopes(self, required_scopes: List[str], event_type: str) -> bool:
        """Verifica si el broadcaster tiene todos los scopes requeridos."""
        if not required_scopes:
            return True

        broadcaster_scopes = self._get_broadcaster_scopes()
        if not broadcaster_scopes:
            logger.warning(f"⚠️ {event_type}: No se pudieron obtener los scopes del broadcaster")
            return False

        missing = [s for s in required_scopes if s not in broadcaster_scopes]
        if missing:
            logger.warning(f"⚠️ {event_type}: Scopes faltantes en el broadcaster: {', '.join(missing)}")
            return False

        logger.info(f"✅ {event_type}: Todos los scopes requeridos están presentes")
        return True

    # ============================================================
    # DEDUPLICACIÓN
    # ============================================================

    def is_duplicate(self, message_id: str) -> bool:
        with self._lock:
            if message_id in self._processed_ids:
                return True

            self._processed_ids.add(message_id)
            self._processed_queue.append(message_id)

            if len(self._processed_queue) == self._processed_queue.maxlen:
                oldest = self._processed_queue[0]
                self._processed_ids.discard(oldest)

            return False

    # ============================================================
    # PROCESADOR DE WEBHOOK
    # ============================================================

    def process_webhook(self, message_id: str, event_type: str, event_data: Dict):
        """Procesa un evento recibido desde el webhook."""
        if self.is_duplicate(message_id):
            self.stats["events_duplicated"] += 1
            logger.info(f"⏭️ Evento duplicado ignorado: {message_id}")
            return

        self.stats["events_processed"] += 1
        logger.info(f"📨 Evento {event_type} recibido (ID: {message_id})")

        handler = self._handlers.get(event_type, self._on_generic_event)
        if self.bot and self.bot.loop:
            asyncio.run_coroutine_threadsafe(
                self._safe_handle(handler, event_type, event_data),
                self.bot.loop
            )
        else:
            logger.warning("⚠️ No hay loop disponible para ejecutar handler")

    async def _safe_handle(self, handler, event_type, event_data):
        try:
            await handler(event_data)
        except Exception as e:
            logger.error(f"Error en handler de {event_type}: {e}", exc_info=True)
            log_service.add_log('error', f'Error en handler de {event_type}: {e}', 'bot')

    # ============================================================
    # HANDLERS
    # ============================================================

    async def _on_generic_event(self, data):
        log_service.add_log('info', f'📨 Evento no manejado: {data}', 'system')

    async def _on_stream_online(self, data):
        streamer = data.get("broadcaster_user_name", "Desconocido")
        log_service.add_log('info', f'📡 Stream EN VIVO: {streamer} ha comenzado', 'system')

    async def _on_stream_offline(self, data):
        streamer = data.get("broadcaster_user_name", "Desconocido")
        log_service.add_log('info', f'🌙 Stream OFFLINE: {streamer} se ha desconectado', 'system')

    async def _on_channel_update(self, data):
        streamer = data.get("broadcaster_user_name", "Desconocido")
        title = data.get("title", "Sin título")
        game = data.get("game_name", "No especificado")
        log_service.add_log('info', f'📝 Canal actualizado: "{title}" - {game}', 'system')

    async def _on_channel_follow(self, data):
        user = data.get("user_name", "Desconocido")
        log_service.add_log('info', f'⭐ Nuevo seguidor: {user}', 'stats')
        if self.channel:
            await notification_service.on_follow(self.channel, user)

    async def _on_channel_subscribe(self, data):
        user = data.get("user_name", "Desconocido")
        tier = data.get("tier", "1000")
        is_gift = data.get("is_gift", False)
        if not is_gift:
            log_service.add_log('info', f'🎉 Nueva suscripción de {user} (Tier {tier})', 'stats')
            if self.channel:
                await notification_service.on_subscribe(self.channel, user, tier, "sub")
        else:
            log_service.add_log('info', f'🎁 Suscripción regalada a {user} (Tier {tier})', 'stats')

    async def _on_channel_subscription_end(self, data):
        user = data.get("user_name", "Desconocido")
        tier = data.get("tier", "1000")
        log_service.add_log('info', f'❌ Suscripción terminada: {user} (Tier {tier})', 'stats')

    async def _on_channel_subscription_gift(self, data):
        user = data.get("user_name", "Alguien")
        total = data.get("total", 1)
        tier = data.get("tier", "1000")
        log_service.add_log('info', f'🎁 {user} regaló {total} suscripción(es) Tier {tier}', 'stats')

    async def _on_channel_subscription_message(self, data):
        user = data.get("user_name", "Desconocido")
        tier = data.get("tier", "1000")
        message = data.get("message", {}).get("text", "")
        log_service.add_log('info', f'💬 Re-suscripción de {user} (Tier {tier}) con mensaje: "{message[:50]}"', 'stats')

    async def _on_channel_cheer(self, data):
        user = data.get("user_name", "Alguien")
        bits = data.get("bits", 0)
        message = data.get("message", "")
        log_service.add_log('info', f'💎 {user} envió {bits} bits - Mensaje: "{message[:30]}"', 'stats')

    async def _on_channel_raid(self, data):
        from_broadcaster = data.get("from_broadcaster_user_name", "Desconocido")
        to_broadcaster = data.get("to_broadcaster_user_name", "Desconocido")
        viewers = data.get("viewers", 0)
        log_service.add_log('info', f'⚔️ Raid de {from_broadcaster} hacia {to_broadcaster} con {viewers} espectadores', 'stats')
        if self.channel:
            await notification_service.on_raid(self.channel, from_broadcaster, viewers)

    async def _on_channel_ban(self, data):
        user = data.get("user_name", "Desconocido")
        moderator = data.get("moderator_user_name", "Staff")
        reason = data.get("reason", "Sin especificar")
        end_time = data.get("end_time")
        is_permanent = end_time is None
        action = "Ban permanente" if is_permanent else "Timeout"
        log_service.add_log('info', f'🔨 {action} aplicado a {user} por {moderator} - Razón: "{reason}"', 'moderation')

    async def _on_channel_unban(self, data):
        user = data.get("user_name", "Desconocido")
        moderator = data.get("moderator_user_name", "Staff")
        log_service.add_log('info', f'🔓 Unban/Timeout removido a {user} por {moderator}', 'moderation')

    async def _on_channel_moderator_add(self, data):
        user = data.get("user_name", "Desconocido")
        log_service.add_log('info', f'🛡️ Moderador añadido: {user}', 'moderation')

    async def _on_channel_moderator_remove(self, data):
        user = data.get("user_name", "Desconocido")
        log_service.add_log('info', f'🛡️ Moderador removido: {user}', 'moderation')

    async def _on_channel_shoutout_create(self, data):
        from_user = data.get("from_broadcaster_user_name", "Desconocido")
        to_user = data.get("to_broadcaster_user_name", "Desconocido")
        log_service.add_log('info', f'📢 Shoutout de {from_user} para {to_user}', 'stats')

    async def _on_channel_shoutout_receive(self, data):
        from_user = data.get("from_broadcaster_user_name", "Desconocido")
        to_user = data.get("to_broadcaster_user_name", "Desconocido")
        log_service.add_log('info', f'📢 Shoutout recibido de {from_user} para {to_user}', 'stats')

    # ============================================================
    # OBTENER APP TOKEN
    # ============================================================

    def _get_app_token(self) -> str:
        """Obtiene el App Access Token para crear suscripciones."""
        token = getattr(settings, "APP_ACCESS_TOKEN", "")
        if token:
            logger.debug("✅ App Access Token disponible")
        else:
            logger.warning("⚠️ App Access Token NO disponible")
        return token

    # ============================================================
    # GESTIÓN DE SUSCRIPCIONES
    # ============================================================

    def _cleanup_invalid_subscriptions(self, headers: Dict):
        """Elimina suscripciones inválidas según el estado."""
        try:
            r = self.session.get(
                "https://api.twitch.tv/helix/eventsub/subscriptions",
                headers=headers,
                timeout=self.HTTP_TIMEOUT
            )
            if r.status_code != 200:
                logger.warning(f"⚠️ No se pudieron listar suscripciones: {r.status_code}")
                return

            data = r.json()
            total = len(data.get("data", []))
            logger.info(f"📋 Total de suscripciones existentes: {total}")

            for sub in data.get("data", []):
                if sub.get("status") in (
                    "authorization_revoked",
                    "webhook_callback_verification_failed",
                    "notification_failures_exceeded",
                    "webhook_disconnected"
                ):
                    url = f"https://api.twitch.tv/helix/eventsub/subscriptions?id={sub['id']}"
                    resp = self.session.delete(url, headers=headers, timeout=self.HTTP_TIMEOUT)
                    if resp.status_code in (200, 204):
                        logger.info(f"🗑️ Eliminada suscripción inválida: {sub['type']} (ID: {sub['id']})")
                    else:
                        logger.warning(f"No se pudo eliminar sub {sub['id']}: {resp.status_code}")
        except Exception as e:
            logger.error(f"Error en cleanup: {e}")

    def _get_existing_subscriptions(self, headers: Dict) -> Set[Tuple[str, Tuple]]:
        """Obtiene las suscripciones existentes y las devuelve como conjunto."""
        try:
            r = self.session.get(
                "https://api.twitch.tv/helix/eventsub/subscriptions",
                headers=headers,
                timeout=self.HTTP_TIMEOUT
            )
            if r.status_code != 200:
                logger.warning(f"⚠️ No se pudieron listar suscripciones: {r.status_code}")
                return set()

            existing = set()
            for sub in r.json().get("data", []):
                event_type = sub["type"]
                condition = tuple(sorted((k, str(v)) for k, v in sub["condition"].items()))
                existing.add((event_type, condition))
            
            logger.info(f"📋 Suscripciones existentes encontradas: {len(existing)}")
            return existing
        except Exception as e:
            logger.error(f"Error obteniendo suscripciones: {e}")
            return set()

    def _get_token_for_event(self, event_def: EventDefinition) -> Tuple[Optional[str], str]:
        """
        Devuelve el token apropiado para el evento según su auth_type.
        """
        if event_def.auth_type == 'user':
            # Usar token del broadcaster para eventos de moderación
            token = settings.BROADCASTER_TOKEN
            token_name = "Broadcaster (User Token)"
            if not token:
                # Fallback al token del bot
                token = settings.BOT_TOKEN
                token_name = "Bot (User Token) [fallback]"
                logger.warning(f"⚠️ No hay BROADCASTER_TOKEN, usando BOT_TOKEN como fallback para {event_def.type}")
        else:
            # Usar App Token para eventos normales
            token = self._get_app_token()
            token_name = "App Token"
        
        if token:
            logger.debug(f"🔑 Token para {event_def.type}: {token_name} (longitud: {len(token)})")
        else:
            logger.error(f"❌ No hay token disponible para {event_def.type} (tipo: {token_name})")
        
        return token, token_name

    def _ensure_subscription(self, event_def: EventDefinition, existing: Set, moderator_id: str):
        """
        Crea una suscripción usando el token apropiado según el tipo de evento.
        """
        # Determinar el moderator_id correcto para eventos de usuario
        if event_def.auth_type == 'user':
            # Para eventos de moderación, el moderador debe ser el broadcaster
            effective_moderator_id = settings.BROADCASTER_ID
            logger.debug(f"🔧 {event_def.type}: Usando BROADCASTER_ID ({effective_moderator_id}) como moderator_user_id")
        else:
            effective_moderator_id = moderator_id

        condition = event_def.condition_builder(
            settings.BROADCASTER_ID,
            effective_moderator_id if event_def.requires_moderator else None,
            settings.BROADCASTER_ID if event_def.requires_user else None
        )

        key = (event_def.type, tuple(sorted((k, str(v)) for k, v in condition.items())))

        if key in existing:
            self.stats["subscriptions_skipped"] += 1
            logger.info(f"⏭️ {event_def.type} ya existe, omitiendo")
            return True

        logger.info(f"🔄 {event_def.type}: Creando nueva suscripción...")

        # Verificar scopes del broadcaster
        if event_def.required_scopes:
            if not self._has_required_scopes(event_def.required_scopes, event_def.type):
                self.stats["subscriptions_failed_scopes"] += 1
                logger.warning(f"⚠️ {event_def.type}: Scopes faltantes, omitiendo")
                log_service.add_log('warning', f'Omitiendo {event_def.type}: Scopes faltantes en el broadcaster', 'bot')
                return False
        else:
            logger.debug(f"📌 {event_def.type}: No requiere scopes adicionales")

        # Obtener token apropiado
        token, token_name = self._get_token_for_event(event_def)
        if not token:
            logger.error(f"❌ {event_def.type}: No hay token disponible, omitiendo")
            log_service.add_log('error', f'No hay token para {event_def.type}', 'bot')
            self.stats["subscription_errors"] += 1
            return False

        headers = {
            "Authorization": f"Bearer {token}",
            "Client-Id": settings.CLIENT_ID,
            "Content-Type": "application/json"
        }

        try:
            callback_url = f"{settings.EVENTSUB_CALLBACK_URL}/twitch/webhook"

            payload = {
                "type": event_def.type,
                "version": event_def.version,
                "condition": condition,
                "transport": {
                    "method": "webhook",
                    "callback": callback_url,
                    "secret": settings.TWITCH_WEBHOOK_SECRET
                }
            }

            logger.info(f"📡 {event_def.type}: Enviando solicitud con {token_name}...")
            logger.debug(f"   Payload: {json.dumps(payload, indent=2)}")

            r = self.session.post(
                "https://api.twitch.tv/helix/eventsub/subscriptions",
                headers=headers,
                json=payload,
                timeout=self.HTTP_TIMEOUT
            )

            # Log detallado de la respuesta
            logger.info(f"📊 {event_def.type}: Respuesta HTTP {r.status_code}")

            if r.status_code == 202:
                self.stats["subscriptions_created"] += 1
                existing.add(key)
                logger.info(f"✅ {event_def.type}: Suscrito exitosamente con {token_name}")
                log_service.add_log('info', f'Suscrito a {event_def.type} con {token_name}', 'bot')
                return True

            if r.status_code == 409:
                existing.add(key)
                self.stats["subscriptions_skipped"] += 1
                logger.info(f"⏭️ {event_def.type}: Ya existe (409), omitiendo")
                return True

            # Errores detallados
            error_detail = r.text
            try:
                error_json = r.json()
                error_detail = error_json.get("message", r.text)
                if "error" in error_json:
                    error_detail = f"{error_json.get('error')}: {error_json.get('message', '')}"
            except:
                pass

            if r.status_code == 403:
                logger.warning(f"⚠️ {event_def.type}: 403 - {error_detail}")
                logger.warning(f"   Token usado: {token_name}")
                logger.warning(f"   Moderator ID: {effective_moderator_id}")
                log_service.add_log('warning', f'{event_def.type}: 403 - Error de autorización con {token_name}', 'bot')
                self.stats["subscriptions_failed_scopes"] += 1
                return False

            elif r.status_code == 400:
                logger.error(f"❌ {event_def.type}: 400 - {error_detail}")
                logger.error(f"   Token usado: {token_name}")
                logger.error(f"   Condition: {condition}")
                log_service.add_log('error', f'{event_def.type}: 400 - {error_detail}', 'bot')
                self.stats["subscription_errors"] += 1
                return False

            elif r.status_code == 401:
                logger.error(f"❌ {event_def.type}: 401 - {error_detail}")
                logger.error(f"   Token usado: {token_name}")
                log_service.add_log('error', f'{event_def.type}: 401 - Token inválido', 'bot')
                self.stats["subscription_errors"] += 1
                return False

            elif r.status_code in (429, 500, 502, 503, 504):
                logger.warning(f"⚠️ {event_def.type}: {r.status_code} - Error temporal, reintentando más tarde")
                log_service.add_log('warning', f'{event_def.type}: {r.status_code} - Error temporal', 'bot')
                return False

            else:
                self.stats["subscription_errors"] += 1
                logger.error(f"❌ {event_def.type}: Error {r.status_code} - {error_detail}")
                log_service.add_log('error', f'Error suscribiendo a {event_def.type}: {r.status_code}', 'bot')
                return False

        except requests.exceptions.Timeout:
            logger.error(f"❌ {event_def.type}: Timeout")
            log_service.add_log('error', f'Timeout suscribiendo a {event_def.type}', 'bot')
            self.stats["subscription_errors"] += 1
            return False
        except Exception as e:
            self.stats["subscription_errors"] += 1
            logger.error(f"❌ {event_def.type}: Excepción - {e}", exc_info=True)
            log_service.add_log('error', f'Excepción suscribiendo a {event_def.type}: {e}', 'bot')
            return False

    def subscribe_to_events(self):
        """Punto de entrada principal para crear todas las suscripciones."""
        logger.info("=" * 60)
        logger.info("🚀 INICIANDO SUSCRIPCIÓN A EVENTSUB")
        logger.info("=" * 60)

        # Esperar a que el webhook esté activo
        if not self.wait_for_webhook(timeout=60):
            logger.warning("⚠️ Webhook no disponible, pero continuando con suscripciones...")

        # Verificar que tenemos App Token para eventos normales
        app_token = self._get_app_token()
        if not app_token:
            logger.error("❌ No hay APP_ACCESS_TOKEN configurado")
            log_service.add_log('error', 'No hay APP_ACCESS_TOKEN para EventSub', 'bot')
            return

        # Verificar que tenemos token del broadcaster para eventos de moderación
        broadcaster_token = settings.BROADCASTER_TOKEN
        if not broadcaster_token:
            logger.error("❌ No hay BROADCASTER_TOKEN para eventos de moderación")
            log_service.add_log('error', 'No hay BROADCASTER_TOKEN para eventos de moderación', 'bot')
            return

        # Obtener y mostrar los scopes del broadcaster
        logger.info("🔍 Verificando scopes del broadcaster...")
        broadcaster_scopes = self._get_broadcaster_scopes()
        if not broadcaster_scopes:
            logger.warning("⚠️ No se pudieron obtener los scopes del broadcaster. Algunas suscripciones pueden fallar.")
        else:
            logger.info(f"✅ Scopes del broadcaster: {len(broadcaster_scopes)}")
            # Mostrar scopes críticos
            critical = ["moderator:manage:banned_users", "moderator:manage:chat_messages", "moderator:read:followers"]
            for scope in critical:
                if scope in broadcaster_scopes:
                    logger.info(f"   ✅ {scope}")
                else:
                    logger.warning(f"   ❌ {scope}")

        # Limpiar suscripciones inválidas (usando App Token para listar)
        app_headers = {
            "Authorization": f"Bearer {app_token}",
            "Client-Id": settings.CLIENT_ID,
            "Content-Type": "application/json"
        }
        self._cleanup_invalid_subscriptions(app_headers)

        # Obtener suscripciones existentes
        existing = self._get_existing_subscriptions(app_headers)

        # IDs necesarios
        moderator_id = getattr(settings, "MODERATOR_USER_ID", settings.BROADCASTER_ID)
        logger.info(f"📌 Moderator ID: {moderator_id}")
        logger.info(f"📌 Broadcaster ID: {settings.BROADCASTER_ID}")

        # Separar eventos por tipo
        app_events = [e for e in EVENTS if e.auth_type == 'app']
        user_events = [e for e in EVENTS if e.auth_type == 'user']

        logger.info(f"📡 Total de eventos: {len(EVENTS)}")
        logger.info(f"   • App Token: {len(app_events)} eventos")
        logger.info(f"   • User Token: {len(user_events)} eventos")

        successful = 0
        failed = 0

        # Primero, suscribir eventos con App Token
        logger.info("\n" + "-" * 40)
        logger.info("📡 SUSCRIBIENDO EVENTOS CON APP TOKEN")
        logger.info("-" * 40)

        for event_def in app_events:
            result = self._ensure_subscription(event_def, existing, moderator_id)
            if result:
                successful += 1
            else:
                failed += 1
            time.sleep(0.3)  # Pausa para evitar rate limiting

        # Luego, suscribir eventos con User Token (moderación)
        logger.info("\n" + "-" * 40)
        logger.info("📡 SUSCRIBIENDO EVENTOS CON USER TOKEN (MODERACIÓN)")
        logger.info("-" * 40)

        for event_def in user_events:
            result = self._ensure_subscription(event_def, existing, moderator_id)
            if result:
                successful += 1
            else:
                failed += 1
            time.sleep(0.5)  # Pausa más larga para eventos de moderación

        # Resumen final
        logger.info("\n" + "=" * 60)
        logger.info("📊 RESUMEN FINAL DE SUSCRIPCIONES")
        logger.info("=" * 60)
        logger.info(f"✅ Creadas exitosamente: {successful}")
        logger.info(f"❌ Fallidas: {failed}")
        logger.info(f"⏭️ Omitidas (ya existentes): {len(existing)}")
        logger.info(f"📊 Total eventos procesados: {len(EVENTS)}")

        # Detalle de fallos
        if failed > 0:
            logger.warning(f"⚠️ {failed} eventos fallaron. Revisa los logs anteriores para más detalles.")
            logger.warning("   Posibles causas:")
            logger.warning("   - Scopes faltantes en el broadcaster")
            logger.warning("   - Token inválido o expirado")
            logger.warning("   - Problemas de red o timeout")
            logger.warning("   - El moderator_user_id no coincide con el token usado")
        else:
            logger.info("✅ ¡Todas las suscripciones se completaron exitosamente!")

        log_service.add_log('info', f'EventSub: {successful} creadas, {failed} fallidas, {len(existing)} existentes', 'bot')

    # ============================================================
    # CIERRE
    # ============================================================

    def stop(self):
        self.session.close()
        logger.info("🛑 EventSub detenido")
        log_service.add_log('info', 'EventSub detenido', 'bot')


# Instancia global
eventsub_service = EventSubService()