# services/eventsub/handlers/moderation.py
"""
Handlers para eventos de moderación.
"""

from services.eventsub.models import (
    BanEvent, UnbanEvent, ClearChatEvent, DeleteMessageEvent,
    SuspiciousUserEvent, ShieldModeEvent
)
from services.eventsub.event_bus import event_bus, Event
from services.eventsub.statistics import stats_collector
from utils.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)


async def handle_ban(event_data: dict) -> None:
    """Procesa un evento de ban."""
    try:
        is_permanent = event_data.get("end_time") is None
        duration = None if is_permanent else event_data.get("duration_seconds")
        ban = BanEvent(
            user_id=event_data.get("user_id", ""),
            user_name=event_data.get("user_name", "Desconocido"),
            user_login=event_data.get("user_login", ""),
            moderator_user_id=event_data.get("moderator_user_id", ""),
            moderator_name=event_data.get("moderator_user_name", "Staff"),
            moderator_login=event_data.get("moderator_user_login", ""),
            reason=event_data.get("reason", "Sin especificar"),
            duration_seconds=duration,
            is_permanent=is_permanent,
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="moderation.ban", payload=ban))
        logger.info(f"Ban procesado: {ban.user_name} por {ban.moderator_name} {'(permanente)' if ban.is_permanent else f'({ban.duration_seconds}s)'}")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_ban: {e}")
        stats_collector.increment("subscription_errors")


async def handle_unban(event_data: dict) -> None:
    """Procesa un evento de unban."""
    try:
        unban = UnbanEvent(
            user_id=event_data.get("user_id", ""),
            user_name=event_data.get("user_name", "Desconocido"),
            user_login=event_data.get("user_login", ""),
            moderator_user_id=event_data.get("moderator_user_id", ""),
            moderator_name=event_data.get("moderator_user_name", "Staff"),
            moderator_login=event_data.get("moderator_user_login", ""),
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="moderation.unban", payload=unban))
        logger.info(f"Unban procesado: {unban.user_name} por {unban.moderator_name}")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_unban: {e}")
        stats_collector.increment("subscription_errors")


async def handle_clear_chat(event_data: dict) -> None:
    """Procesa un evento de limpieza de chat."""
    try:
        clear = ClearChatEvent(
            moderator_user_id=event_data.get("moderator_user_id", ""),
            moderator_name=event_data.get("moderator_user_name", "Staff"),
            moderator_login=event_data.get("moderator_user_login", ""),
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="moderation.clear_chat", payload=clear))
        logger.info(f"Chat limpiado por {clear.moderator_name}")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_clear_chat: {e}")
        stats_collector.increment("subscription_errors")


async def handle_delete_message(event_data: dict) -> None:
    """Procesa un evento de eliminación de mensaje."""
    try:
        delete = DeleteMessageEvent(
            target_user_id=event_data.get("target_user_id", ""),
            target_user_name=event_data.get("target_user_name", "Desconocido"),
            target_user_login=event_data.get("target_user_login", ""),
            moderator_user_id=event_data.get("moderator_user_id", ""),
            moderator_name=event_data.get("moderator_user_name", "Staff"),
            moderator_login=event_data.get("moderator_user_login", ""),
            message_id=event_data.get("message_id", ""),
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="moderation.delete_message", payload=delete))
        logger.info(f"Mensaje eliminado de {delete.target_user_name} por {delete.moderator_name}")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_delete_message: {e}")
        stats_collector.increment("subscription_errors")


async def handle_suspicious_user(event_data: dict) -> None:
    """Procesa un evento de usuario sospechoso."""
    try:
        suspicious = SuspiciousUserEvent(
            user_id=event_data.get("user_id", ""),
            user_name=event_data.get("user_name", "Desconocido"),
            user_login=event_data.get("user_login", ""),
            moderator_user_id=event_data.get("moderator_user_id", ""),
            moderator_name=event_data.get("moderator_user_name", "Staff"),
            moderator_login=event_data.get("moderator_user_login", ""),
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            reason=event_data.get("reason", "Actividad sospechosa"),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="moderation.suspicious_user", payload=suspicious))
        logger.info(f"Usuario sospechoso: {suspicious.user_name}")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_suspicious_user: {e}")
        stats_collector.increment("subscription_errors")


async def handle_shield_mode(event_data: dict) -> None:
    """Procesa un evento de Shield Mode."""
    try:
        # Detectar si es begin o end
        event_type = event_data.get("subscription", {}).get("type", "")
        action = "begin" if "begin" in event_type else "end"
        shield = ShieldModeEvent(
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            moderator_user_id=event_data.get("moderator_user_id", ""),
            moderator_name=event_data.get("moderator_user_name", "Staff"),
            moderator_login=event_data.get("moderator_user_login", ""),
            action=action,
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="moderation.shield_mode", payload=shield))
        logger.info(f"Shield Mode {action} por {shield.moderator_name}")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_shield_mode: {e}")
        stats_collector.increment("subscription_errors")