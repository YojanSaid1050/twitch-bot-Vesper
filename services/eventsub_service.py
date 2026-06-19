# services/eventsub_service.py
"""
Servicio EventSub profesional para Twitch Helix API (2026)
- Todas las suscripciones se crean con App Access Token
- Verifica scopes del broadcaster antes de suscribir
- Espera a que el webhook esté activo
- Dispatcher central con handlers específicos
- Deduplicación y validación de eventos
- El webhook ahora está en /twitch/webhook (servicio independiente)
"""

import os
import asyncio
import time
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
    # ===== Stream =====
    EventDefinition("stream.online", "1", lambda b, m, u: {"broadcaster_user_id": b}),
    EventDefinition("stream.offline", "1", lambda b, m, u: {"broadcaster_user_id": b}),
    EventDefinition("channel.update", "2", lambda b, m, u: {"broadcaster_user_id": b}),

    # ===== Suscripciones =====
    EventDefinition("channel.subscribe", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:subscriptions"]),
    EventDefinition("channel.subscription.end", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:subscriptions"]),
    EventDefinition("channel.subscription.gift", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:subscriptions"]),
    EventDefinition("channel.subscription.message", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:subscriptions"]),

    # ===== Cheers =====
    EventDefinition("channel.cheer", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["bits:read"]),

    # ===== Raid =====
    EventDefinition("channel.raid", "1", lambda b, m, u: {"to_broadcaster_user_id": b}),

    # ===== VIP =====
    EventDefinition("channel.vip.add", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:vips"]),
    EventDefinition("channel.vip.remove", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:vips"]),

    # ===== Predicciones =====
    EventDefinition("channel.prediction.begin", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:predictions"]),
    EventDefinition("channel.prediction.progress", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:predictions"]),
    EventDefinition("channel.prediction.lock", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:predictions"]),
    EventDefinition("channel.prediction.end", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:predictions"]),

    # ===== Encuestas =====
    EventDefinition("channel.poll.begin", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:polls"]),
    EventDefinition("channel.poll.progress", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:polls"]),
    EventDefinition("channel.poll.end", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:polls"]),

    # ===== Metas =====
    EventDefinition("channel.goal.begin", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:goals"]),
    EventDefinition("channel.goal.progress", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:goals"]),
    EventDefinition("channel.goal.end", "1", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:goals"]),

    # ===== Hype Train =====
    EventDefinition("channel.hype_train.begin", "2", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:hype_train"]),
    EventDefinition("channel.hype_train.progress", "2", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:hype_train"]),
    EventDefinition("channel.hype_train.end", "2", lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:hype_train"]),

    # ===== Redenciones =====
    EventDefinition("channel.channel_points_custom_reward_redemption.add", "1",
                    lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:redemptions"]),
    EventDefinition("channel.channel_points_custom_reward_redemption.update", "1",
                    lambda b, m, u: {"broadcaster_user_id": b},
                    required_scopes=["channel:read:redemptions"]),

    # ===== EVENTOS CON MODERATOR_USER_ID =====
    # Estos requieren que el moderador (broadcaster) tenga los scopes específicos
    EventDefinition("channel.follow", "2",
                    lambda b, m, u: _build_condition(b, moderator_id=m),
                    required_scopes=["moderator:read:followers"],
                    requires_moderator=True),

    EventDefinition("channel.moderator.add", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m),
                    required_scopes=["channel:manage:moderators"],
                    requires_moderator=True),
    EventDefinition("channel.moderator.remove", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m),
                    required_scopes=["channel:manage:moderators"],
                    requires_moderator=True),

    # Chat (requieren user_id = broadcaster_id)
    EventDefinition("channel.chat.message_delete", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m, user_id=b),
                    required_scopes=["moderator:manage:chat_messages"],
                    requires_moderator=True, requires_user=True),
    EventDefinition("channel.chat.clear", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m, user_id=b),
                    required_scopes=["moderator:manage:chat_messages"],
                    requires_moderator=True, requires_user=True),
    EventDefinition("channel.chat.clear_user_messages", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m, user_id=b),
                    required_scopes=["moderator:manage:chat_messages"],
                    requires_moderator=True, requires_user=True),

    # Shoutout
    EventDefinition("channel.shoutout.create", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m),
                    required_scopes=["moderator:manage:shoutouts"],
                    requires_moderator=True),
    EventDefinition("channel.shoutout.receive", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m),
                    required_scopes=["moderator:manage:shoutouts"],
                    requires_moderator=True),

    # Ban / Unban
    EventDefinition("channel.ban", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m),
                    required_scopes=["moderator:manage:banned_users"],
                    requires_moderator=True),
    EventDefinition("channel.unban", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m),
                    required_scopes=["moderator:manage:banned_users"],
                    requires_moderator=True),

    # Shield Mode
    EventDefinition("channel.shield_mode.begin", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m),
                    required_scopes=["moderator:manage:shield_mode"],
                    requires_moderator=True),
    EventDefinition("channel.shield_mode.end", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m),
                    required_scopes=["moderator:manage:shield_mode"],
                    requires_moderator=True),

    # Unban Requests
    EventDefinition("channel.unban_request.create", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m),
                    required_scopes=["moderator:manage:unban_requests"],
                    requires_moderator=True),
    EventDefinition("channel.unban_request.resolve", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m),
                    required_scopes=["moderator:manage:unban_requests"],
                    requires_moderator=True),

    # Usuarios Sospechosos
    EventDefinition("channel.suspicious_user.message", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m),
                    required_scopes=["moderator:read:suspicious_users"],
                    requires_moderator=True),
    EventDefinition("channel.suspicious_user.update", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m),
                    required_scopes=["moderator:read:suspicious_users"],
                    requires_moderator=True),

    # Automod
    EventDefinition("automod.message.hold", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m),
                    required_scopes=["moderator:manage:automod"],
                    requires_moderator=True),
    EventDefinition("automod.message.update", "1",
                    lambda b, m, u: _build_condition(b, moderator_id=m),
                    required_scopes=["moderator:manage:automod"],
                    requires_moderator=True),
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

        # Cache de scopes
        self._broadcaster_scopes = None
        self._scopes_cache_time = 0
        self._scopes_cache_ttl = 300  # 5 minutos

        # Handlers mapeados por tipo de evento
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
    # ESPERA DEL WEBHOOK (nueva ruta /twitch/webhook)
    # ============================================================

    def wait_for_webhook(self, timeout: int = 60, check_interval: int = 2):
        """Espera a que el webhook esté activo en la ruta /twitch/webhook."""
        if self._webhook_checked and self._webhook_ready:
            return True

        callback_url = settings.EVENTSUB_CALLBACK_URL
        if not callback_url:
            logger.error("❌ EVENTSUB_CALLBACK_URL no configurado")
            return False

        # NUEVA RUTA: /twitch/webhook
        webhook_url = f"{callback_url}/twitch/webhook"
        logger.info(f"⏳ Esperando que el webhook esté activo: {webhook_url}")

        start_time = time.time()
        while time.time() - start_time < timeout:
            # Intentar primero con la URL pública
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
    # VERIFICACIÓN DE SCOPES
    # ============================================================

    def _get_broadcaster_scopes(self) -> List[str]:
        """Obtiene los scopes del token del broadcaster desde la API de Twitch."""
        now = time.time()
        if self._broadcaster_scopes and (now - self._scopes_cache_time) < self._scopes_cache_ttl:
            return self._broadcaster_scopes

        try:
            token = settings.BROADCASTER_TOKEN
            if not token:
                return []

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
                return self._broadcaster_scopes
            else:
                logger.warning(f"⚠️ No se pudieron obtener scopes: {r.status_code}")
                return []

        except Exception as e:
            logger.error(f"❌ Error obteniendo scopes: {e}")
            return []

    def _has_required_scopes(self, required_scopes: List[str]) -> bool:
        """Verifica si el broadcaster tiene todos los scopes requeridos."""
        if not required_scopes:
            return True

        broadcaster_scopes = self._get_broadcaster_scopes()
        if not broadcaster_scopes:
            return False

        missing = [s for s in required_scopes if s not in broadcaster_scopes]
        if missing:
            logger.info(f"⚠️ Scopes faltantes: {', '.join(missing)}")
            return False

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
    # PROCESADOR DE WEBHOOK (punto de entrada desde webhook.py)
    # ============================================================

    def process_webhook(self, message_id: str, event_type: str, event_data: Dict):
        """Procesa un evento recibido desde el webhook."""
        if self.is_duplicate(message_id):
            self.stats["events_duplicated"] += 1
            logger.info(f"⏭️ Evento duplicado ignorado: {message_id}")
            return

        self.stats["events_processed"] += 1
        logger.info(f"📨 Evento {event_type} recibido (ID: {message_id})")

        # Buscar handler
        handler = self._handlers.get(event_type, self._on_generic_event)
        # Ejecutar de forma asíncrona
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
    # HANDLERS GENÉRICOS Y ESPECÍFICOS
    # ============================================================

    async def _on_generic_event(self, data):
        """Handler por defecto para eventos sin handler específico."""
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
    # TOKEN - SIEMPRE APP ACCESS TOKEN
    # ============================================================

    def _get_app_token(self) -> str:
        return getattr(settings, "APP_ACCESS_TOKEN", "")

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
                return

            for sub in r.json().get("data", []):
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
                return set()

            existing = set()
            for sub in r.json().get("data", []):
                event_type = sub["type"]
                condition = tuple(sorted((k, str(v)) for k, v in sub["condition"].items()))
                existing.add((event_type, condition))
            return existing
        except Exception as e:
            logger.error(f"Error obteniendo suscripciones: {e}")
            return set()

    def _ensure_subscription(self, headers, event_def: EventDefinition, existing: Set, moderator_id: str):
        """Crea una suscripción si no existe y los scopes son suficientes."""
        condition = event_def.condition_builder(
            settings.BROADCASTER_ID,
            moderator_id if event_def.requires_moderator else None,
            settings.BROADCASTER_ID if event_def.requires_user else None
        )

        key = (event_def.type, tuple(sorted((k, str(v)) for k, v in condition.items())))

        if key in existing:
            self.stats["subscriptions_skipped"] += 1
            # ✅ Log de evento ya existente (skipped)
            logger.info(f"⏭️ {event_def.type} ya existe, omitiendo")
            return True

        # Verificar scopes antes de crear
        if event_def.required_scopes:
            if not self._has_required_scopes(event_def.required_scopes):
                self.stats["subscriptions_failed_scopes"] += 1
                # ✅ Log de evento omitido por scopes faltantes
                logger.warning(f"⚠️ Omitiendo {event_def.type}: Scopes faltantes: {', '.join(event_def.required_scopes)}")
                log_service.add_log('warning', f'Omitiendo {event_def.type}: Scopes faltantes', 'bot')
                return False

        try:
            # NUEVA RUTA: /twitch/webhook
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

            # ✅ Log de intento de suscripción
            logger.info(f"📡 Intentando suscribir: {event_def.type} (v{event_def.version})")

            r = self.session.post(
                "https://api.twitch.tv/helix/eventsub/subscriptions",
                headers=headers,
                json=payload,
                timeout=self.HTTP_TIMEOUT
            )

            if r.status_code == 202:
                self.stats["subscriptions_created"] += 1
                existing.add(key)
                # ✅ Log de éxito
                logger.info(f"✅ Suscrito a {event_def.type} (v{event_def.version})")
                log_service.add_log('info', f'Suscrito a {event_def.type}', 'bot')
                return True

            if r.status_code == 409:
                existing.add(key)
                self.stats["subscriptions_skipped"] += 1
                # ✅ Log de conflicto (ya existe)
                logger.info(f"⏭️ {event_def.type} ya existe (409), omitiendo")
                return True

            # Errores que no deben reintentarse (400, 401, 403)
            if r.status_code in (400, 401, 403):
                error_detail = r.text
                try:
                    error_json = r.json()
                    error_detail = error_json.get("message", r.text)
                except:
                    pass

                if r.status_code == 403:
                    # ✅ Log de error 403 (scopes insuficientes)
                    logger.warning(f"⚠️ {event_def.type}: 403 - {error_detail} (scopes insuficientes)")
                    log_service.add_log('warning', f'{event_def.type}: 403 - Scopes insuficientes', 'bot')
                    self.stats["subscriptions_failed_scopes"] += 1
                else:
                    # ✅ Log de otros errores 4xx
                    logger.error(f"❌ Error en {event_def.type}: {r.status_code} - {error_detail}")
                    log_service.add_log('error', f'Error suscribiendo a {event_def.type}: {r.status_code}', 'bot')
                    self.stats["subscription_errors"] += 1
                return False

            # Errores que pueden reintentarse (429, 5xx)
            if r.status_code in (429, 500, 502, 503, 504):
                # ✅ Log de error temporal
                logger.warning(f"⚠️ {event_def.type}: {r.status_code} - reintentando más tarde")
                return False

            self.stats["subscription_errors"] += 1
            # ✅ Log de error desconocido
            logger.error(f"❌ Error en {event_def.type}: {r.status_code} - {r.text}")
            log_service.add_log('error', f'Error suscribiendo a {event_def.type}: {r.status_code}', 'bot')
            return False

        except Exception as e:
            self.stats["subscription_errors"] += 1
            # ✅ Log de excepción
            logger.error(f"❌ Excepción en {event_def.type}: {e}", exc_info=True)
            log_service.add_log('error', f'Excepción suscribiendo a {event_def.type}: {e}', 'bot')
            return False

    def subscribe_to_events(self):
        """Punto de entrada principal para crear todas las suscripciones."""
        # Esperar a que el webhook esté activo
        if not self.wait_for_webhook(timeout=60):
            logger.warning("⚠️ Webhook no disponible, pero continuando con suscripciones...")

        app_token = self._get_app_token()
        if not app_token:
            logger.error("❌ No hay APP_ACCESS_TOKEN configurado")
            log_service.add_log('error', 'No hay APP_ACCESS_TOKEN para EventSub', 'bot')
            return

        headers = {
            "Authorization": f"Bearer {app_token}",
            "Client-Id": settings.CLIENT_ID,
            "Content-Type": "application/json"
        }

        # Limpiar suscripciones inválidas
        self._cleanup_invalid_subscriptions(headers)

        # Obtener suscripciones existentes
        existing = self._get_existing_subscriptions(headers)

        # IDs necesarios
        broadcaster_id = settings.BROADCASTER_ID
        moderator_id = getattr(settings, "MODERATOR_USER_ID", broadcaster_id)

        logger.info(f"📡 Suscribiendo {len(EVENTS)} eventos con App Token")
        log_service.add_log('info', f'Suscribiendo {len(EVENTS)} eventos con App Token', 'bot')

        successful = 0
        failed = 0
        skipped = 0

        for event_def in EVENTS:
            result = self._ensure_subscription(headers, event_def, existing, moderator_id)
            if result:
                successful += 1
            else:
                failed += 1
            # Pequeña pausa para evitar rate limiting
            time.sleep(0.5)

        logger.info(f"📊 Resultado: {successful} suscripciones creadas, {failed} fallidas, {len(existing)} existentes")
        log_service.add_log('info', f'EventSub: {successful} creadas, {failed} fallidas', 'bot')

    # ============================================================
    # CIERRE
    # ============================================================

    def stop(self):
        self.session.close()
        logger.info("🛑 EventSub detenido")
        log_service.add_log('info', 'EventSub detenido', 'bot')


# Instancia global
eventsub_service = EventSubService()