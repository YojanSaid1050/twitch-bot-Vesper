"""
Validadores de entrada para comandos
"""

import re
from typing import Tuple, Optional


def validate_title(title: str) -> Tuple[bool, Optional[str]]:
    """
    Validar título del stream
    
    Returns:
        (es_valido, mensaje_error)
    """
    if not title or not title.strip():
        return False, "El título no puede estar vacío"
    
    if len(title) > 140:
        return False, "El título no puede exceder 140 caracteres"
    
    return True, None


def validate_game_name(game_name: str) -> Tuple[bool, Optional[str]]:
    """
    Validar nombre del juego/categoría
    
    Returns:
        (es_valido, mensaje_error)
    """
    if not game_name or not game_name.strip():
        return False, "El nombre del juego no puede estar vacío"
    
    if len(game_name) > 100:
        return False, "El nombre del juego es demasiado largo"
    
    # Evitar caracteres potencialmente peligrosos
    if re.search(r'[<>]', game_name):
        return False, "El nombre contiene caracteres inválidos"
    
    return True, None


def validate_slow_mode_time(seconds: int) -> Tuple[bool, Optional[str]]:
    """
    Validar tiempo para modo lento (segundos)
    """
    if seconds < 1:
        return False, "El tiempo debe ser al menos 1 segundo"
    
    if seconds > 120:
        return False, "El tiempo no puede exceder 120 segundos"
    
    return True, None


def validate_follower_duration(minutes: int) -> Tuple[bool, Optional[str]]:
    """
    Validar duración para modo followers (minutos)
    """
    if minutes < 1:
        return False, "La duración debe ser al menos 1 minuto"
    
    if minutes > 129600:  # 90 días
        return False, "La duración no puede exceder 90 días"
    
    return True, None