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
        self.app_token_expires_at = None
        
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
    
    def refresh_app_token(self) -> bool:
        """
        Refrescar App Access Token usando client_credentials
        Los App Access Token duran aproximadamente 60 días (86400 * 60 segundos)
        """
        try:
            response = requests.post(
                "https://id.twitch.tv/oauth2/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "client_credentials"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                new_token = data["access_token"]
                # App tokens expiran en ~60 días (pero Twitch no devuelve expires_in)
                expires_in = data.get("expires_in", 5184000)  # 60 días por defecto
                
                # Actualizar settings
                settings.update_app_token(new_token)
                
                self.app_token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                days = expires_in // 86400
                hours = (expires_in % 86400) // 3600
                
                if days > 0:
                    logger.info(f"✅ App Access Token refrescado. Expira en {days} días y {hours} horas")
                else:
                    logger.info(f"✅ App Access Token refrescado. Expira en {expires_in // 3600} horas")
                return True
            else:
                logger.error(f"Error refrescando App Access Token: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error refrescando App Access Token: {e}")
            return False
    
    def refresh_all_tokens(self):
        """Refrescar todos los tokens"""
        bot_ok = self.refresh_bot_token()
        broadcaster_ok = self.refresh_broadcaster_token()
        app_ok = self.refresh_app_token()
        
        if bot_ok and broadcaster_ok and app_ok:
            logger.info("✅ Todos los tokens refrescados correctamente")
        else:
            logger.warning("⚠️ Algunos tokens no pudieron refrescarse")
    
    def validate_token(self, token: str, token_type: str = "bot") -> tuple:
        """
        Validar si un token sigue siendo válido
        
        Args:
            token: El token a validar
            token_type: "bot", "broadcaster" o "app"
        
        Returns:
            (is_valid, expires_in_seconds)
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
                elif token_type == "broadcaster":
                    self.broadcaster_token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                elif token_type == "app":
                    # Los App Token no devuelven expires_in, asumir 60 días
                    expires_in = 5184000  # 60 días
                    self.app_token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                return True, expires_in
            else:
                return False, 0
        except Exception:
            return False, 0
    
    def get_token_status(self) -> dict:
        """Obtener estado detallado de todos los tokens"""
        status = {
            "bot": {"valid": False, "expires_at": None, "expires_in": None},
            "broadcaster": {"valid": False, "expires_at": None, "expires_in": None},
            "app": {"valid": False, "expires_at": None, "expires_in": None}
        }
        
        # Validar bot token
        bot_valid, bot_expires = self.validate_token(settings.BOT_TOKEN, "bot")
        status["bot"]["valid"] = bot_valid
        if self.bot_token_expires_at:
            status["bot"]["expires_at"] = self.bot_token_expires_at
            status["bot"]["expires_in"] = (self.bot_token_expires_at - datetime.now()).total_seconds()
        
        # Validar broadcaster token
        broadcaster_valid, broadcaster_expires = self.validate_token(settings.BROADCASTER_TOKEN, "broadcaster")
        status["broadcaster"]["valid"] = broadcaster_valid
        if self.broadcaster_token_expires_at:
            status["broadcaster"]["expires_at"] = self.broadcaster_token_expires_at
            status["broadcaster"]["expires_in"] = (self.broadcaster_token_expires_at - datetime.now()).total_seconds()
        
        # Validar app token
        app_token = getattr(settings, 'APP_ACCESS_TOKEN', '')
        if app_token:
            app_valid, app_expires = self.validate_token(app_token, "app")
            status["app"]["valid"] = app_valid
            if self.app_token_expires_at:
                status["app"]["expires_at"] = self.app_token_expires_at
                status["app"]["expires_in"] = (self.app_token_expires_at - datetime.now()).total_seconds()
        
        return status
    
    def print_token_status(self):
        """Imprimir estado de los tokens en consola"""
        logger.info("=" * 50)
        logger.info("📊 ESTADO DE TOKENS")
        logger.info("=" * 50)
        
        status = self.get_token_status()
        
        # Bot Token
        if status["bot"]["valid"]:
            expires_in = status["bot"]["expires_in"]
            if expires_in:
                hours = expires_in // 3600
                minutes = (expires_in % 3600) // 60
                logger.info(f"🤖 Bot Token: ✅ Válido - Expira en {hours}h {minutes}m")
            else:
                logger.info(f"🤖 Bot Token: ✅ Válido")
        else:
            logger.info(f"🤖 Bot Token: ❌ Inválido")
        
        # Broadcaster Token
        if status["broadcaster"]["valid"]:
            expires_in = status["broadcaster"]["expires_in"]
            if expires_in:
                hours = expires_in // 3600
                minutes = (expires_in % 3600) // 60
                logger.info(f"📺 Streamer Token: ✅ Válido - Expira en {hours}h {minutes}m")
            else:
                logger.info(f"📺 Streamer Token: ✅ Válido")
        else:
            logger.info(f"📺 Streamer Token: ❌ Inválido")
        
        # App Token
        if status["app"]["valid"]:
            expires_in = status["app"]["expires_in"]
            if expires_in:
                days = expires_in // 86400
                hours = (expires_in % 86400) // 3600
                if days > 0:
                    logger.info(f"🔑 App Token: ✅ Válido - Expira en {days} días y {hours} horas")
                else:
                    logger.info(f"🔑 App Token: ✅ Válido - Expira en {hours} horas")
            else:
                logger.info(f"🔑 App Token: ✅ Válido")
        else:
            logger.info(f"🔑 App Token: ❌ Inválido")
        
        logger.info("=" * 50)
    
    def schedule_refresh(self, minutes_before: int = 5):
        """
        Programar refresh automático antes de que expiren los tokens
        
        Args:
            minutes_before: Minutos antes de expiración para refrescar
        """
        now = datetime.now()
        refresh_times = []
        
        # Bot token (4 horas)
        if self.bot_token_expires_at:
            time_to_bot = (self.bot_token_expires_at - now).total_seconds() - (minutes_before * 60)
            if time_to_bot > 0:
                refresh_times.append(time_to_bot)
        
        # Broadcaster token (4 horas)
        if self.broadcaster_token_expires_at:
            time_to_broadcaster = (self.broadcaster_token_expires_at - now).total_seconds() - (minutes_before * 60)
            if time_to_broadcaster > 0:
                refresh_times.append(time_to_broadcaster)
        
        # App token (60 días, refrescar cada 30 días para estar seguros)
        if self.app_token_expires_at:
            # Refrescar App Token cada 30 días (mitad de su vida útil)
            app_refresh_days = 30
            time_to_app = (self.app_token_expires_at - now).total_seconds() - (app_refresh_days * 24 * 3600)
            if time_to_app > 0:
                refresh_times.append(min(time_to_app, 30 * 24 * 3600))  # Máximo 30 días
            elif self.app_token_expires_at > now:
                # Si falta menos de 30 días, refrescar cuando falten 5 minutos
                time_to_app = (self.app_token_expires_at - now).total_seconds() - (minutes_before * 60)
                if time_to_app > 0:
                    refresh_times.append(time_to_app)
        
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
        bot_valid, _ = self.validate_token(settings.BOT_TOKEN, "bot")
        broadcaster_valid, _ = self.validate_token(settings.BROADCASTER_TOKEN, "broadcaster")
        
        app_token = getattr(settings, 'APP_ACCESS_TOKEN', '')
        app_valid, _ = self.validate_token(app_token, "app") if app_token else (False, 0)
        
        if not bot_valid:
            logger.warning("Token del bot inválido o expirado, refrescando...")
            self.refresh_bot_token()
        
        if not broadcaster_valid:
            logger.warning("Token del streamer inválido o expirado, refrescando...")
            self.refresh_broadcaster_token()
        
        if not app_valid and app_token:
            logger.warning("App Access Token inválido o expirado, refrescando...")
            self.refresh_app_token()
    
    def start_auto_refresh(self):
        """Iniciar el sistema de auto-refresh"""
        logger.info("🔄 Iniciando sistema de auto-refresh de tokens...")
        
        # Mostrar estado inicial de los tokens
        self.print_token_status()
        
        # Validar y refrescar si es necesario
        self.validate_current_tokens()
        
        # Mostrar estado después de refrescar
        self.print_token_status()
        
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