"""
Servicio para crear y gestionar clips de Twitch
"""

import asyncio
import requests
from typing import Optional, Dict

from config import settings
from services.log_service import log_service
from utils.logger import get_logger

logger = get_logger(__name__)


class ClipService:
    """Servicio para crear clips de Twitch"""
    
    def __init__(self):
        self.broadcaster_id = settings.BROADCASTER_ID

    @property
    def headers(self) -> Dict[str, str]:
        # Se leen en cada petición: guardarlos en __init__ dejaba el token de
        # arranque fijo y !clip fallaba con 401 cuando el token se renovaba.
        return settings.BROADCASTER_HEADERS

    def _post_clip(self) -> requests.Response:
        url = "https://api.twitch.tv/helix/clips"
        params = {"broadcaster_id": self.broadcaster_id}
        response = requests.post(url, headers=self.headers, params=params, timeout=10)
        if response.status_code == 401:
            from services.token_manager import token_manager
            if token_manager.refresh_broadcaster_token():
                response = requests.post(url, headers=self.headers, params=params, timeout=10)
        return response

    async def create_clip(self) -> Optional[Dict]:
        try:
            logger.info("Creando clip...")
            response = await asyncio.to_thread(self._post_clip)

            logger.info(f"Respuesta status: {response.status_code}")
            
            if response.status_code == 202:
                data = response.json()
                clip_data = data.get("data", [])
                
                if clip_data and len(clip_data) > 0:
                    clip_id = clip_data[0].get("id")
                    if clip_id:
                        clip_url = f"https://clips.twitch.tv/{clip_id}"
                        logger.info(f"Clip creado: {clip_url}")
                        log_service.add_log('info', f'Clip creado: {clip_url}', 'bot')
                        return {"success": True, "url": clip_url, "id": clip_id}
                
                return {"success": True, "url": "El clip se está procesando... espera unos segundos", "id": "processing"}
            
            elif response.status_code == 404:
                error_text = response.text.lower()
                if "channel offline" in error_text or "offline" in error_text:
                    log_service.add_log('warning', 'Intento de clip con stream offline', 'bot')
                    return {"success": False, "error": "offline"}
                return {"success": False, "error": "not_found"}
            
            elif response.status_code == 401:
                log_service.add_log('error', 'Token no autorizado para crear clip', 'twitch_api')
                return {"success": False, "error": "unauthorized"}
            
            else:
                log_service.add_log('error', f'Error creando clip: {response.status_code}', 'twitch_api')
                return {"success": False, "error": "unknown", "details": f"Error {response.status_code}"}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de conexión creando clip: {e}")
            log_service.add_log('error', f'Error de conexión creando clip: {e}', 'twitch_api')
            return {"success": False, "error": "connection_error", "details": str(e)}
        except Exception as e:
            logger.error(f"Error creando clip: {e}")
            log_service.add_log('error', f'Error creando clip: {e}', 'bot')
            return {"success": False, "error": "exception", "details": str(e)}


clip_service = ClipService()