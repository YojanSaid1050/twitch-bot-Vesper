"""
Sistema de gestión de advertencias para infracciones (enlaces, palabras, spam, etc.)
"""

import time
from typing import Dict, Optional, Tuple
from datetime import datetime

from services.config_service import config_service
from utils.logger import get_logger

logger = get_logger(__name__)


class WarningManager:
    """
    Gestiona advertencias por tipo de infracción.
    Cada usuario tiene un contador por tipo.
    """
    def __init__(self):
        # Estructura: {user_id: {type: count}}
        self.warnings: Dict[str, Dict[str, int]] = {}
        self._load_data()

    def _load_data(self):
        """Cargar advertencias desde config_service"""
        try:
            data = config_service.get('warning_manager', {})
            self.warnings = data.get('warnings', {})
        except Exception as e:
            logger.error(f"Error cargando advertencias: {e}")
            self.warnings = {}

    def _save_data(self):
        """Guardar advertencias en config_service"""
        try:
            config_service.set('warning_manager', {'warnings': self.warnings})
        except Exception as e:
            logger.error(f"Error guardando advertencias: {e}")

    def get_warning_count(self, user_id: str, warning_type: str = 'link') -> int:
        """Obtener número de advertencias de un usuario para un tipo"""
        return self.warnings.get(user_id, {}).get(warning_type, 0)

    def increment_warning(self, user_id: str, warning_type: str = 'link') -> int:
        """Incrementar advertencia y devolver nuevo contador"""
        if user_id not in self.warnings:
            self.warnings[user_id] = {}
        self.warnings[user_id][warning_type] = self.warnings[user_id].get(warning_type, 0) + 1
        self._save_data()
        return self.warnings[user_id][warning_type]

    def clear_warnings(self, user_id: str, warning_type: str = 'link') -> int:
        """Limpiar advertencias de un usuario para un tipo"""
        count = self.get_warning_count(user_id, warning_type)
        if user_id in self.warnings and warning_type in self.warnings[user_id]:
            del self.warnings[user_id][warning_type]
            if not self.warnings[user_id]:
                del self.warnings[user_id]
            self._save_data()
        return count

    def get_max_warnings(self) -> int:
        """Obtener el máximo de advertencias desde la configuración"""
        return config_service.get('moderation.max_warnings', 3)

    def check_and_get_action(self, user_id: str, warning_type: str = 'link') -> Tuple[str, int]:
        """
        Incrementa advertencia y determina la acción a tomar.
        Retorna (acción, current_count)
        acción: 'warning', 'timeout', 'ban'
        """
        max_warnings = self.get_max_warnings()
        current = self.increment_warning(user_id, warning_type)
        if current >= max_warnings + 1:
            return 'ban', current
        elif current == max_warnings:
            return 'timeout', current
        else:
            return 'warning', current

    def reset_after_timeout(self, user_id: str, warning_type: str = 'link'):
        """Resetear advertencias a 1 después de un timeout (para no acumular)"""
        if user_id in self.warnings and warning_type in self.warnings[user_id]:
            self.warnings[user_id][warning_type] = 1
            self._save_data()

    def get_all_warnings_summary(self) -> Dict[str, Dict]:
        """
        Devuelve un resumen de todas las advertencias:
        {
            user_id: {
                'user_name': str,
                'warnings': { 'link': 3, 'word': 1, ... }
            }
        }
        """
        result = {}
        for user_id, types in self.warnings.items():
            result[user_id] = {
                'user_name': self._get_user_name(user_id),
                'warnings': types.copy()
            }
        return result

    def _get_user_name(self, user_id: str) -> str:
        # Intentar obtener el nombre desde link_manager o devolver el ID
        try:
            from services.link_manager import link_manager
            name = link_manager.get_user_name_by_id(user_id)
            if name and name != user_id:
                return name
        except:
            pass
        return f"Usuario {user_id[:8]}"


# Instancia global
warning_manager = WarningManager()