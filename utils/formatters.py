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

def format_duration_long(total_seconds: float) -> str:
    """
    Formatea una duración larga en español: "2 años, 3 meses y 5 días".
    Muestra como máximo tres unidades (años/meses/días u horas/minutos).
    """
    seconds = int(max(0, total_seconds))
    units = [
        ("año", "años", 365 * 86400),
        ("mes", "meses", 30 * 86400),
        ("día", "días", 86400),
        ("hora", "horas", 3600),
        ("minuto", "minutos", 60),
    ]
    parts = []
    for singular, plural, size in units:
        value, seconds = divmod(seconds, size)
        if value:
            parts.append(f"{value} {singular if value == 1 else plural}")
        if len(parts) == 3:
            break
    if not parts:
        return "menos de un minuto"
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + " y " + parts[-1]
