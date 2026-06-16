"""
Sistema de anti-spam
"""

import time
import re
from collections import defaultdict
from typing import Dict, Tuple, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


class AntiSpam:
    """Sistema para detectar y prevenir spam"""
    
    def __init__(self):
        # Configuración
        self.MAX_MESSAGES_PER_MINUTE = 15
        self.MAX_SIMILAR_MESSAGES = 3
        self.MAX_CAPS_RATIO = 0.7  # 70% mayúsculas = spam
        self.MIN_MESSAGE_LENGTH = 5
        
        # Almacenamiento temporal
        self.user_messages: Dict[str, list] = defaultdict(list)  # {user: [timestamps]}
        self.user_last_message: Dict[str, str] = {}  # {user: last_message}
        self.user_similar_count: Dict[str, int] = defaultdict(int)
        
        # Palabras prohibidas
        self.banned_words = self._load_banned_words()
    
    def _load_banned_words(self) -> set:
        """Cargar palabras prohibidas"""
        # Palabras comunes ofensivas (ejemplo)
        return {
            "puta", "mierda", "coño", "joder", "cabron", "gilipollas",
            "hijodeputa", "pendejo", "marica", "verga", "carajo",
            # Agrega más según necesites
        }
    
    def clean_message(self, text: str) -> str:
        """Limpiar mensaje eliminando emotes y caracteres especiales"""
        # Eliminar emotes de Twitch comunes
        text = re.sub(r'[^\w\s]', '', text)
        return text.lower()
    
    def check_message(self, user_id: str, message: str) -> Tuple[bool, Optional[str]]:
        """
        Verificar si un mensaje es spam
        
        Returns:
            (is_spam, reason)
        """
        current_time = time.time()
        clean_msg = self.clean_message(message)
        
        # 1. Verificar mensajes vacíos o muy cortos
        if len(clean_msg) < self.MIN_MESSAGE_LENGTH:
            return False, None
        
        # 2. Verificar mayúsculas excesivas
        caps_count = sum(1 for c in message if c.isupper())
        caps_ratio = caps_count / len(message) if len(message) > 0 else 0
        
        if caps_ratio > self.MAX_CAPS_RATIO and len(message) > 10:
            return True, "EXCESO_MAYUSCULAS"
        
        # 3. Verificar rate limit (mensajes por minuto)
        user_timestamps = self.user_messages[user_id]
        
        # Limpiar timestamps viejos (más de 60 segundos)
        user_timestamps = [ts for ts in user_timestamps if current_time - ts < 60]
        self.user_messages[user_id] = user_timestamps
        
        if len(user_timestamps) >= self.MAX_MESSAGES_PER_MINUTE:
            return True, "RATE_LIMIT"
        
        # 4. Verificar mensajes repetidos
        last_msg = self.user_last_message.get(user_id, "")
        
        if last_msg and clean_msg == last_msg:
            self.user_similar_count[user_id] += 1
            
            if self.user_similar_count[user_id] >= self.MAX_SIMILAR_MESSAGES:
                self.user_similar_count[user_id] = 0
                return True, "MENSAJE_REPETIDO"
        else:
            self.user_similar_count[user_id] = 0
        
        # 5. Verificar palabras prohibidas
        words = clean_msg.split()
        for word in words:
            if word in self.banned_words:
                return True, f"PALABRA_PROHIBIDA: {word}"
        
        # Actualizar registros
        self.user_messages[user_id].append(current_time)
        self.user_last_message[user_id] = clean_msg
        
        return False, None


# Instancia global
anti_spam = AntiSpam()