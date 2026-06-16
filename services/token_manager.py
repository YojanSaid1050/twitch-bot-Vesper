"""
Gestor de refresh de tokens de Twitch
"""

import requests
import threading
import time
from datetime import datetime, timedelta

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class TokenManager:
    """
    Gestiona el refresh automático de tokens de Twitch
    """
    
    def __init__(self):
        self.client_id = settings.CLIENT_ID
        self.client_secret = settings.CLIENT_SECRET
        
        # Estado de los tokens
        self.bot_token_expires_at = None
        self.broadcaster_token_expires_at = None
        
        # Timer para refresh automático
        self._refresh_timer = None
    
    def refresh_bot_token(self) -> bool:
        """Refrescar token del bot usando refresh_token"""
        if not settings.BOT_REFRESH_TOKEN:
            logger.error("No hay BOT_REFRESH_TOKEN configurado")
            return False
        
        try:
            response = requests.post(
                "https://id.twitch.tv/oauth2/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": settings.BOT_REFRESH_TOKEN
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                new_token = data["access_token"]
                new_refresh_token = data.get("refresh_token", settings.BOT_REFRESH_TOKEN)
                expires_in = data.get("expires_in", 14400)
                
                # Actualizar settings
                settings.update_bot_token(new_token)
                
                # Actualizar refresh token si cambió
                if new_refresh_token != settings.BOT_REFRESH_TOKEN:
                    settings._save_to_env("BOT_REFRESH_TOKEN", new_refresh_token)
                    settings.BOT_REFRESH_TOKEN = new_refresh_token
                
                self.bot_token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                logger.info(f"✅ Token del bot refrescado. Expira en {expires_in // 60} minutos")
                return True
            else:
                logger.error(f"Error refrescando token del bot: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error refrescando token del bot: {e}")
            return False
    
    def refresh_broadcaster_token(self) -> bool:
        """Refrescar token del streamer usando refresh_token"""
        if not settings.BROADCASTER_REFRESH_TOKEN:
            logger.error("No hay BROADCASTER_REFRESH_TOKEN configurado")
            return False
        
        try:
            response = requests.post(
                "https://id.twitch.tv/oauth2/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": settings.BROADCASTER_REFRESH_TOKEN
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                new_token = data["access_token"]
                new_refresh_token = data.get("refresh_token", settings.BROADCASTER_REFRESH_TOKEN)
                expires_in = data.get("expires_in", 14400)
                
                # Actualizar settings
                settings.update_broadcaster_token(new_token)
                
                # Actualizar refresh token si cambió
                if new_refresh_token != settings.BROADCASTER_REFRESH_TOKEN:
                    settings._save_to_env("BROADCASTER_REFRESH_TOKEN", new_refresh_token)
                    settings.BROADCASTER_REFRESH_TOKEN = new_refresh_token
                
                self.broadcaster_token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                logger.info(f"✅ Token del streamer refrescado. Expira en {expires_in // 60} minutos")
                return True
            else:
                logger.error(f"Error refrescando token del streamer: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error refrescando token del streamer: {e}")
            return False
    
    def refresh_all_tokens(self):
        """Refrescar ambos tokens"""
        bot_ok = self.refresh_bot_token()
        broadcaster_ok = self.refresh_broadcaster_token()
        
        if bot_ok and broadcaster_ok:
            logger.info("✅ Todos los tokens refrescados correctamente")
        else:
            logger.warning("⚠️ Algunos tokens no pudieron refrescarse")
    
    def validate_token(self, token: str, token_type: str = "bot") -> bool:
        """
        Validar si un token sigue siendo válido
        
        Args:
            token: El token a validar
            token_type: "bot" o "broadcaster"
        
        Returns:
            True si es válido, False si expiró
        """
        try:
            response = requests.get(
                "https://id.twitch.tv/oauth2/validate",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                expires_in = data.get("expires_in", 0)
                
                # Actualizar tiempo de expiración
                if token_type == "bot":
                    self.bot_token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                else:
                    self.broadcaster_token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                return True
            else:
                return False
        except Exception:
            return False
    
    def schedule_refresh(self, minutes_before: int = 5):
        """
        Programar refresh automático antes de que expiren los tokens
        
        Args:
            minutes_before: Minutos antes de expiración para refrescar
        """
        # Calcular tiempo hasta la próxima expiración
        now = datetime.now()
        refresh_times = []
        
        if self.bot_token_expires_at:
            time_to_bot = (self.bot_token_expires_at - now).total_seconds() - (minutes_before * 60)
            if time_to_bot > 0:
                refresh_times.append(time_to_bot)
        
        if self.broadcaster_token_expires_at:
            time_to_broadcaster = (self.broadcaster_token_expires_at - now).total_seconds() - (minutes_before * 60)
            if time_to_broadcaster > 0:
                refresh_times.append(time_to_broadcaster)
        
        if not refresh_times:
            # Si no hay tiempos, refrescar en 3 horas
            next_refresh = 3 * 60 * 60
        else:
            next_refresh = min(refresh_times)
        
        # Asegurar un mínimo de 5 minutos
        next_refresh = max(next_refresh, 5 * 60)
        
        logger.info(f"⏰ Refresh programado en {next_refresh // 60} minutos")
        
        # Cancelar timer anterior si existe
        if self._refresh_timer:
            self._refresh_timer.cancel()
        
        # Programar nuevo refresh
        self._refresh_timer = threading.Timer(next_refresh, self._do_scheduled_refresh)
        self._refresh_timer.daemon = True
        self._refresh_timer.start()
    
    def _do_scheduled_refresh(self):
        """Ejecutar refresh programado"""
        logger.info("🔄 Ejecutando refresh programado de tokens...")
        self.refresh_all_tokens()
        self.validate_current_tokens()
        self.schedule_refresh()  # Reprogramar
    
    def validate_current_tokens(self):
        """Validar tokens actuales y actualizar tiempos de expiración"""
        bot_valid = self.validate_token(settings.BOT_TOKEN, "bot")
        broadcaster_valid = self.validate_token(settings.BROADCASTER_TOKEN, "broadcaster")
        
        if not bot_valid:
            logger.warning("Token del bot inválido o expirado, refrescando...")
            self.refresh_bot_token()
        
        if not broadcaster_valid:
            logger.warning("Token del streamer inválido o expirado, refrescando...")
            self.refresh_broadcaster_token()
    
    def start_auto_refresh(self):
        """Iniciar el sistema de auto-refresh"""
        logger.info("🔄 Iniciando sistema de auto-refresh de tokens...")
        
        # Validar tokens actuales
        self.validate_current_tokens()
        
        # Programar refresh
        self.schedule_refresh()
    
    def stop_auto_refresh(self):
        """Detener el sistema de auto-refresh"""
        if self._refresh_timer:
            self._refresh_timer.cancel()
            self._refresh_timer = None
        logger.info("🛑 Sistema de auto-refresh detenido")


# Instancia global
token_manager = TokenManager()