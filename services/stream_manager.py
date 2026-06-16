"""
Gestión del stream (título, categoría, markers)
"""

from typing import Optional, Tuple
from config import settings
from services.twitch_api import TwitchAPI
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
        """
        Actualizar el título del stream
        
        Args:
            title: Nuevo título
        
        Returns:
            True si fue exitoso
        
        Raises:
            TwitchAPIError: Si hay error en la API
        """
        logger.info(f"Actualizando título a: {title}")
        
        response = self.api.patch(
            "channels",
            params={"broadcaster_id": self.broadcaster_id},
            json={"title": title}
        )
        
        # 204 significa éxito sin contenido
        return response is None
    
    async def update_game(self, game_name: str) -> Tuple[str, str]:
        """
        Actualizar la categoría/juego del stream con búsqueda mejorada
        
        Args:
            game_name: Nombre del juego a buscar
        
        Returns:
            Tuple (game_id, game_name) del juego encontrado
        
        Raises:
            ResourceNotFoundError: Si no se encuentra el juego
            TwitchAPIError: Si hay error en la API
        """
        logger.info(f"Buscando categoría: {game_name}")
        
        # Buscar categoría
        search_result = self.api.get(
            "search/categories",
            params={"query": game_name}
        )
        
        data = search_result.get("data", [])
        
        if not data:
            raise ResourceNotFoundError(f"No se encontró la categoría: {game_name}")
        
        # Buscar coincidencia exacta (insensible a mayúsculas)
        game_lower = game_name.lower()
        exact_match = None
        starts_with_match = None
        
        for game in data:
            game_title_lower = game["name"].lower()
            
            # Coincidencia exacta
            if game_title_lower == game_lower:
                exact_match = game
                break
            
            # Coincidencia por inicio (ej: "VALORANT" coincide con "VALORANT: algo")
            if game_title_lower.startswith(game_lower) and not starts_with_match:
                starts_with_match = game
        
        # Priorizar coincidencia exacta > coincidencia por inicio > primer resultado
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
        
        # Actualizar
        response = self.api.patch(
            "channels",
            params={"broadcaster_id": self.broadcaster_id},
            json={"game_id": game_id}
        )
        
        return game_id, actual_name
    
    async def create_marker(self) -> str:
        """
        Crear un marker en el stream
        
        Returns:
            ID del marker creado
        
        Raises:
            TwitchAPIError: Si hay error en la API
        """
        logger.info("Creando marker...")
        
        result = self.api.post(
            "streams/markers",
            json={"user_id": self.broadcaster_id}
        )
        
        marker_id = result.get("data", [{}])[0].get("id", "unknown")
        logger.info(f"Marker creado: {marker_id}")
        
        return marker_id