"""
Servicio para crear y gestionar clips de Twitch
"""

import requests
import time
from typing import Optional, Dict

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class ClipService:
    """Servicio para crear clips de Twitch"""
    
    def __init__(self):
        self.broadcaster_id = settings.BROADCASTER_ID
        self.headers = settings.BROADCASTER_HEADERS
    
    async def create_clip(self) -> Optional[Dict]:
        """
        Crear un clip del stream actual
        
        Returns:
            Dict con información del clip o error manejado
        """
        try:
            url = "https://api.twitch.tv/helix/clips"
            
            params = {
                "broadcaster_id": self.broadcaster_id
            }
            
            logger.info(f"Creando clip...")
            
            response = requests.post(
                url,
                headers=self.headers,
                params=params
            )
            
            logger.info(f"Respuesta status: {response.status_code}")
            
            if response.status_code == 202:
                data = response.json()
                clip_data = data.get("data", [])
                
                if clip_data and len(clip_data) > 0:
                    clip_id = clip_data[0].get("id")
                    
                    if clip_id:
                        clip_url = f"https://clips.twitch.tv/{clip_id}"
                        logger.info(f"Clip creado: {clip_url}")
                        
                        return {
                            "success": True,
                            "url": clip_url,
                            "id": clip_id
                        }
                
                return {
                    "success": True,
                    "url": "El clip se está procesando... espera unos segundos",
                    "id": "processing"
                }
            
            elif response.status_code == 404:
                error_text = response.text.lower()
                if "channel offline" in error_text or "offline" in error_text:
                    return {
                        "success": False,
                        "error": "offline"
                    }
                return {
                    "success": False,
                    "error": "not_found"
                }
            
            elif response.status_code == 401:
                return {
                    "success": False,
                    "error": "unauthorized"
                }
            
            else:
                return {
                    "success": False,
                    "error": "unknown",
                    "details": f"Error {response.status_code}"
                }
            
        except Exception as e:
            logger.error(f"Error creando clip: {e}")
            return {
                "success": False,
                "error": "exception",
                "details": str(e)
            }


# Instancia global
clip_service = ClipService()