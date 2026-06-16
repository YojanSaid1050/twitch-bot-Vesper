"""
Servicio para comandos personalizados
"""

import random
import re
from typing import Dict, Optional

from database import db
from utils.logger import get_logger

logger = get_logger(__name__)


class CustomCommandsService:
    """Servicio para gestionar comandos personalizados"""
    
    def __init__(self):
        self._cache = {}
        self._load_cache()
    
    def _load_cache(self):
        """Cargar comandos en caché"""
        commands = db.get_all_commands()
        for cmd in commands:
            self._cache[cmd["command_name"]] = True
    
    def add_command(self, name: str, response: str, created_by: str, cooldown: int = 0) -> tuple:
        """
        Agregar comando personalizado
        
        Returns:
            (success, message)
        """
        # Validar nombre
        if not re.match(r'^[a-záéíóúñ0-9_]+$', name.lower()):
            return False, "Nombre inválido (solo letras, números y _)"
        
        if len(name) > 20:
            return False, "Nombre muy largo (máximo 20 caracteres)"
        
        if len(response) > 400:
            return False, "Respuesta muy larga (máximo 400 caracteres)"
        
        # Verificar si es comando base
        base_commands = ["hola", "ping", "comandos", "title", "game", "slow", "followers", "emote", "subscribers", "vip", "timeout", "ban", "8ball", "dado", "moneda", "elige", "lurk", "uptime", "viewers", "shoutout", "announce", "warn"]
        
        if name.lower() in base_commands:
            return False, f"'{name}' es un comando base del bot"
        
        if db.add_command(name, response, created_by, cooldown):
            self._cache[name.lower()] = True
            return True, f"Comando !{name} creado correctamente"
        
        return False, f"Error al crear el comando"
    
    def remove_command(self, name: str) -> tuple:
        """Eliminar comando personalizado"""
        if db.remove_command(name):
            self._cache.pop(name.lower(), None)
            return True, f"Comando !{name} eliminado"
        
        return False, f"Comando !{name} no existe"
    
    def get_command(self, name: str) -> Optional[Dict]:
        """Obtener comando personalizado"""
        return db.get_command(name)
    
    def list_commands(self) -> list:
        """Listar todos los comandos personalizados"""
        return db.get_all_commands()
    
    def process_response(self, response: str, ctx) -> str:
        """Procesar variables en la respuesta"""
        # Variables disponibles
        vars_map = {
            "{user}": ctx.author.name,
            "{user_id}": str(ctx.author.id),
            "{channel}": ctx.channel.name,
            "{random_emote}": random.choice(["🕯️", "⚔️", "🔥", "📜", "👁️", "🎭", "🌙"])
        }
        
        for var, value in vars_map.items():
            response = response.replace(var, value)
        
        return response


# Instancia global
custom_commands_service = CustomCommandsService()