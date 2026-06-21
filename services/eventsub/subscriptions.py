# services/eventsub/subscriptions.py
"""
Comunicación con la API de EventSub de Twitch.
"""

import json
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
from config import settings
from services.eventsub.definitions import EventDefinition, Subscription
from services.eventsub.conditions import condition_builder
from services.eventsub.exceptions import SubscriptionError
from services.eventsub.retry import with_retry, RetryConfig
from services.eventsub.statistics import stats_collector
from services.eventsub.tokens import TokenValidator
from utils.logger import get_logger

logger = get_logger(__name__)


class SubscriptionManager:
    """Gestiona la creación, listado y eliminación de suscripciones."""

    BASE_URL = "https://api.twitch.tv/helix/eventsub/subscriptions"

    def __init__(self):
        # Ya no guardamos el token en memoria fija, lo obtendremos bajo demanda desde la BD.
        pass

    def _get_headers(self) -> Dict[str, str]:
        """
        Siempre usa App Access Token para todas las operaciones de gestión
        de suscripciones webhook, tal como exige la API de Twitch.
        El token se obtiene desde la base de datos.
        """
        app_token = TokenValidator.get_raw_token("app")
        if not app_token:
            raise SubscriptionError("No se pudo obtener APP_ACCESS_TOKEN desde la base de datos")

        return {
            "Authorization": f"Bearer {app_token}",
            "Client-Id": settings.CLIENT_ID,
            "Content-Type": "application/json",
        }

    @with_retry(RetryConfig(max_attempts=3, retryable_exceptions=(SubscriptionError,)))
    def create_subscription(self, event_def: EventDefinition) -> bool:
        """
        Crea una suscripción usando SIEMPRE App Access Token.
        La validación de scopes del usuario correspondiente ya se realizó antes.
        """
        condition = condition_builder.build(event_def)
        callback_url = f"{settings.EVENTSUB_CALLBACK_URL}/twitch/webhook"
        secret = settings.TWITCH_WEBHOOK_SECRET

        if not secret:
            logger.warning("TWITCH_WEBHOOK_SECRET vacío. Las suscripciones pueden fallar.")

        payload = {
            "type": event_def.type,
            "version": event_def.version,
            "condition": condition,
            "transport": {
                "method": "webhook",
                "callback": callback_url,
                "secret": secret,
            },
        }

        headers = self._get_headers()

        try:
            logger.info(f"Creando suscripción {event_def.type}...")
            response = requests.post(
                self.BASE_URL,
                headers=headers,
                json=payload,
                timeout=10,
            )
        except requests.RequestException as e:
            raise SubscriptionError(f"Error de red: {e}")

        if response.status_code == 202:
            stats_collector.increment("subscriptions_created")
            logger.info(f"Suscripción creada: {event_def.type}")
            return True

        if response.status_code == 409:
            logger.info(f"Suscripción ya existe: {event_def.type}")
            return False

        # Error 403: scopes insuficientes (la validación previa debería evitarlo)
        if response.status_code == 403:
            error_detail = self._extract_error(response)
            logger.error(
                f"Error 403 al crear {event_def.type}: {error_detail}. "
                f"Scopes requeridos: {event_def.required_scopes}"
            )
            stats_collector.increment("subscriptions_failed_scopes")
            raise SubscriptionError(
                f"Error 403 al crear {event_def.type}: {error_detail}"
            )

        # Error 400: condición incorrecta o problema con el token
        if response.status_code == 400:
            error_detail = self._extract_error(response)
            logger.error(
                f"Error 400 al crear {event_def.type}: {error_detail}. "
                f"Condición: {condition}"
            )
            raise SubscriptionError(
                f"Error 400 al crear {event_def.type}: {error_detail}"
            )

        error_detail = self._extract_error(response)
        raise SubscriptionError(
            f"Error {response.status_code} al crear {event_def.type}: {error_detail}"
        )

    @with_retry(RetryConfig(max_attempts=2))
    def delete_subscription(self, subscription_id: str) -> bool:
        """Elimina una suscripción por su ID usando App Access Token desde la BD."""
        headers = self._get_headers()
        try:
            response = requests.delete(
                f"{self.BASE_URL}?id={subscription_id}",
                headers=headers,
                timeout=10,
            )
        except requests.RequestException as e:
            raise SubscriptionError(f"Error de red al eliminar: {e}")

        if response.status_code in (200, 204):
            logger.info(f"Suscripción eliminada: {subscription_id}")
            return True
        error_detail = self._extract_error(response)
        raise SubscriptionError(f"Error al eliminar {subscription_id}: {error_detail}")

    def list_subscriptions(self) -> List[Subscription]:
        """Lista todas las suscripciones activas usando App Access Token desde la BD."""
        headers = self._get_headers()
        subscriptions = []
        cursor = None
        while True:
            params = {"first": 100}
            if cursor:
                params["after"] = cursor
            try:
                response = requests.get(
                    self.BASE_URL,
                    headers=headers,
                    params=params,
                    timeout=10,
                )
            except requests.RequestException as e:
                logger.error(f"Error listando suscripciones: {e}")
                break

            if response.status_code != 200:
                logger.error(f"Error listando suscripciones: {response.status_code}")
                break

            data = response.json()
            for sub_data in data.get("data", []):
                subscriptions.append(
                    Subscription(
                        id=sub_data["id"],
                        type=sub_data["type"],
                        version=sub_data["version"],
                        status=sub_data["status"],
                        condition=sub_data["condition"],
                        transport=sub_data["transport"],
                        created_at=datetime.fromisoformat(
                            sub_data["created_at"].replace("Z", "+00:00")
                        ),
                    )
                )
            cursor = data.get("pagination", {}).get("cursor")
            if not cursor:
                break
        return subscriptions

    @staticmethod
    def _extract_error(response) -> str:
        try:
            error_json = response.json()
            return error_json.get("message", response.text)
        except:
            return response.text[:200]


# Instancia global
subscription_manager = SubscriptionManager()