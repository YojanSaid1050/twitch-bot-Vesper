"""
Utilidades de formateo
"""

from datetime import timedelta
import random


def format_time_delta(delta: timedelta) -> str:
    """Formatear timedelta para mostrar"""
    days = delta.days
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    
    parts = []
    if days > 0:
        parts.append(f"{days} día{'s' if days > 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hora{'s' if hours > 1 else ''}")
    if minutes > 0 or not parts:
        parts.append(f"{minutes} minuto{'s' if minutes != 1 else ''}")
    
    return " ".join(parts)


def format_choice(options: list) -> str:
    """Formatear elección aleatoria"""
    return random.choice(options)


def truncate_message(message: str, max_length: int = 450) -> str:
    """Truncar mensaje si es muy largo"""
    if len(message) <= max_length:
        return message
    return message[:max_length - 3] + "..."