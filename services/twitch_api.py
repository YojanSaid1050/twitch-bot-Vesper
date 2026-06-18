"""
Cliente base para la API de Twitch con auto-refresh
"""

import time
import requests
from typing import Dict, Any, Optional

from config import settings
from exceptions import TwitchAPIError, RateLimitError, AuthenticationError
from utils.logger import get_logger
from services.log_service import log_service

logger = get_logger(__name__)


class TwitchAPI:
    """
    Cliente HTTP para la API de Twitch con manejo de errores y auto-refresh
    """
    
    def __init__(self, use_broadcaster_token: bool = False):
        self.use_broadcaster_token = use_broadcaster_token
        self.base_url = "https://api.twitch.tv/helix"
        self._last_request_time = 0
        self._min_request_interval = 0.1
        self._last_refresh_attempt = 0
        self._refresh_cooldown = 120
    
    @property
    def headers(self) -> Dict[str, str]:
        if self.use_broadcaster_token:
            return settings.BROADCASTER_HEADERS
        return settings.BOT_HEADERS
    
    def _rate_limit_wait(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()
    
    def _can_refresh(self) -> bool:
        now = time.time()
        if now - self._last_refresh_attempt < self._refresh_cooldown:
            return False
        self._last_refresh_attempt = now
        return True
    
    def _refresh_token(self):
        try:
            from services.token_manager import token_manager
            if self.use_broadcaster_token:
                return token_manager.refresh_broadcaster_token()
            else:
                return token_manager.refresh_bot_token()
        except Exception as e:
            logger.error(f"Error refrescando token: {e}")
            log_service.add_log('error', f'Error refrescando token en TwitchAPI: {e}', 'twitch_api')
            return False
    
    def _handle_response(self, response: requests.Response, endpoint: str, retry: bool = True) -> Any:
        if response.status_code == 401 and retry and self._can_refresh():
            logger.warning("Token expirado, intentando refrescar...")
            log_service.add_log('warning', f'Token expirado en endpoint {endpoint}, refrescando...', 'twitch_api')
            if self._refresh_token():
                time.sleep(1)
                return self._retry_request(endpoint)
            else:
                raise AuthenticationError(
                    "Token inválido y no se pudo refrescar automáticamente",
                    status_code=401,
                    response_text=response.text
                )
        
        if response.status_code == 204:
            return None
        
        if response.status_code == 200:
            return response.json()
        
        if response.status_code == 400:
            log_service.add_log('error', f'Error 400 en {endpoint}: {response.text[:100]}', 'twitch_api')
            raise TwitchAPIError(f"Solicitud inválida: {response.text}", status_code=400)
        elif response.status_code == 401:
            log_service.add_log('error', f'Error 401 en {endpoint}: Token inválido', 'twitch_api')
            raise AuthenticationError("Token inválido o expirado", status_code=401, response_text=response.text)
        elif response.status_code == 429:
            log_service.add_log('warning', f'Rate limit excedido en {endpoint}', 'twitch_api')
            raise RateLimitError("Rate limit excedido. Espera unos segundos.", status_code=429)
        elif response.status_code == 404:
            log_service.add_log('warning', f'Recurso no encontrado en {endpoint}', 'twitch_api')
            raise TwitchAPIError("Recurso no encontrado", status_code=404)
        else:
            log_service.add_log('error', f'Error {response.status_code} en {endpoint}', 'twitch_api')
            raise TwitchAPIError(f"Error {response.status_code}: {response.text}", status_code=response.status_code)
    
    def _retry_request(self, endpoint: str, method: str = "GET", params: Dict = None, json_data: Dict = None):
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers, params=params, timeout=10)
            elif method == "PATCH":
                response = requests.patch(url, headers=self.headers, params=params, json=json_data, timeout=10)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, params=params, json=json_data, timeout=10)
            elif method == "PUT":
                response = requests.put(url, headers=self.headers, params=params, json=json_data, timeout=10)
            elif method == "DELETE":
                response = requests.delete(url, headers=self.headers, params=params, timeout=10)
            else:
                raise ValueError(f"Método HTTP no soportado: {method}")
            return self._handle_response(response, endpoint, retry=False)
        except Exception as e:
            log_service.add_log('error', f'Error en reintento de {endpoint}: {e}', 'twitch_api')
            raise TwitchAPIError(f"Error en reintento: {e}")
    
    def get(self, endpoint: str, params: Dict = None) -> Any:
        self._rate_limit_wait()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        logger.debug(f"GET {url} params={params}")
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            return self._handle_response(response, endpoint)
        except requests.RequestException as e:
            log_service.add_log('error', f'Error de conexión en GET {endpoint}: {e}', 'twitch_api')
            raise TwitchAPIError(f"Error de conexión: {e}")
    
    def patch(self, endpoint: str, params: Dict = None, json: Dict = None) -> Any:
        self._rate_limit_wait()
        logger.debug(f"PATCH {endpoint} params={params} json={json}")
        try:
            response = requests.patch(
                f"{self.base_url}/{endpoint.lstrip('/')}",
                headers=self.headers,
                params=params,
                json=json,
                timeout=10
            )
            return self._handle_response(response, endpoint)
        except requests.RequestException as e:
            log_service.add_log('error', f'Error de conexión en PATCH {endpoint}: {e}', 'twitch_api')
            raise TwitchAPIError(f"Error de conexión: {e}")
    
    def post(self, endpoint: str, params: Dict = None, json: Dict = None) -> Any:
        self._rate_limit_wait()
        logger.debug(f"POST {endpoint} params={params} json={json}")
        try:
            response = requests.post(
                f"{self.base_url}/{endpoint.lstrip('/')}",
                headers=self.headers,
                params=params,
                json=json,
                timeout=10
            )
            return self._handle_response(response, endpoint)
        except requests.RequestException as e:
            log_service.add_log('error', f'Error de conexión en POST {endpoint}: {e}', 'twitch_api')
            raise TwitchAPIError(f"Error de conexión: {e}")
    
    def put(self, endpoint: str, params: Dict = None, json: Dict = None) -> Any:
        self._rate_limit_wait()
        logger.debug(f"PUT {endpoint} params={params} json={json}")
        try:
            response = requests.put(
                f"{self.base_url}/{endpoint.lstrip('/')}",
                headers=self.headers,
                params=params,
                json=json,
                timeout=10
            )
            return self._handle_response(response, endpoint)
        except requests.RequestException as e:
            log_service.add_log('error', f'Error de conexión en PUT {endpoint}: {e}', 'twitch_api')
            raise TwitchAPIError(f"Error de conexión: {e}")
    
    def delete(self, endpoint: str, params: Dict = None) -> Any:
        self._rate_limit_wait()
        logger.debug(f"DELETE {endpoint} params={params}")
        try:
            response = requests.delete(
                f"{self.base_url}/{endpoint.lstrip('/')}",
                headers=self.headers,
                params=params,
                timeout=10
            )
            return self._handle_response(response, endpoint)
        except requests.RequestException as e:
            log_service.add_log('error', f'Error de conexión en DELETE {endpoint}: {e}', 'twitch_api')
            raise TwitchAPIError(f"Error de conexión: {e}")