# services/eventsub/tokens.py
"""
Validación de tokens para EventSub.
Lectura de tokens desde la base de datos mediante TokenRepository.
"""

import time
import requests
from typing import Optional
from config import settings
from services.eventsub.definitions import TokenInfo
from services.eventsub.cache import cache
from database.token_repository import TokenRepository  # ← Importar el repositorio
from utils.logger import get_logger

logger = get_logger(__name__)


class TokenValidator:
    """Valida tokens y obtiene su información, con caché."""

    CACHE_KEY_PREFIX = "token_info_"
    CACHE_TTL = 300  # 5 minutos

    @classmethod
    def _get_token_from_db(cls, token_type: str) -> Optional[str]:
        """
        Obtiene el token de acceso desde la base de datos usando TokenRepository.
        """
        try:
            # Mapear token_type a account (coinciden)
            token_data = TokenRepository.get_token("twitch", token_type)
            if token_data:
                return token_data.get("access_token")
            else:
                logger.warning(f"No se encontró token '{token_type}' en la base de datos")
                return None
        except Exception as e:
            logger.error(f"Error al obtener token '{token_type}' de la BD: {e}")
            return None

    @classmethod
    def get_token_info(cls, token_type: str) -> Optional[TokenInfo]:
        """
        Obtiene información de un token (scopes, user_id, login, expires).
        Tipos: 'broadcaster', 'moderator', 'user', 'app'
        """
        cache_key = f"{cls.CACHE_KEY_PREFIX}{token_type}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        token = cls._get_token_from_db(token_type)
        if not token:
            logger.warning(f"No hay token para {token_type} en la BD")
            return None

        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "Client-Id": settings.CLIENT_ID,
            }
            response = requests.get(
                "https://id.twitch.tv/oauth2/validate",
                headers=headers,
                timeout=10,
            )
            if response.status_code != 200:
                logger.warning(
                    f"Error validando token {token_type}: {response.status_code}"
                )
                return None

            data = response.json()
            info = TokenInfo(
                scopes=data.get("scopes", []),
                user_id=data.get("user_id"),
                login=data.get("login"),
                expires_at=time.time() + data.get("expires_in", 0),
                fetched_at=time.time(),
            )
            cache.set(cache_key, info, ttl=cls.CACHE_TTL)
            return info

        except Exception as e:
            logger.error(f"Error obteniendo info de token {token_type}: {e}")
            return None

    @classmethod
    def invalidate(cls, token_type: str):
        """Invalida la caché de un token."""
        cache_key = f"{cls.CACHE_KEY_PREFIX}{token_type}"
        cache.invalidate(cache_key)

    @classmethod
    def get_raw_token(cls, token_type: str) -> Optional[str]:
        """
        Método público para obtener el token crudo desde la BD sin validar.
        Útil para SubscriptionManager.
        """
        return cls._get_token_from_db(token_type)