# services/eventsub/handlers/chat.py
"""
Handlers para eventos de chat.
"""

from services.eventsub.models import ChatMessageDeleteEvent, ChatClearEvent, ChatClearUserMessagesEvent
from services.eventsub.event_bus import event_bus, Event
from services.eventsub.statistics import stats_collector
from utils.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)


async def handle_chat_message_delete(event_data: dict) -> None:
    """Procesa un evento de eliminación de mensaje de chat."""
    try:
        delete = ChatMessageDeleteEvent(
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
        await event_bus.publish(Event(type="chat.message_delete", payload=delete))
        logger.info(f"Mensaje de chat eliminado de {delete.target_user_name} por {delete.moderator_name}")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_chat_message_delete: {e}")
        stats_collector.increment("subscription_errors")


async def handle_chat_clear(event_data: dict) -> None:
    """Procesa un evento de limpieza de chat."""
    try:
        clear = ChatClearEvent(
            moderator_user_id=event_data.get("moderator_user_id", ""),
            moderator_name=event_data.get("moderator_user_name", "Staff"),
            moderator_login=event_data.get("moderator_user_login", ""),
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="chat.clear", payload=clear))
        logger.info(f"Chat limpiado por {clear.moderator_name}")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_chat_clear: {e}")
        stats_collector.increment("subscription_errors")


async def handle_chat_clear_user_messages(event_data: dict) -> None:
    """Procesa un evento de limpieza de mensajes de un usuario."""
    try:
        clear = ChatClearUserMessagesEvent(
            target_user_id=event_data.get("target_user_id", ""),
            target_user_name=event_data.get("target_user_name", "Desconocido"),
            target_user_login=event_data.get("target_user_login", ""),
            moderator_user_id=event_data.get("moderator_user_id", ""),
            moderator_name=event_data.get("moderator_user_name", "Staff"),
            moderator_login=event_data.get("moderator_user_login", ""),
            broadcaster_user_id=event_data.get("broadcaster_user_id", ""),
            broadcaster_name=event_data.get("broadcaster_user_name", "Desconocido"),
            broadcaster_login=event_data.get("broadcaster_user_login", ""),
            timestamp=datetime.now()
        )
        await event_bus.publish(Event(type="chat.clear_user_messages", payload=clear))
        logger.info(f"Mensajes de {clear.target_user_name} limpiados por {clear.moderator_name}")
        stats_collector.increment("events_processed")
    except Exception as e:
        logger.error(f"Error en handle_chat_clear_user_messages: {e}")
        stats_collector.increment("subscription_errors")