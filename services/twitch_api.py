"""
Cliente base para la API de Twitch con auto-refresh
"""

import time
import requests
from typing import Dict, Any, Optional

from config import settings
from exceptions import TwitchAPIError, RateLimitError, AuthenticationError
from utils.logger import get_logger

logger = get_logger(__name__)


class TwitchAPI:
    """
    Cliente HTTP para la API de Twitch con manejo de errores y auto-refresh
    """
    
    def __init__(self, use_broadcaster_token: bool = False):
        """
        Args:
            use_broadcaster_token: Si usar token del streamer o del bot
        """
        self.use_broadcaster_token = use_broadcaster_token
        self.base_url = "https://api.twitch.tv/helix"
        self._last_request_time = 0
        self._min_request_interval = 0.1  # 100ms mínimo entre requests
    
    @property
    def headers(self) -> Dict[str, str]:
        """Headers según el token configurado"""
        if self.use_broadcaster_token:
            return settings.BROADCASTER_HEADERS
        return settings.BOT_HEADERS
    
    def _rate_limit_wait(self):
        """Esperar si es necesario para respetar rate limits básicos"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()
    
    def _refresh_token_if_needed(self, response: requests.Response):
        """Si hay error 401, intentar refrescar el token"""
        if response.status_code == 401:
            from services.token_manager import token_manager
            
            logger.warning("Token expirado, intentando refrescar...")
            
            if self.use_broadcaster_token:
                token_manager.refresh_broadcaster_token()
            else:
                token_manager.refresh_bot_token()
            
            # Esperar un momento para que se actualicen los headers
            time.sleep(1)
            return True
        return False
    
    def _handle_response(self, response: requests.Response, endpoint: str, retry: bool = True) -> Any:
        """
        Manejar la respuesta de la API
        
        Args:
            response: Respuesta de requests
            endpoint: Endpoint llamado (para logging)
            retry: Si debe reintentar después de refrescar token
        
        Returns:
            Datos de la respuesta (JSON o None)
        
        Raises:
            TwitchAPIError: Según el código de error
        """
        # Si es 401 y tenemos refresh_token, intentar refrescar y reintentar
        if response.status_code == 401 and retry:
            if self._refresh_token_if_needed(response):
                # Reintentar la petición original
                return self._retry_request(endpoint)
        
        if response.status_code == 204:
            return None  # Sin contenido (éxito)
        
        if response.status_code == 200:
            return response.json()
        
        # Manejar errores específicos
        if response.status_code == 400:
            raise TwitchAPIError(
                f"Solicitud inválida: {response.text}",
                status_code=400
            )
        elif response.status_code == 401:
            raise AuthenticationError(
                "Token inválido o expirado (no se pudo refrescar automáticamente)",
                status_code=401,
                response_text=response.text
            )
        elif response.status_code == 429:
            raise RateLimitError(
                "Rate limit excedido. Espera unos segundos.",
                status_code=429,
                response_text=response.text
            )
        elif response.status_code == 404:
            raise TwitchAPIError(
                "Recurso no encontrado",
                status_code=404,
                response_text=response.text
            )
        else:
            raise TwitchAPIError(
                f"Error {response.status_code}: {response.text}",
                status_code=response.status_code,
                response_text=response.text
            )
    
    def _retry_request(self, endpoint: str, method: str = "GET", params: Dict = None, json_data: Dict = None):
        """Reintentar una petición después de refrescar token"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers, params=params)
            elif method == "PATCH":
                response = requests.patch(url, headers=self.headers, params=params, json=json_data)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, params=params, json=json_data)
            elif method == "PUT":
                response = requests.put(url, headers=self.headers, params=params, json=json_data)
            elif method == "DELETE":
                response = requests.delete(url, headers=self.headers, params=params)
            else:
                raise ValueError(f"Método HTTP no soportado: {method}")
            
            return self._handle_response(response, endpoint, retry=False)
        except Exception as e:
            raise TwitchAPIError(f"Error en reintento: {e}")
    
    def get(self, endpoint: str, params: Dict = None) -> Any:
        """GET request a la API"""
        self._rate_limit_wait()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        logger.debug(f"GET {url} params={params}")
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            return self._handle_response(response, endpoint)
        except requests.RequestException as e:
            raise TwitchAPIError(f"Error de conexión: {e}")
    
    def patch(self, endpoint: str, params: Dict = None, json: Dict = None) -> Any:
        """PATCH request a la API"""
        self._rate_limit_wait()
        
        logger.debug(f"PATCH {endpoint} params={params} json={json}")
        
        try:
            response = requests.patch(
                f"{self.base_url}/{endpoint.lstrip('/')}",
                headers=self.headers,
                params=params,
                json=json
            )
            return self._handle_response(response, endpoint)
        except requests.RequestException as e:
            raise TwitchAPIError(f"Error de conexión: {e}")
    
    def post(self, endpoint: str, params: Dict = None, json: Dict = None) -> Any:
        """POST request a la API"""
        self._rate_limit_wait()
        
        logger.debug(f"POST {endpoint} params={params} json={json}")
        
        try:
            response = requests.post(
                f"{self.base_url}/{endpoint.lstrip('/')}",
                headers=self.headers,
                params=params,
                json=json
            )
            return self._handle_response(response, endpoint)
        except requests.RequestException as e:
            raise TwitchAPIError(f"Error de conexión: {e}")
    
    def put(self, endpoint: str, params: Dict = None, json: Dict = None) -> Any:
        """PUT request a la API"""
        self._rate_limit_wait()
        
        logger.debug(f"PUT {endpoint} params={params} json={json}")
        
        try:
            response = requests.put(
                f"{self.base_url}/{endpoint.lstrip('/')}",
                headers=self.headers,
                params=params,
                json=json
            )
            return self._handle_response(response, endpoint)
        except requests.RequestException as e:
            raise TwitchAPIError(f"Error de conexión: {e}")
    
    def delete(self, endpoint: str, params: Dict = None) -> Any:
        """DELETE request a la API"""
        self._rate_limit_wait()
        
        logger.debug(f"DELETE {endpoint} params={params}")
        
        try:
            response = requests.delete(
                f"{self.base_url}/{endpoint.lstrip('/')}",
                headers=self.headers,
                params=params
            )
            return self._handle_response(response, endpoint)
        except requests.RequestException as e:
            raise TwitchAPIError(f"Error de conexión: {e}")