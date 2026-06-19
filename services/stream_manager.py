"""
Gestión del stream (título, categoría, markers)
"""

from typing import Optional, Tuple
from config import settings
from services.twitch_api import TwitchAPI
from services.log_service import log_service
from exceptions import TwitchAPIError, ResourceNotFoundError
from utils.logger import get_logger

logger = get_logger(__name__)


class StreamManager:
    """
    Servicio para gestionar el stream del broadcaster
    """
    
    def __init__(self):
        self.api = TwitchAPI(use_broadcaster_token=True)
        self.broadcaster_id = settings.BROADCASTER_ID
    
    async def update_title(self, title: str) -> bool:
        logger.info(f"Actualizando título a: {title}")
        try:
            response = self.api.patch(
                "channels",
                params={"broadcaster_id": self.broadcaster_id},
                json={"title": title}
            )
            # Log de éxito (moderación)
            log_service.add_log('info', f'Título del stream actualizado: "{title}"', 'moderation')
            return response is None
        except TwitchAPIError as e:
            logger.error(f"Error actualizando título: {e}")
            log_service.add_log('error', f'Error actualizando título: {e.message}', 'twitch_api')
            raise
        except Exception as e:
            logger.error(f"Error inesperado actualizando título: {e}")
            log_service.add_log('error', f'Error inesperado actualizando título: {e}', 'bot')
            raise
    
    async def update_game(self, game_name: str) -> Tuple[str, str]:
        logger.info(f"Buscando categoría: {game_name}")
        try:
            search_result = self.api.get(
                "search/categories",
                params={"query": game_name}
            )
            data = search_result.get("data", [])
            if not data:
                log_service.add_log('warning', f'Categoría no encontrada: {game_name}', 'twitch_api')
                raise ResourceNotFoundError(f"No se encontró la categoría: {game_name}")
            
            game_lower = game_name.lower()
            exact_match = None
            starts_with_match = None
            
            for game in data:
                game_title_lower = game["name"].lower()
                if game_title_lower == game_lower:
                    exact_match = game
                    break
                if game_title_lower.startswith(game_lower) and not starts_with_match:
                    starts_with_match = game
            
            if exact_match:
                selected_game = exact_match
                logger.info(f"Coincidencia exacta encontrada: {selected_game['name']}")
            elif starts_with_match:
                selected_game = starts_with_match
                logger.info(f"Coincidencia por inicio encontrada: {selected_game['name']}")
            else:
                selected_game = data[0]
                logger.info(f"Usando primer resultado: {selected_game['name']}")
            
            game_id = selected_game["id"]
            actual_name = selected_game["name"]
            
            logger.info(f"Categoría seleccionada: {actual_name} (ID: {game_id})")
            response = self.api.patch(
                "channels",
                params={"broadcaster_id": self.broadcaster_id},
                json={"game_id": game_id}
            )
            # Log de éxito (moderación)
            log_service.add_log('info', f'Juego del stream actualizado: "{actual_name}"', 'moderation')
            return game_id, actual_name
        except ResourceNotFoundError:
            # Ya se registró el warning, solo relanzamos
            raise
        except TwitchAPIError as e:
            logger.error(f"Error actualizando juego: {e}")
            log_service.add_log('error', f'Error actualizando juego: {e.message}', 'twitch_api')
            raise
        except Exception as e:
            logger.error(f"Error inesperado actualizando juego: {e}")
            log_service.add_log('error', f'Error inesperado actualizando juego: {e}', 'bot')
            raise
    
    async def create_marker(self) -> str:
        logger.info("Creando marker...")
        try:
            result = self.api.post(
                "streams/markers",
                json={"user_id": self.broadcaster_id}
            )
            marker_id = result.get("data", [{}])[0].get("id", "unknown")
            logger.info(f"Marker creado: {marker_id}")
            log_service.add_log('info', f'Marker creado: {marker_id}', 'bot')  # Sistema
            return marker_id
        except TwitchAPIError as e:
            logger.error(f"Error creando marker: {e}")
            log_service.add_log('error', f'Error creando marker: {e.message}', 'twitch_api')
            raise
        except Exception as e:
            logger.error(f"Error inesperado creando marker: {e}")
            log_service.add_log('error', f'Error inesperado creando marker: {e}', 'bot')
            raise