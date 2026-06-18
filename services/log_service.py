"""
Servicio de logs para el dashboard
Almacena logs importantes en memoria para su visualización
"""

from datetime import datetime
from typing import List, Dict, Optional, Callable
from collections import deque

from utils.logger import get_logger

logger = get_logger(__name__)

class LogService:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not LogService._initialized:
            self.max_logs = 1000  # Máximo de logs en memoria
            self.logs: deque = deque(maxlen=self.max_logs)
            LogService._initialized = True
            self._callbacks: List[Callable] = []

    def add_log(self, level: str, message: str, source: str = None, details: dict = None):
        """
        Añadir un log al sistema.
        level: 'info', 'warning', 'error', 'critical'
        """
        entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level.upper(),
            'message': message,
            'source': source or 'unknown',
            'details': details or {}
        }
        self.logs.append(entry)
        # Notificar callbacks
        for cb in self._callbacks:
            try:
                cb(entry)
            except Exception as e:
                logger.error(f"Error en callback de log: {e}")
        # También imprimir en consola para debug
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(f"[LOG] {entry['level']} - {entry['source']}: {message}")

    def get_logs(self, limit: int = 100, level_filter: str = None, source_filter: str = None) -> List[Dict]:
        """Obtener logs filtrados"""
        logs = list(self.logs)
        # Ordenar por timestamp descendente (más reciente primero)
        logs = sorted(logs, key=lambda x: x['timestamp'], reverse=True)
        if level_filter:
            logs = [l for l in logs if l['level'] == level_filter.upper()]
        if source_filter:
            logs = [l for l in logs if l['source'] == source_filter]
        return logs[:limit]

    def clear_logs(self):
        """Limpiar todos los logs"""
        self.logs.clear()
        self.add_log('info', 'Logs limpiados', 'system')

    def on_log(self, callback: Callable):
        """Registrar callback para nuevos logs"""
        self._callbacks.append(callback)


# Instancia global
log_service = LogService()