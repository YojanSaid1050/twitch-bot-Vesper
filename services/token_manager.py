"""
Gestor de refresh de tokens de Twitch y Spotify
"""

import requests
import threading
import time
from datetime import datetime, timedelta
import os

from config import settings
from utils.logger import get_logger
from services.log_service import log_service

logger = get_logger(__name__)


class TokenManager:
    """
    Gestiona el refresh automático de tokens de Twitch y Spotify
    """
    
    def __init__(self):
        self.client_id = settings.CLIENT_ID
        self.client_secret = settings.CLIENT_SECRET
        
        # Estado de los tokens de Twitch
        self.bot_token_expires_at = None
        self.broadcaster_token_expires_at = None
        self.app_token_expires_at = None
        
        # Estado del token de Spotify
        self.spotify_token_expires_at = None
        self.spotify_access_token = None
        self.spotify_refresh_token = os.getenv('SPOTIFY_REFRESH_TOKEN', '')
        
        # Timer para refresh automático
        self._refresh_timer = None
        
        # Cooldown para evitar refrescos en bucle
        self._last_refresh_attempt = 0
        self._refresh_cooldown = 180  # 3 minutos
        
        # Evento para indicar que los tokens están listos
        self._tokens_ready = threading.Event()
    
    def _can_refresh(self) -> bool:
        """Verificar si se puede intentar un refresh (evitar bucles)"""
        now = time.time()
        if now - self._last_refresh_attempt < self._refresh_cooldown:
            logger.debug(f"⏳ Cooldown de refresh activo ({self._refresh_cooldown}s)")
            return False
        self._last_refresh_attempt = now
        return True
    
    def _is_token_valid(self, token: str) -> bool:
        """Verificar si un token de Twitch es válido"""
        try:
            response = requests.get(
                "https://id.twitch.tv/oauth2/validate",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False
    
    # ============================================
    # REFRESH DE TOKENS DE TWITCH
    # ============================================
    
    def refresh_bot_token(self) -> bool:
        """Refrescar token del bot usando refresh_token"""
        if not self._can_refresh():
            return False
        
        if not settings.BOT_REFRESH_TOKEN:
            logger.error("No hay BOT_REFRESH_TOKEN configurado")
            log_service.add_log('error', 'No hay BOT_REFRESH_TOKEN configurado', 'token_manager')
            return False
        
        try:
            response = requests.post(
                "https://id.twitch.tv/oauth2/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": settings.BOT_REFRESH_TOKEN
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                new_token = data["access_token"]
                new_refresh_token = data.get("refresh_token", settings.BOT_REFRESH_TOKEN)
                expires_in = data.get("expires_in", 14400)
                
                settings.update_bot_token(new_token)
                
                if new_refresh_token != settings.BOT_REFRESH_TOKEN:
                    settings._save_to_env("BOT_REFRESH_TOKEN", new_refresh_token)
                    settings.BOT_REFRESH_TOKEN = new_refresh_token
                
                self.bot_token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                logger.info(f"✅ Token del bot refrescado. Expira en {expires_in // 60} minutos")
                log_service.add_log('info', f'Token del bot refrescado. Expira en {expires_in // 60} min', 'token_manager')
                return True
            else:
                logger.error(f"Error refrescando token del bot: {response.status_code} - {response.text}")
                log_service.add_log('error', f'Error refrescando token del bot: {response.status_code}', 'token_manager')
                return False
                
        except Exception as e:
            logger.error(f"Error refrescando token del bot: {e}")
            log_service.add_log('error', f'Error refrescando token del bot: {e}', 'token_manager')
            return False
    
    def refresh_broadcaster_token(self) -> bool:
        """Refrescar token del streamer usando refresh_token"""
        if not self._can_refresh():
            return False
        
        if not settings.BROADCASTER_REFRESH_TOKEN:
            logger.error("No hay BROADCASTER_REFRESH_TOKEN configurado")
            log_service.add_log('error', 'No hay BROADCASTER_REFRESH_TOKEN configurado', 'token_manager')
            return False
        
        try:
            response = requests.post(
                "https://id.twitch.tv/oauth2/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": settings.BROADCASTER_REFRESH_TOKEN
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                new_token = data["access_token"]
                new_refresh_token = data.get("refresh_token", settings.BROADCASTER_REFRESH_TOKEN)
                expires_in = data.get("expires_in", 14400)
                
                settings.update_broadcaster_token(new_token)
                
                if new_refresh_token != settings.BROADCASTER_REFRESH_TOKEN:
                    settings._save_to_env("BROADCASTER_REFRESH_TOKEN", new_refresh_token)
                    settings.BROADCASTER_REFRESH_TOKEN = new_refresh_token
                
                self.broadcaster_token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                logger.info(f"✅ Token del streamer refrescado. Expira en {expires_in // 60} minutos")
                log_service.add_log('info', f'Token del streamer refrescado. Expira en {expires_in // 60} min', 'token_manager')
                return True
            else:
                logger.error(f"Error refrescando token del streamer: {response.status_code} - {response.text}")
                log_service.add_log('error', f'Error refrescando token del streamer: {response.status_code}', 'token_manager')
                return False
                
        except Exception as e:
            logger.error(f"Error refrescando token del streamer: {e}")
            log_service.add_log('error', f'Error refrescando token del streamer: {e}', 'token_manager')
            return False
    
    def refresh_app_token(self) -> bool:
        """Refrescar App Access Token usando client_credentials"""
        if not self._can_refresh():
            return False
        
        try:
            response = requests.post(
                "https://id.twitch.tv/oauth2/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "client_credentials"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                new_token = data["access_token"]
                expires_in = data.get("expires_in", 5184000)
                
                settings.update_app_token(new_token)
                self.app_token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                logger.info("✅ App Access Token refrescado")
                log_service.add_log('info', 'App Access Token refrescado', 'token_manager')
                return True
            else:
                logger.error(f"Error refrescando App Access Token: {response.status_code}")
                log_service.add_log('error', f'Error refrescando App Access Token: {response.status_code}', 'token_manager')
                return False
                
        except Exception as e:
            logger.error(f"Error refrescando App Access Token: {e}")
            log_service.add_log('error', f'Error refrescando App Access Token: {e}', 'token_manager')
            return False
    
    # ============================================
    # REFRESH DE TOKEN DE SPOTIFY
    # ============================================
    
    def refresh_spotify_token(self) -> bool:
        """
        Refrescar token de Spotify usando refresh_token desde variables de entorno.
        Devuelve True si se obtuvo un nuevo access token.
        """
        if not self._can_refresh():
            return False
        
        if not self.spotify_refresh_token:
            logger.warning("No hay SPOTIFY_REFRESH_TOKEN configurado")
            log_service.add_log('warning', 'No hay SPOTIFY_REFRESH_TOKEN configurado', 'token_manager')
            return False
        
        try:
            # Usar el endpoint de Spotify para refrescar el token
            response = requests.post(
                "https://accounts.spotify.com/api/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.spotify_refresh_token,
                    "client_id": settings.SPOTIFY_CLIENT_ID,
                    "client_secret": settings.SPOTIFY_CLIENT_SECRET,
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.spotify_access_token = data.get("access_token")
                expires_in = data.get("expires_in", 3600)
                
                # Si devuelve un nuevo refresh token (raro), actualizarlo
                if "refresh_token" in data:
                    self.spotify_refresh_token = data["refresh_token"]
                    # No podemos actualizar variables de entorno, pero lo guardamos en memoria
                
                self.spotify_token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                logger.info(f"✅ Token de Spotify refrescado. Expira en {expires_in // 60} minutos")
                log_service.add_log('info', f'Token de Spotify refrescado. Expira en {expires_in // 60} min', 'token_manager')
                return True
            else:
                logger.error(f"Error refrescando token de Spotify: {response.status_code} - {response.text}")
                log_service.add_log('error', f'Error refrescando token de Spotify: {response.status_code}', 'token_manager')
                return False
                
        except Exception as e:
            logger.error(f"Error refrescando token de Spotify: {e}")
            log_service.add_log('error', f'Error refrescando token de Spotify: {e}', 'token_manager')
            return False
    
    def get_spotify_token(self) -> str:
        """
        Obtener el access token de Spotify. Si no existe o está expirado, lo refresca.
        Devuelve el access token o None si falla.
        """
        # Si no hay token o está expirado, refrescar
        if not self.spotify_access_token or not self.spotify_token_expires_at or datetime.now() >= self.spotify_token_expires_at:
            if not self.refresh_spotify_token():
                return None
        return self.spotify_access_token
    
    # ============================================
    # FUNCIONES DE ESTADO Y VALIDACIÓN
    # ============================================
    
    def validate_token(self, token: str, token_type: str = "bot") -> tuple:
        """Validar si un token de Twitch sigue siendo válido"""
        try:
            response = requests.get(
                "https://id.twitch.tv/oauth2/validate",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                expires_in = data.get("expires_in", 0)
                
                if token_type == "bot":
                    self.bot_token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                elif token_type == "broadcaster":
                    self.broadcaster_token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                elif token_type == "app":
                    expires_in = 5184000
                    self.app_token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                return True, expires_in
            else:
                return False, 0
        except Exception:
            return False, 0
    
    def are_tokens_valid(self) -> bool:
        """Verificar si los tokens esenciales (bot y broadcaster) son válidos"""
        bot_valid = self._is_token_valid(settings.BOT_TOKEN)
        broadcaster_valid = self._is_token_valid(settings.BROADCASTER_TOKEN)
        return bot_valid and broadcaster_valid
    
    def get_token_status(self) -> dict:
        """Obtener estado detallado de todos los tokens (incluido Spotify)"""
        status = {
            "bot": {"valid": False, "expires_at": None, "expires_in": None},
            "broadcaster": {"valid": False, "expires_at": None, "expires_in": None},
            "app": {"valid": False, "expires_at": None, "expires_in": None},
            "spotify": {"valid": False, "expires_at": None, "expires_in": None}
        }
        
        # Twitch: Bot
        bot_valid, bot_expires = self.validate_token(settings.BOT_TOKEN, "bot")
        status["bot"]["valid"] = bot_valid
        if self.bot_token_expires_at:
            status["bot"]["expires_at"] = self.bot_token_expires_at
            status["bot"]["expires_in"] = (self.bot_token_expires_at - datetime.now()).total_seconds()
        
        # Twitch: Broadcaster
        broadcaster_valid, broadcaster_expires = self.validate_token(settings.BROADCASTER_TOKEN, "broadcaster")
        status["broadcaster"]["valid"] = broadcaster_valid
        if self.broadcaster_token_expires_at:
            status["broadcaster"]["expires_at"] = self.broadcaster_token_expires_at
            status["broadcaster"]["expires_in"] = (self.broadcaster_token_expires_at - datetime.now()).total_seconds()
        
        # Twitch: App
        app_token = getattr(settings, 'APP_ACCESS_TOKEN', '')
        if app_token:
            app_valid, app_expires = self.validate_token(app_token, "app")
            status["app"]["valid"] = app_valid
            if self.app_token_expires_at:
                status["app"]["expires_at"] = self.app_token_expires_at
                status["app"]["expires_in"] = (self.app_token_expires_at - datetime.now()).total_seconds()
        
        # Spotify: si tenemos refresh token, intentar obtener estado
        if self.spotify_refresh_token:
            # Si tenemos access token en memoria y no ha expirado, considerarlo válido
            if self.spotify_access_token and self.spotify_token_expires_at and datetime.now() < self.spotify_token_expires_at:
                status["spotify"]["valid"] = True
                status["spotify"]["expires_at"] = self.spotify_token_expires_at
                status["spotify"]["expires_in"] = (self.spotify_token_expires_at - datetime.now()).total_seconds()
            else:
                # Intentar refrescar para obtener estado
                if self.refresh_spotify_token():
                    status["spotify"]["valid"] = True
                    status["spotify"]["expires_at"] = self.spotify_token_expires_at
                    status["spotify"]["expires_in"] = (self.spotify_token_expires_at - datetime.now()).total_seconds()
                else:
                    status["spotify"]["valid"] = False
        
        return status
    
    def print_token_status(self):
        """Imprimir estado de todos los tokens en consola (agrupado)"""
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
                logger.info(f"🤖 Bot Token: ✅ Válido - Expira en {int(hours)}h {int(minutes)}m")
            else:
                logger.info("🤖 Bot Token: ✅ Válido")
        else:
            logger.info("🤖 Bot Token: ❌ Inválido")
            log_service.add_log('error', 'Token del bot inválido', 'token_manager')
        
        # Streamer Token
        if status["broadcaster"]["valid"]:
            expires_in = status["broadcaster"]["expires_in"]
            if expires_in:
                hours = expires_in // 3600
                minutes = (expires_in % 3600) // 60
                logger.info(f"📺 Streamer Token: ✅ Válido - Expira en {int(hours)}h {int(minutes)}m")
            else:
                logger.info("📺 Streamer Token: ✅ Válido")
        else:
            logger.info("📺 Streamer Token: ❌ Inválido")
            log_service.add_log('error', 'Token del streamer inválido', 'token_manager')
        
        # App Token
        if status["app"]["valid"]:
            expires_in = status["app"]["expires_in"]
            if expires_in:
                days = expires_in // 86400
                hours = (expires_in % 86400) // 3600
                if days > 0:
                    logger.info(f"🔑 App Token: ✅ Válido - Expira en {int(days)} días y {int(hours)} horas")
                else:
                    logger.info(f"🔑 App Token: ✅ Válido - Expira en {int(hours)} horas")
            else:
                logger.info("🔑 App Token: ✅ Válido")
        else:
            logger.info("🔑 App Token: ❌ Inválido")
            log_service.add_log('error', 'App Token inválido', 'token_manager')
        
        # Spotify Token
        if status["spotify"]["valid"]:
            expires_in = status["spotify"]["expires_in"]
            if expires_in:
                hours = expires_in // 3600
                minutes = (expires_in % 3600) // 60
                logger.info(f"🎵 Spotify Token: ✅ Válido - Expira en {int(hours)}h {int(minutes)}m")
            else:
                logger.info("🎵 Spotify Token: ✅ Válido")
        else:
            if self.spotify_refresh_token:
                logger.info("🎵 Spotify Token: ❌ Inválido (falló refresh)")
                log_service.add_log('error', 'Token de Spotify inválido', 'token_manager')
            else:
                logger.info("🎵 Spotify Token: ⚠️ No configurado (falta SPOTIFY_REFRESH_TOKEN)")
                log_service.add_log('warning', 'SPOTIFY_REFRESH_TOKEN no configurado', 'token_manager')
        
        logger.info("=" * 50)
    
    # ============================================
    # PROGRAMACIÓN DE REFRESH
    # ============================================
    
    def schedule_refresh(self, minutes_before: int = 5):
        """
        Programar refresh automático con un límite máximo de 24 horas
        para evitar OverflowError en threading.Timer.
        """
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
        
        if self.app_token_expires_at:
            time_to_app = (self.app_token_expires_at - now).total_seconds() - (minutes_before * 60)
            if time_to_app > 0:
                refresh_times.append(time_to_app)
        
        # Spotify
        if self.spotify_token_expires_at:
            time_to_spotify = (self.spotify_token_expires_at - now).total_seconds() - (minutes_before * 60)
            if time_to_spotify > 0:
                refresh_times.append(time_to_spotify)
        
        # Si no hay tiempos programados, usar un valor por defecto (5 minutos)
        if not refresh_times:
            next_refresh = 5 * 60  # 5 minutos
        else:
            next_refresh = min(refresh_times)
            # Limitar a 24 horas máximo para evitar OverflowError
            max_interval = 24 * 60 * 60  # 24 horas
            if next_refresh > max_interval:
                next_refresh = max_interval
                logger.info(f"⏳ Intervalo de refresh limitado a 24 horas (era {min(refresh_times)//3600}h)")
        
        # Asegurar un mínimo de 60 segundos
        next_refresh = max(next_refresh, 60)
        
        logger.info(f"⏰ Refresh programado en {next_refresh // 60} minutos")
        
        if self._refresh_timer:
            self._refresh_timer.cancel()
        
        self._refresh_timer = threading.Timer(next_refresh, self._do_scheduled_refresh)
        self._refresh_timer.daemon = True
        self._refresh_timer.start()
    
    def _do_scheduled_refresh(self):
        """Ejecutar refresh programado de todos los tokens"""
        logger.info("🔄 Ejecutando refresh programado de tokens...")
        log_service.add_log('info', 'Ejecutando refresh programado de tokens', 'token_manager')
        self.refresh_all_tokens()
        self.schedule_refresh()
    
    # ============================================
    # REFRESH DE TODOS LOS TOKENS
    # ============================================
    
    def refresh_all_tokens(self):
        """Refrescar todos los tokens (Twitch + Spotify)"""
        bot_ok = self.refresh_bot_token()
        broadcaster_ok = self.refresh_broadcaster_token()
        app_ok = self.refresh_app_token()
        spotify_ok = self.refresh_spotify_token()
        
        if bot_ok and broadcaster_ok and app_ok and spotify_ok:
            logger.info("✅ Todos los tokens refrescados correctamente")
            log_service.add_log('info', 'Todos los tokens refrescados correctamente', 'token_manager')
            self._tokens_ready.set()
        else:
            logger.warning("⚠️ Algunos tokens no pudieron refrescarse")
            log_service.add_log('warning', 'Algunos tokens no pudieron refrescarse', 'token_manager')
            # Si al menos el bot y broadcaster son válidos, consideramos que estamos listos
            if self.are_tokens_valid():
                self._tokens_ready.set()
    
    def start_auto_refresh(self, wait_for_tokens: bool = True):
        """
        Iniciar el sistema de auto-refresh.
        Si wait_for_tokens es True, espera hasta que los tokens sean válidos.
        """
        logger.info("🔄 Iniciando sistema de auto-refresh de tokens...")
        
        # Primero, obtener token de Spotify si es posible
        if self.spotify_refresh_token and not self.spotify_access_token:
            self.refresh_spotify_token()
        
        # Verificar estado y refrescar si es necesario
        status = self.get_token_status()
        bot_valid = status["bot"]["valid"]
        broadcaster_valid = status["broadcaster"]["valid"]
        spotify_valid = status["spotify"]["valid"]
        
        if not bot_valid or not broadcaster_valid:
            logger.warning("⚠️ Tokens inválidos detectados. Intentando refrescar...")
            log_service.add_log('warning', 'Tokens inválidos detectados. Intentando refrescar...', 'token_manager')
            self.refresh_all_tokens()
            # Verificar de nuevo después del refresh
            status = self.get_token_status()
            if not status["bot"]["valid"] or not status["broadcaster"]["valid"]:
                logger.error("❌ No se pudieron refrescar los tokens. El bot puede fallar al conectar.")
                log_service.add_log('critical', 'No se pudieron refrescar los tokens del bot o streamer', 'token_manager')
        
        # Si se solicita esperar, bloquear hasta que los tokens sean válidos (o timeout)
        if wait_for_tokens:
            self.wait_for_valid_tokens(timeout=60)
        
        self.print_token_status()
        self.schedule_refresh()
    
    def wait_for_valid_tokens(self, timeout: int = 60):
        """
        Espera hasta que los tokens del bot y broadcaster sean válidos,
        o hasta que se alcance el timeout.
        """
        logger.info(f"⏳ Esperando hasta {timeout}s para que los tokens sean válidos...")
        start = time.time()
        while time.time() - start < timeout:
            if self.are_tokens_valid():
                logger.info("✅ Todos los tokens esenciales son válidos.")
                return
            # Intentar refrescar si ha pasado suficiente tiempo
            if self._can_refresh():
                logger.info("🔄 Intentando refrescar tokens durante la espera...")
                self.refresh_all_tokens()
            time.sleep(2)
        
        logger.warning(f"⚠️ Timeout esperando tokens válidos después de {timeout}s. Continuando de todos modos.")
    
    def stop_auto_refresh(self):
        """Detener el sistema de auto-refresh"""
        if self._refresh_timer:
            self._refresh_timer.cancel()
            self._refresh_timer = None
        logger.info("🛑 Sistema de auto-refresh detenido")
        log_service.add_log('info', 'Sistema de auto-refresh detenido', 'token_manager')
    
    def force_refresh_broadcaster_if_needed(self) -> bool:
        """Forzar refresco del token del broadcaster si es necesario (usado por el dashboard)"""
        if not self._is_token_valid(settings.BROADCASTER_TOKEN):
            logger.info("🔄 Forzando refresco del token del streamer desde el dashboard...")
            return self.refresh_broadcaster_token()
        return True


# Instancia global
token_manager = TokenManager()