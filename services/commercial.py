"""
Servicio para reproducir comerciales
"""

from typing import Optional

from config import settings
from services.twitch_api import TwitchAPI
from services.log_service import log_service
from exceptions import TwitchAPIError
from utils.logger import get_logger

logger = get_logger(__name__)


class CommercialManager:
    """
    Servicio para gestionar comerciales en el stream
    """
    
    VALID_DURATIONS = [30, 60, 90, 120, 150, 180]
    
    def __init__(self):
        self.api = TwitchAPI(use_broadcaster_token=True)
        self.broadcaster_id = settings.BROADCASTER_ID
    
    async def run_commercial(self, duration: int = 30) -> dict:
        if duration not in self.VALID_DURATIONS:
            log_service.add_log('warning', f'Duración inválida de comercial: {duration}', 'bot')
            raise ValueError(f"Duración inválida. Usa: {self.VALID_DURATIONS}")
        
        logger.info(f"Reproduciendo comercial de {duration} segundos")
        
        try:
            result = self.api.post(
                "channels/commercial",
                json={
                    "broadcaster_id": self.broadcaster_id,
                    "length": duration
                }
            )
            
            commercial_data = result.get("data", [{}])[0]
            length = commercial_data.get("length", duration)
            message = commercial_data.get("message", "")
            retry_after = commercial_data.get("retry_after", 0)
            
            logger.info(f"Comercial reproducido: {length}s, esperar {retry_after}s")
            log_service.add_log('info', f'Comercial de {length}s reproducido', 'bot')
            
            return {
                "duration": length,
                "message": message,
                "retry_after": retry_after
            }
        except TwitchAPIError as e:
            logger.error(f"Error reproduciendo comercial: {e}")
            log_service.add_log('error', f'Error reproduciendo comercial: {e.message}', 'twitch_api')
            raise
        except Exception as e:
            logger.error(f"Error inesperado reproduciendo comercial: {e}")
            log_service.add_log('error', f'Error inesperado reproduciendo comercial: {e}', 'bot')
            raise