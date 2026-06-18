import time
import requests
from typing import Dict, Optional, Literal, Tuple
from datetime import datetime, timedelta
from enum import Enum

class TokenType(Enum):
    BOT = "bot"
    BROADCASTER = "broadcaster"
    APP = "app"
    SPOTIFY = "spotify"

class OAuthError(Exception):
    pass

class OAuthManager:
    MAX_RETRIES = 3
    BASE_DELAY = 1

    @staticmethod
    def refresh_twitch_token(client_id: str, client_secret: str, refresh_token: str, token_type: TokenType) -> Dict:
        if not refresh_token:
            raise OAuthError(f"No hay refresh_token para {token_type.value}")

        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        return OAuthManager._post_with_retry(
            url="https://id.twitch.tv/oauth2/token",
            data=data,
            token_type=token_type,
            is_spotify=False
        )

    @staticmethod
    def refresh_spotify_token(client_id: str, client_secret: str, refresh_token: str) -> Dict:
        if not refresh_token:
            raise OAuthError("No hay SPOTIFY_REFRESH_TOKEN")

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        }
        return OAuthManager._post_with_retry(
            url="https://accounts.spotify.com/api/token",
            data=data,
            token_type=TokenType.SPOTIFY,
            is_spotify=True
        )

    @staticmethod
    def get_app_token(client_id: str, client_secret: str) -> Dict:
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials"
        }
        return OAuthManager._post_with_retry(
            url="https://id.twitch.tv/oauth2/token",
            data=data,
            token_type=TokenType.APP,
            is_spotify=False
        )

    @staticmethod
    def _post_with_retry(url: str, data: dict, token_type: TokenType, is_spotify: bool) -> Dict:
        last_exception = None
        for attempt in range(1, OAuthManager.MAX_RETRIES + 1):
            try:
                response = requests.post(url, data=data, timeout=10)
                if response.status_code == 200:
                    return response.json()

                if response.status_code == 401:
                    error_msg = "Refresh token inválido o expirado"
                    if not is_spotify and "invalid refresh token" in response.text.lower():
                        raise OAuthError(f"Refresh token inválido para {token_type.value}: {error_msg}")
                    raise OAuthError(f"Error 401 en {token_type.value}: {response.text}")

                if response.status_code in (429, 500, 502, 503):
                    delay = OAuthManager.BASE_DELAY * (2 ** (attempt - 1))
                    time.sleep(delay)
                    continue

                raise OAuthError(f"Error {response.status_code} en {token_type.value}: {response.text}")

            except requests.exceptions.Timeout:
                last_exception = OAuthError(f"Timeout en {token_type.value}")
                time.sleep(OAuthManager.BASE_DELAY * (2 ** (attempt - 1)))
                continue
            except requests.exceptions.ConnectionError as e:
                last_exception = OAuthError(f"Error de conexión en {token_type.value}: {e}")
                time.sleep(OAuthManager.BASE_DELAY * (2 ** (attempt - 1)))
                continue
            except OAuthError as e:
                raise
            except Exception as e:
                last_exception = OAuthError(f"Error inesperado en {token_type.value}: {e}")
                time.sleep(OAuthManager.BASE_DELAY * (2 ** (attempt - 1)))
                continue

        raise OAuthError(f"Fallo después de {OAuthManager.MAX_RETRIES} intentos para {token_type.value}") from last_exception