"""
Sistema de anti-spam
"""

import time
import re
from collections import defaultdict
from typing import Dict, Tuple, Optional

from services.config_service import config_service
from services.warning_manager import warning_manager
from services.log_service import log_service
from utils.logger import get_logger

logger = get_logger(__name__)


class AntiSpam:
    """Sistema para detectar y prevenir spam"""
    
    def __init__(self):
        # Configuración
        self.MAX_MESSAGES_PER_MINUTE = 15
        self.MAX_SIMILAR_MESSAGES = 3
        self.MAX_CAPS_RATIO = 0.7
        self.MIN_MESSAGE_LENGTH = 3
        
        # Almacenamiento temporal
        self.user_messages: Dict[str, list] = defaultdict(list)
        self.user_last_message: Dict[str, str] = {}
        self.user_similar_count: Dict[str, int] = defaultdict(int)
        
        # Palabras prohibidas
        self.banned_words = set()
        self._load_banned_words()
        
        # Registrar callback para cambios en config_service
        config_service.on_change(self._load_banned_words)
    
    def _load_banned_words(self):
        """Cargar palabras prohibidas desde config_service"""
        try:
            words = config_service.get_banned_words()
            self.banned_words = set(word.lower() for word in words)
            logger.debug(f"Palabras prohibidas cargadas: {len(self.banned_words)}")
            log_service.add_log('info', f'Palabras prohibidas cargadas: {len(self.banned_words)}', 'bot')
        except Exception as e:
            logger.error(f"Error cargando palabras prohibidas: {e}")
            log_service.add_log('error', f'Error cargando palabras prohibidas: {e}', 'bot')
            self.banned_words = set()
    
    def clean_message(self, text: str) -> str:
        """Limpiar mensaje eliminando emotes y caracteres especiales"""
        text = re.sub(r'[^\w\s]', '', text)
        return text.lower()
    
    def check_message(self, user_id: str, message: str, is_vip: bool = False, is_staff: bool = False) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """
        Verificar si un mensaje es spam y devolver acción a tomar.
        
        Returns:
            (is_spam, action, warning_type, reason)
            action: 'warning', 'timeout', 'ban' o None si no es spam
            warning_type: 'caps', 'rate', 'repeat', 'word'
        """
        # Staff está exento de todo
        if is_staff:
            return False, None, None, None
        
        current_time = time.time()
        clean_msg = self.clean_message(message)
        
        # 1. Verificar mensajes vacíos o muy cortos
        if len(clean_msg) < self.MIN_MESSAGE_LENGTH:
            return False, None, None, None
        
        # 2. Verificar mayúsculas excesivas (solo para no-VIP)
        if not is_vip:
            caps_count = sum(1 for c in message if c.isupper())
            caps_ratio = caps_count / len(message) if len(message) > 0 else 0
            
            if caps_ratio > self.MAX_CAPS_RATIO and len(message) > 10:
                log_service.add_log('warning', f'Exceso de mayúsculas detectado de usuario {user_id}', 'moderation')
                action, count = warning_manager.check_and_get_action(user_id, 'caps')
                return True, action, 'caps', f"EXCESO_MAYUSCULAS (advertencia {count})"
        
        # 3. Verificar rate limit (mensajes por minuto)
        user_timestamps = self.user_messages[user_id]
        user_timestamps = [ts for ts in user_timestamps if current_time - ts < 60]
        self.user_messages[user_id] = user_timestamps
        
        if len(user_timestamps) >= self.MAX_MESSAGES_PER_MINUTE:
            log_service.add_log('warning', f'Rate limit excedido para usuario {user_id}', 'moderation')
            action, count = warning_manager.check_and_get_action(user_id, 'rate')
            return True, action, 'rate', f"RATE_LIMIT (advertencia {count})"
        
        # 4. Verificar mensajes repetidos
        last_msg = self.user_last_message.get(user_id, "")
        
        if last_msg and clean_msg == last_msg:
            self.user_similar_count[user_id] += 1
            
            if self.user_similar_count[user_id] >= self.MAX_SIMILAR_MESSAGES:
                self.user_similar_count[user_id] = 0
                log_service.add_log('warning', f'Mensaje repetido detectado de usuario {user_id}', 'moderation')
                action, count = warning_manager.check_and_get_action(user_id, 'repeat')
                return True, action, 'repeat', f"MENSAJE_REPETIDO (advertencia {count})"
        else:
            self.user_similar_count[user_id] = 0
        
        # 5. Verificar palabras prohibidas (VIPs están exentos)
        if not is_vip and self.banned_words:
            words = clean_msg.split()
            for word in words:
                if word in self.banned_words:
                    log_service.add_log('warning', f'Palabra prohibida "{word}" detectada de usuario {user_id}', 'moderation')
                    action, count = warning_manager.check_and_get_action(user_id, 'word')
                    return True, action, 'word', f"PALABRA_PROHIBIDA: {word} (advertencia {count})"
        
        # Actualizar registros
        self.user_messages[user_id].append(current_time)
        self.user_last_message[user_id] = clean_msg
        
        return False, None, None, None
    
    def reload_banned_words(self):
        """Recargar palabras prohibidas (público)"""
        self._load_banned_words()
        logger.info(f"🔄 Palabras prohibidas recargadas: {len(self.banned_words)}")
        log_service.add_log('info', f'Palabras prohibidas recargadas: {len(self.banned_words)}', 'moderation')


anti_spam = AntiSpam()