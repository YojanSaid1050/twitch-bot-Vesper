"""
Servicio para reproducir comerciales
"""

from typing import Optional

from config import settings
from services.twitch_api import TwitchAPI
from exceptions import TwitchAPIError
from utils.logger import get_logger


logger = get_logger(__name__)


class CommercialManager:
    """
    Servicio para gestionar comerciales en el stream
    """
    
    # Duración válida en segundos (30, 60, 90, 120, 150, 180)
    VALID_DURATIONS = [30, 60, 90, 120, 150, 180]
    
    def __init__(self):
        self.api = TwitchAPI(use_broadcaster_token=True)
        self.broadcaster_id = settings.BROADCASTER_ID
    
    async def run_commercial(self, duration: int = 30) -> dict:
        """
        Reproducir un comercial
        
        Args:
            duration: Duración en segundos (30, 60, 90, 120, 150, 180)
        
        Returns:
            Dict con información del comercial
        
        Raises:
            ValueError: Si la duración no es válida
            TwitchAPIError: Si hay error en la API
        """
        if duration not in self.VALID_DURATIONS:
            raise ValueError(f"Duración inválida. Usa: {self.VALID_DURATIONS}")
        
        logger.info(f"Reproduciendo comercial de {duration} segundos")
        
        result = self.api.post(
            "channels/commercial",
            json={
                "broadcaster_id": self.broadcaster_id,
                "length": duration
            }
        )
        
        # El endpoint devuelve datos del comercial
        commercial_data = result.get("data", [{}])[0]
        length = commercial_data.get("length", duration)
        message = commercial_data.get("message", "")
        retry_after = commercial_data.get("retry_after", 0)
        
        logger.info(f"Comercial reproducido: {length}s, esperar {retry_after}s")
        
        return {
            "duration": length,
            "message": message,
            "retry_after": retry_after
        }