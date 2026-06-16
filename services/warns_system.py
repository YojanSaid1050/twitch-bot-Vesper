"""
Sistema de advertencias
"""

from services.moderation_actions import ModerationActions
from database import db
from utils.logger import get_logger

logger = get_logger(__name__)


class WarnsSystem:
    """Sistema de advertencias para moderación"""
    
    MAX_WARNS = 3  # Máximo de advertencias antes de timeout/ban
    
    def __init__(self):
        self.mod_actions = ModerationActions()
    
    async def add_warning(self, user_id: str, user_name: str, reason: str, warned_by: str) -> tuple:
        """
        Agregar advertencia y verificar si se necesita acción
        
        Returns:
            (warning_count, action_taken, action_type)
        """
        # Agregar advertencia
        db.add_warning(user_id, user_name, reason, warned_by)
        
        # Obtener total de advertencias
        warnings = db.get_warnings(user_id)
        warning_count = len(warnings)
        
        action_taken = False
        action_type = None
        
        # Aplicar acción según cantidad de advertencias
        if warning_count >= self.MAX_WARNS:
            # Timeout de 10 minutos
            await self.mod_actions.timeout(user_name, 600, "Máximo de advertencias alcanzado")
            action_taken = True
            action_type = "timeout"
            # Limpiar advertencias después del timeout
            db.clear_warnings(user_id)
        elif warning_count == self.MAX_WARNS - 1:
            action_type = "warning_last"
        
        return warning_count, action_taken, action_type


# Instancia global
warns_system = WarnsSystem()