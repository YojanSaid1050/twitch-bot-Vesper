# services/eventsub/conditions.py
"""
Construcción automática de condiciones para EventSub.
"""

from typing import Dict
from services.eventsub.definitions import EventDefinition
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class ConditionBuilder:
    """Construye condiciones basadas en la definición del evento."""

    def __init__(self):
        self._placeholders = {
            "broadcaster_id": settings.BROADCASTER_ID,
            "moderator_id": getattr(settings, "MODERATOR_USER_ID", settings.BROADCASTER_ID),
            "user_id": getattr(settings, "BOT_ID", settings.BROADCASTER_ID),
            "client_id": settings.CLIENT_ID,
        }
        logger.debug(
            f"Placeholders inicializados: broadcaster_id={self._placeholders['broadcaster_id']}, "
            f"moderator_id={self._placeholders['moderator_id']}, "
            f"user_id={self._placeholders['user_id']}"
        )

    def build(self, event_def: EventDefinition) -> Dict[str, str]:
        """
        Construye el diccionario condition para el evento.
        """
        condition = {}
        for field_key, value_source in event_def.condition_fields.items():
            value = self._placeholders.get(value_source, value_source)
            if not value:
                raise ValueError(
                    f"Valor vacío para campo {field_key} en evento {event_def.type}"
                )
            condition[field_key] = str(value)
        return condition


# Instancia global
condition_builder = ConditionBuilder()