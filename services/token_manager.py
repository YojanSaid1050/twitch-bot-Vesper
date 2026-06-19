"""
Gestor de refresh de tokens de Twitch y Spotify (refactorizado con PostgreSQL)
"""

import threading
import time
from typing import Optional, Dict
from enum import Enum

from config import settings
from services.oauth_manager import OAuthManager, TokenType, OAuthError
from services.token_validator import TokenValidator
from services.log_service import log_service
from utils.logger import get_logger

logger = get_logger(__name__)


class TokenState:
    """Estado de un token individual."""
    def __init__(self, token_type: TokenType, refresh_token: str, access_token: str = None):
        self.token_type = token_type
        self.refresh_token = refresh_token
        self.access_token = access_token
        self.expires_at: Optional[float] = None  # timestamp
        self.lock = threading.Lock()
        self.valid = False

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return True
        return time.time() >= self.expires_at - 60  # margen 1 minuto

    def update(self, access_token: str, expires_in: int, new_refresh_token: Optional[str] = None):
        self.access_token = access_token
        self.expires_at = time.time() + expires_in
        self.valid = True
        if new_refresh_token:
            self.refresh_token = new_refresh_token


class TokenManager:
    """Orquestador principal de tokens con persistencia PostgreSQL."""

    def __init__(self):
        self.client_id = settings.CLIENT_ID
        self.client_secret = settings.CLIENT_SECRET

        # Estados de tokens (cada uno con su lock)
        self.states = {
            TokenType.BOT: TokenState(
                TokenType.BOT,
                settings.BOT_REFRESH_TOKEN,
                settings.BOT_TOKEN
            ),
            TokenType.BROADCASTER: TokenState(
                TokenType.BROADCASTER,
                settings.BROADCASTER_REFRESH_TOKEN,
                settings.BROADCASTER_TOKEN
            ),
            TokenType.APP: TokenState(
                TokenType.APP,
                None,  # App token no tiene refresh
                settings.APP_ACCESS_TOKEN
            ),
            TokenType.SPOTIFY: TokenState(
                TokenType.SPOTIFY,
                settings.SPOTIFY_REFRESH_TOKEN,
                None  # lo obtenemos cuando se necesite
            )
        }

        self._refresh_timer: Optional[threading.Timer] = None
        self._shutdown_event = threading.Event()

    # ============================================
    # Métodos públicos (compatibilidad)
    # ============================================

    def refresh_bot_token(self) -> bool:
        return self._refresh_token(TokenType.BOT)

    def refresh_broadcaster_token(self) -> bool:
        return self._refresh_token(TokenType.BROADCASTER)

    def refresh_app_token(self) -> bool:
        return self._refresh_token(TokenType.APP)

    def refresh_spotify_token(self) -> bool:
        return self._refresh_token(TokenType.SPOTIFY)

    def refresh_all_tokens(self):
        """Refresca todos los tokens (para uso en arranque)."""
        results = {
            TokenType.BOT: self.refresh_bot_token(),
            TokenType.BROADCASTER: self.refresh_broadcaster_token(),
            TokenType.APP: self.refresh_app_token(),
            TokenType.SPOTIFY: self.refresh_spotify_token(),
        }
        logger.info(f"Refresh all results: {results}")

    def get_spotify_token(self) -> Optional[str]:
        """Devuelve el access token de Spotify, refrescando si es necesario."""
        state = self.states[TokenType.SPOTIFY]
        with state.lock:
            if not state.valid or state.is_expired():
                if not self._refresh_token(TokenType.SPOTIFY):
                    return None
            return state.access_token

    def are_tokens_valid(self) -> bool:
        """Verifica si los tokens esenciales (bot y broadcaster) son válidos."""
        bot_valid = self._is_token_valid(TokenType.BOT)
        broadcaster_valid = self._is_token_valid(TokenType.BROADCASTER)
        return bot_valid and broadcaster_valid

    def get_token_status(self) -> dict:
        """Devuelve estado detallado (para dashboard)."""
        status = {}
        for token_type, state in self.states.items():
            if token_type == TokenType.SPOTIFY:
                # Spotify: usar estado interno, no validar con Twitch
                valid = state.valid
                if state.expires_at:
                    expires_in = max(0, state.expires_at - time.time())
                else:
                    expires_in = None
            else:
                # Twitch: validar con caché
                valid, expires_in = TokenValidator.validate(state.access_token or "")
            status[token_type.value] = {
                "valid": valid,
                "expires_at": state.expires_at,
                "expires_in": expires_in,
            }
        return status

    def print_token_status(self):
        """Imprime en consola (igual que antes)."""
        logger.info("=" * 50)
        logger.info("📊 ESTADO DE TOKENS")
        logger.info("=" * 50)
        status = self.get_token_status()
        for token_type, info in status.items():
            valid = info["valid"]
            expires_in = info.get("expires_in")
            if valid:
                if expires_in and expires_in > 0:
                    hours = expires_in // 3600
                    minutes = (expires_in % 3600) // 60
                    logger.info(f"{token_type.upper()}: ✅ Válido - Expira en {int(hours)}h {int(minutes)}m")
                else:
                    logger.info(f"{token_type.upper()}: ✅ Válido")
            else:
                logger.info(f"{token_type.upper()}: ❌ Inválido")
                log_service.add_log('error', f'Token {token_type} inválido', 'token_manager')
        logger.info("=" * 50)

    def start_auto_refresh(self, wait_for_tokens: bool = True):
        """Inicia el sistema de auto-refresh (compatible con la interfaz actual)."""
        logger.info("🔄 Iniciando sistema de auto-refresh de tokens...")
        log_service.add_log('info', 'Iniciando sistema de auto-refresh de tokens', 'token_manager')

        # Intentar refrescar todos al arranque
        self.refresh_all_tokens()

        # Si se pide esperar, bloquear hasta que los tokens esenciales sean válidos
        if wait_for_tokens:
            self.wait_for_valid_tokens(timeout=60)

        self.print_token_status()
        self._schedule_next_refresh()

    def wait_for_valid_tokens(self, timeout: int = 60):
        """Espera hasta que los tokens esenciales sean válidos."""
        logger.info(f"⏳ Esperando hasta {timeout}s para que los tokens sean válidos...")
        log_service.add_log('info', f'Esperando tokens válidos (timeout {timeout}s)', 'token_manager')
        start = time.time()
        while time.time() - start < timeout:
            if self.are_tokens_valid():
                logger.info("✅ Todos los tokens esenciales son válidos.")
                log_service.add_log('info', 'Todos los tokens esenciales son válidos', 'token_manager')
                return
            # Intentar refrescar si alguno está inválido
            for token_type in (TokenType.BOT, TokenType.BROADCASTER):
                state = self.states[token_type]
                with state.lock:
                    if not state.valid or state.is_expired():
                        self._refresh_token(token_type)
            time.sleep(2)
        logger.warning(f"⚠️ Timeout esperando tokens válidos después de {timeout}s. Continuando de todos modos.")
        log_service.add_log('warning', f'Timeout esperando tokens válidos ({timeout}s)', 'token_manager')

    def stop_auto_refresh(self):
        """Detiene el scheduler."""
        self._shutdown_event.set()
        if self._refresh_timer:
            self._refresh_timer.cancel()
            self._refresh_timer = None
        logger.info("🛑 Sistema de auto-refresh detenido")
        log_service.add_log('info', 'Sistema de auto-refresh detenido', 'token_manager')

    def force_refresh_broadcaster_if_needed(self) -> bool:
        """Forzar refresh del broadcaster si es necesario (usado por dashboard)."""
        if not self._is_token_valid(TokenType.BROADCASTER):
            return self.refresh_broadcaster_token()
        return True

    # ============================================
    # Métodos internos
    # ============================================

    def _refresh_token(self, token_type: TokenType) -> bool:
        """Refresca un token específico, usando su propio lock."""
        state = self.states[token_type]

        # Si es App Token, no tiene refresh; lo obtenemos con client_credentials
        if token_type == TokenType.APP:
            return self._refresh_app_token_internal(state)

        # Si es Spotify, usamos el método específico
        if token_type == TokenType.SPOTIFY:
            return self._refresh_spotify_token_internal(state)

        # Twitch: bot o broadcaster
        with state.lock:
            # Si ya es válido y no expirará pronto, no hacer nada
            if state.valid and not state.is_expired():
                return True

            try:
                token_data = OAuthManager.refresh_twitch_token(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    refresh_token=state.refresh_token,
                    token_type=token_type
                )
                # Actualizar estado
                new_access = token_data["access_token"]
                expires_in = token_data.get("expires_in", 14400)
                new_refresh = token_data.get("refresh_token")  # Puede no venir
                state.update(new_access, expires_in, new_refresh)

                # Guardar refresh token en PostgreSQL si cambió
                if new_refresh and new_refresh != state.refresh_token:
                    if token_type == TokenType.BOT:
                        settings.update_bot_refresh_token(new_refresh)
                    elif token_type == TokenType.BROADCASTER:
                        settings.update_broadcaster_refresh_token(new_refresh)
                    state.refresh_token = new_refresh

                # Guardar access token en PostgreSQL (con expiración)
                self._update_settings_token(token_type, new_access, expires_in)

                # Invalidar caché de validación para este token (opcional)
                TokenValidator.invalidate(new_access)

                logger.info(f"✅ Token {token_type.value} refrescado. Expira en {expires_in//60} minutos.")
                log_service.add_log('info', f'Token {token_type.value} refrescado', 'token_manager')
                return True

            except OAuthError as e:
                error_msg = str(e)
                logger.error(f"❌ Error refrescando {token_type.value}: {error_msg}")
                if "refresh token inválido" in error_msg.lower() or "invalid refresh token" in error_msg.lower():
                    log_service.add_log('critical', f'REFRESH TOKEN EXPIRADO PARA {token_type.value}. NECESITAS REAUTORIZAR.', 'token_manager')
                else:
                    log_service.add_log('error', f'Error refrescando {token_type.value}: {error_msg}', 'twitch_api')
                return False

    def _refresh_app_token_internal(self, state: TokenState) -> bool:
        """Obtiene nuevo App Access Token."""
        with state.lock:
            try:
                token_data = OAuthManager.get_app_token(
                    client_id=self.client_id,
                    client_secret=self.client_secret
                )
                new_access = token_data["access_token"]
                expires_in = token_data.get("expires_in", 5184000)
                state.update(new_access, expires_in, None)
                self._update_settings_token(TokenType.APP, new_access, expires_in)
                logger.info("✅ App Token refrescado.")
                log_service.add_log('info', 'App Token refrescado', 'token_manager')
                return True
            except OAuthError as e:
                logger.error(f"❌ Error refrescando App Token: {e}")
                log_service.add_log('error', f'Error refrescando App Token: {e}', 'twitch_api')
                return False

    def _refresh_spotify_token_internal(self, state: TokenState) -> bool:
        """Refresca token de Spotify y lo guarda en PostgreSQL."""
        with state.lock:
            try:
                token_data = OAuthManager.refresh_spotify_token(
                    client_id=settings.SPOTIFY_CLIENT_ID,
                    client_secret=settings.SPOTIFY_CLIENT_SECRET,
                    refresh_token=state.refresh_token
                )
                new_access = token_data["access_token"]
                expires_in = token_data.get("expires_in", 3600)
                new_refresh = token_data.get("refresh_token")  # Puede cambiar
                state.update(new_access, expires_in, new_refresh)

                # Guardar refresh token en PostgreSQL si cambió
                if new_refresh and new_refresh != state.refresh_token:
                    settings.update_spotify_refresh_token(new_refresh)
                    state.refresh_token = new_refresh

                # Guardar access token (aunque settings no lo expone, lo guardamos en la base de datos)
                from database.token_repository import TokenRepository
                TokenRepository.update_access_token("spotify", "default", new_access, expires_in)

                logger.info(f"✅ Spotify Token refrescado. Expira en {expires_in//60} minutos.")
                log_service.add_log('info', f'Spotify Token refrescado (expira en {expires_in//60}m)', 'token_manager')
                return True
            except OAuthError as e:
                logger.error(f"❌ Error refrescando Spotify: {e}")
                log_service.add_log('error', f'Error refrescando Spotify: {e}', 'twitch_api')
                return False

    def _is_token_valid(self, token_type: TokenType) -> bool:
        """Valida usando TokenValidator con caché."""
        state = self.states[token_type]
        if not state.access_token:
            return False
        valid, _ = TokenValidator.validate(state.access_token)
        return valid

    def _update_settings_token(self, token_type: TokenType, new_token: str, expires_in: int):
        """
        Actualiza el objeto settings y la base de datos.
        """
        if token_type == TokenType.BOT:
            settings.update_bot_token(new_token, expires_in)
        elif token_type == TokenType.BROADCASTER:
            settings.update_broadcaster_token(new_token, expires_in)
        elif token_type == TokenType.APP:
            settings.update_app_token(new_token, expires_in)

    # ============================================
    # Scheduler inteligente
    # ============================================

    def _schedule_next_refresh(self):
        """Calcula el próximo token que expirará y programa su refresh."""
        if self._shutdown_event.is_set():
            return

        now = time.time()
        earliest = None
        earliest_type = None

        for token_type, state in self.states.items():
            if state.expires_at and state.valid:
                time_left = state.expires_at - now - 60  # margen 1 minuto
                if time_left > 0 and (earliest is None or time_left < earliest):
                    earliest = time_left
                    earliest_type = token_type

        if earliest_type is None:
            # Si no hay tokens con expiración, programar un refresh general en 5 minutos
            delay = 5 * 60
            logger.info(f"⏰ No se detectaron expiraciones. Refresh general en {delay//60} minutos.")
            log_service.add_log('info', f'No se detectaron expiraciones, refresh general en {delay//60}m', 'token_manager')
        else:
            # Programar solo ese token
            delay = max(earliest, 60)  # mínimo 60 segundos
            logger.info(f"⏰ Próximo refresh para {earliest_type.value} en {delay//60} minutos.")
            log_service.add_log('info', f'Próximo refresh para {earliest_type.value} en {delay//60}m', 'token_manager')

        if self._refresh_timer:
            self._refresh_timer.cancel()

        self._refresh_timer = threading.Timer(delay, self._do_scheduled_refresh)
        self._refresh_timer.daemon = True
        self._refresh_timer.start()

    def _do_scheduled_refresh(self):
        """Ejecuta el refresh del token que expirará primero."""
        if self._shutdown_event.is_set():
            return

        logger.info("🔄 Ejecutando refresh programado...")
        log_service.add_log('info', 'Refresh programado iniciado', 'token_manager')

        # Determinar qué token refrescar: el que expira más pronto
        now = time.time()
        earliest = None
        earliest_type = None

        for token_type, state in self.states.items():
            if state.expires_at and state.valid:
                time_left = state.expires_at - now
                if time_left < 300:  # menos de 5 minutos
                    if earliest is None or time_left < earliest:
                        earliest = time_left
                        earliest_type = token_type

        if earliest_type:
            logger.info(f"Refrescando {earliest_type.value} (expira en {int(earliest)}s)")
            self._refresh_token(earliest_type)
        else:
            # Si no hay ninguno cercano, refrescar todos (por si acaso)
            logger.info("Refrescando todos los tokens (por precaución)")
            self.refresh_all_tokens()

        # Reprogramar
        self._schedule_next_refresh()


# ============================================
# INSTANCIA GLOBAL (NECESARIA PARA IMPORTACIÓN)
# ============================================
token_manager = TokenManager()