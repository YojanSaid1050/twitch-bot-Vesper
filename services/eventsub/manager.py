# services/eventsub/manager.py
"""
Manager del sistema EventSub: orquesta todos los módulos.
"""

import asyncio
from typing import Optional
from services.eventsub.registry import EVENTS
from services.eventsub.subscriptions import subscription_manager
from services.eventsub.cleanup import cleaner
from services.eventsub.scopes import scope_validator
from services.eventsub.tokens import TokenValidator
from services.eventsub.deduplicator import deduplicator
from services.eventsub.statistics import stats_collector
from services.eventsub.webhook import webhook_handler
from services.eventsub.dispatcher import dispatcher
from services.eventsub.exceptions import EventSubError
from utils.logger import get_logger
from config import settings

logger = get_logger(__name__)


class EventSubManager:
    """Orquestador principal del sistema EventSub."""

    def __init__(self):
        self._initialized = False
        self._webhook_ready = False

    def initialize(self):
        """Inicializa el sistema (valida tokens y scopes básicos)."""
        if self._initialized:
            return
        logger.info("Inicializando EventSubManager...")
        # Validar app token
        app_info = TokenValidator.get_token_info("app")
        if not app_info:
            logger.error("App Access Token no válido")
            raise EventSubError("App Access Token no válido")

        # Validar broadcaster token (para eventos que requieren User Token)
        broadcaster_info = TokenValidator.get_token_info("broadcaster")
        if not broadcaster_info:
            logger.warning("Broadcaster Token no válido. Los eventos que requieran User Token fallarán.")
        else:
            logger.info(f"Broadcaster Token válido para {broadcaster_info.login}")

        self._initialized = True
        logger.info("EventSubManager inicializado correctamente")

    async def start(self):
        """Inicia el sistema: limpia suscripciones y crea las necesarias."""
        if not self._initialized:
            self.initialize()

        # Validar webhook
        if not await self._check_webhook():
            logger.warning("Webhook no disponible, continuando de todas formas")

        # Limpiar suscripciones inválidas
        deleted = cleaner.cleanup()
        if deleted:
            logger.info(f"Se eliminaron {deleted} suscripciones inválidas")

        # Obtener suscripciones existentes
        existing = subscription_manager.list_subscriptions()
        existing_set = {(sub.type, tuple(sorted(sub.condition.items()))) for sub in existing}

        # Crear suscripciones faltantes
        created = 0
        for event_type, event_def in EVENTS.items():
            if not event_def.enabled:
                continue

            # Verificar scopes (contra el usuario indicado por scope_owner)
            try:
                scope_validator.validate(
                    event_def.required_scopes,
                    event_def.scope_owner,
                    event_type
                )
            except Exception as e:
                logger.warning(f"Saltando {event_type} por scopes: {e}")
                stats_collector.increment("subscriptions_failed_scopes")
                continue

            # Verificar si ya existe
            condition = self._build_condition_for_check(event_def)
            key = (event_type, tuple(sorted(condition.items())))
            if key in existing_set:
                logger.debug(f"Evento {event_type} ya existe, omitiendo")
                continue

            # Crear
            try:
                success = subscription_manager.create_subscription(event_def)
                if success:
                    created += 1
                    stats_collector.increment("subscriptions_created")
                await asyncio.sleep(0.3)  # Rate limiting
            except Exception as e:
                logger.error(f"Error creando {event_type}: {e}")
                stats_collector.increment("subscriptions_failed")

        logger.info(f"Suscripciones creadas: {created}")

    def _build_condition_for_check(self, event_def):
        from services.eventsub.conditions import condition_builder
        return condition_builder.build(event_def)

    async def _check_webhook(self) -> bool:
        """Verifica que el webhook esté activo."""
        import requests
        callback_url = settings.EVENTSUB_CALLBACK_URL
        if not callback_url:
            return False
        webhook_url = f"{callback_url}/twitch/webhook"
        try:
            resp = requests.get(webhook_url, timeout=3)
            if resp.status_code == 200:
                self._webhook_ready = True
                return True
        except:
            pass
        return False

    def stop(self):
        """Detiene el sistema (cierra sesiones, etc.)."""
        logger.info("Deteniendo EventSubManager")


# Instancia global
manager = EventSubManager()