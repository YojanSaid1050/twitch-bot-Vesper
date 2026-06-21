# services/eventsub/cleanup.py
"""
Limpieza de suscripciones inválidas o desactualizadas.
"""

from typing import List, Set
from config import settings
from services.eventsub.subscriptions import subscription_manager
from services.eventsub.registry import EVENTS
from services.eventsub.conditions import condition_builder
from services.eventsub.definitions import Subscription
from services.eventsub.statistics import stats_collector
from utils.logger import get_logger

logger = get_logger(__name__)


class SubscriptionCleaner:
    """Limpia suscripciones que son inválidas o no coinciden con la definición."""

    # Campos que son OBLIGATORIOS para que la suscripción sea válida
    # Si faltan o no coinciden → se elimina la suscripción
    CRITICAL_FIELDS: Set[str] = {
        "broadcaster_user_id",
        "to_broadcaster_user_id",
        "from_broadcaster_user_id",
        # No incluir moderator_user_id ni user_id aquí
    }

    # Campos que son OPCIONALES para la condición
    # Si Twitch no los devuelve (None) → se ignoran
    OPTIONAL_FIELDS: Set[str] = {
        "moderator_user_id",
        "user_id",
        "reward_id",
    }

    def cleanup(self) -> int:
        """
        Verifica todas las suscripciones y elimina las que son inválidas.
        Retorna el número de suscripciones eliminadas.
        """
        try:
            subs = subscription_manager.list_subscriptions()
        except Exception as e:
            logger.error(f"Error listando suscripciones para limpieza: {e}")
            return 0

        deleted = 0
        for sub in subs:
            if self._should_delete(sub):
                try:
                    subscription_manager.delete_subscription(sub.id)
                    stats_collector.increment("subscriptions_recreated")
                    deleted += 1
                except Exception as e:
                    logger.warning(f"No se pudo eliminar sub {sub.id}: {e}")
        return deleted

    def _should_delete(self, sub: Subscription) -> bool:
        """
        Determina si una suscripción debe ser eliminada.
        Usa lógica de campos críticos vs opcionales para evitar
        eliminaciones falsas por campos que Twitch omite en la respuesta.
        """
        # 1. Estados que siempre deben eliminarse
        if sub.status in (
            "authorization_revoked",
            "webhook_callback_verification_failed",
            "notification_failures_exceeded",
            "webhook_disconnected",
        ):
            logger.info(f"Suscripción inválida {sub.type} ({sub.id}): {sub.status}")
            return True

        # 2. Verificar si el evento está definido en nuestro registro
        event_def = EVENTS.get(sub.type)
        if not event_def:
            logger.info(f"Evento no registrado: {sub.type}, eliminando")
            return True

        # 3. Verificar versión
        if sub.version != event_def.version:
            logger.info(
                f"Versión incorrecta para {sub.type}: esperada {event_def.version}, "
                f"actual {sub.version}"
            )
            return True

        # 4. Verificar callback
        expected_callback = f"{settings.EVENTSUB_CALLBACK_URL}/twitch/webhook"
        if sub.transport.get("callback") != expected_callback:
            logger.info(
                f"Callback incorrecto para {sub.type}: esperado {expected_callback}, "
                f"actual {sub.transport.get('callback')}"
            )
            return True

        # 5. Verificar condición (con lógica de campos críticos vs opcionales)
        expected_condition = condition_builder.build(event_def)

        for key, expected_value in expected_condition.items():
            actual_value = sub.condition.get(key)

            # ============================================================
            # REGLA 1: Si el campo es OPCIONAL y Twitch no lo devuelve (None)
            #          → lo ignoramos, NO es motivo de eliminación
            # ============================================================
            if key in self.OPTIONAL_FIELDS and actual_value is None:
                logger.debug(
                    f"Campo opcional {key} ausente para {sub.type}, ignorando"
                )
                continue

            # ============================================================
            # REGLA 2: Si el campo es CRÍTICO y no coincide → eliminar
            # ============================================================
            if key in self.CRITICAL_FIELDS:
                if str(actual_value) != str(expected_value):
                    logger.info(
                        f"Condición diferente para {sub.type}: campo crítico {key} "
                        f"esperado {expected_value}, actual {actual_value}"
                    )
                    return True
                continue

            # ============================================================
            # REGLA 3: Para campos no clasificados (por defecto, son opcionales)
            #          Solo eliminamos si el valor existe y no coincide
            # ============================================================
            if actual_value is not None and str(actual_value) != str(expected_value):
                logger.info(
                    f"Condición diferente para {sub.type}: campo {key} "
                    f"esperado {expected_value}, actual {actual_value}"
                )
                return True

        # Todas las verificaciones pasaron → suscripción válida
        return False


# Instancia global
cleaner = SubscriptionCleaner()