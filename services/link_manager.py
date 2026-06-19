"""
Sistema de gestión de enlaces con integración API de Twitch
"""

import re
import time
import requests
from typing import Optional, Tuple, List, Dict, Any
from urllib.parse import urlparse
from datetime import datetime, timedelta

from config import settings
from services.config_service import config_service
from services.moderation_actions import ModerationActions
from services.warning_manager import warning_manager
from utils.logger import get_logger
from services.log_service import log_service

logger = get_logger(__name__)


class LinkManager:
    """
    Gestiona los enlaces en el chat con integración API de Twitch
    """
    
    def __init__(self):
        self.mod_actions = ModerationActions()
        self.link_warnings: Dict[str, int] = {}
        self.warning_users: Dict[str, str] = {}
        self.timeout_users: Dict[str, float] = {}
        self.timeout_user_names: Dict[str, str] = {}
        self.banned_users: Dict[str, Dict] = {}
        self.TIMEOUT_DURATION = 600  # 10 minutos
        self.BAN_DURATION = 1209600  # 14 días
        
        self._last_token_refresh = 0
        self._refresh_cooldown = 120
        
        self._banned_cache = []
        self._banned_cache_time = 0
        self._banned_cache_ttl = 60
        
        self._load_data()
    
    def _load_data(self):
        """Cargar datos de configuración (para dashboard)"""
        try:
            saved_data = config_service.get('link_management', {})
            self.link_warnings = saved_data.get('warnings', {})
            self.warning_users = saved_data.get('warning_users', {})
            self.banned_users = saved_data.get('banned', {})
            
            saved_timeouts = saved_data.get('timeouts', {})
            saved_timeout_names = saved_data.get('timeout_names', {})
            now = time.time()
            
            for user_id, end_time in list(saved_timeouts.items()):
                if end_time > now:
                    self.timeout_users[user_id] = end_time
                    if user_id in saved_timeout_names:
                        self.timeout_user_names[user_id] = saved_timeout_names[user_id]
                else:
                    if user_id in self.link_warnings:
                        del self.link_warnings[user_id]
                    if user_id in self.warning_users:
                        del self.warning_users[user_id]
            
            logger.info(f"📊 Datos de enlaces cargados: {len(self.link_warnings)} advertencias, {len(self.banned_users)} baneados, {len(self.timeout_users)} timeouts activos")
            log_service.add_log('info', f'Datos de enlaces cargados: {len(self.link_warnings)} advertencias', 'bot')
        except Exception as e:
            logger.error(f"Error cargando datos de enlaces: {e}")
            log_service.add_log('error', f'Error cargando datos de enlaces: {e}', 'bot')
            self.link_warnings = {}
            self.warning_users = {}
            self.banned_users = {}
            self.timeout_users = {}
            self.timeout_user_names = {}
    
    def _save_data(self):
        """Guardar datos en configuración (para dashboard)"""
        try:
            timeouts_to_save = {}
            timeout_names_to_save = {}
            now = time.time()
            for user_id, end_time in self.timeout_users.items():
                if end_time > now:
                    timeouts_to_save[user_id] = end_time
                    if user_id in self.timeout_user_names:
                        timeout_names_to_save[user_id] = self.timeout_user_names[user_id]
            
            config_service.set('link_management', {
                'warnings': self.link_warnings,
                'warning_users': self.warning_users,
                'banned': self.banned_users,
                'timeouts': timeouts_to_save,
                'timeout_names': timeout_names_to_save
            })
        except Exception as e:
            logger.error(f"Error guardando datos de enlaces: {e}")
            log_service.add_log('error', f'Error guardando datos de enlaces: {e}', 'bot')
    
    def _extract_links(self, message: str) -> List[str]:
        """Extraer todos los enlaces de un mensaje"""
        url_pattern = re.compile(
            r'https?://(?:www\.)?[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/\S*)?|'
            r'(?:www\.)[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/\S*)?|'
            r'(?:[a-zA-Z0-9-]+\.)+(?:com|net|org|es|io|gg|tv|ly|co|it|eu)(?:/\S*)?'
        )
        return url_pattern.findall(message)
    
    def is_link_allowed(self, link: str) -> bool:
        """
        Verificar si un enlace está permitido
        """
        try:
            parsed = urlparse(link)
            domain = parsed.netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]
            
            if not domain:
                match = re.search(r'(?:[a-zA-Z0-9-]+\.)+(?:com|net|org|es|io|gg|tv|ly|co|it|eu)', link)
                if match:
                    domain = match.group()
            
            # Spotify: PERMITIDO
            if 'spotify.com' in domain or 'open.spotify.com' in domain:
                return True
            
            # Clips de Twitch: PERMITIDO
            if 'clips.twitch.tv' in domain:
                return True
            
            # Verificar en la lista de permitidos del dashboard
            allowed_links = config_service.get_allowed_links()
            for allowed_domain in allowed_links:
                if allowed_domain in domain:
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Error verificando enlace {link}: {e}")
            log_service.add_log('error', f'Error verificando enlace {link}: {e}', 'twitch_api')
            return False
    
    async def check_message(self, user_id: str, user_name: str, message: str, is_staff: bool = False, is_vip: bool = False) -> Optional[Tuple[str, str, List[str]]]:
        """
        Verificar enlaces en el mensaje
        """
        if is_staff or is_vip:
            return None
        
        links = self._extract_links(message)
        if not links:
            return None
        
        blocked_links = []
        for link in links:
            if not self.is_link_allowed(link):
                blocked_links.append(link)
        
        if not blocked_links:
            return None
        
        action, count = warning_manager.check_and_get_action(user_id, 'link')
        
        self.warning_users[user_id] = user_name
        self.link_warnings[user_id] = count
        self._save_data()
        
        # Log de detección (moderación)
        log_service.add_log('info', f'Enlace bloqueado de {user_name} - Advertencia {count}/{warning_manager.get_max_warnings()}', 'moderation')
        
        if action == 'warning':
            return ('warning', f'Enlaces no permitidos - {len(blocked_links)} enlace(s) bloqueado(s)', blocked_links)
        elif action == 'timeout':
            self.timeout_users[user_id] = time.time() + self.TIMEOUT_DURATION
            self.timeout_user_names[user_id] = user_name
            self._save_data()
            log_service.add_log('warning', f'Timeout a {user_name} por enlaces prohibidos (advertencia {count})', 'moderation')
            return ('timeout', f'Enlaces no permitidos - {len(blocked_links)} enlace(s) bloqueado(s)', blocked_links)
        else:  # ban
            self.banned_users[user_id] = {
                'name': user_name,
                'reason': f'Enlaces no permitidos - {len(blocked_links)} enlace(s) bloqueado(s) - {count} advertencias',
                'banned_at': datetime.now().isoformat()
            }
            if user_id in self.link_warnings:
                del self.link_warnings[user_id]
            if user_id in self.warning_users:
                del self.warning_users[user_id]
            if user_id in self.timeout_users:
                del self.timeout_users[user_id]
            if user_id in self.timeout_user_names:
                del self.timeout_user_names[user_id]
            self._save_data()
            log_service.add_log('critical', f'Ban a {user_name} por enlaces prohibidos (advertencia {count})', 'moderation')
            return ('ban', f'Enlaces no permitidos - {len(blocked_links)} enlace(s) bloqueado(s)', blocked_links)
    
    # ============================================
    # FUNCIONES DE API DE TWITCH
    # ============================================
    
    def _get_token(self) -> str:
        token = settings.BOT_TOKEN
        if token.startswith("oauth:"):
            token = token[6:]
        return token
    
    def _get_broadcaster_token(self) -> str:
        token = settings.BROADCASTER_TOKEN
        if token.startswith("oauth:"):
            token = token[6:]
        return token
    
    def _refresh_token_if_needed(self, token_type: str = "broadcaster") -> bool:
        now = time.time()
        if now - self._last_token_refresh < self._refresh_cooldown:
            return False
        
        self._last_token_refresh = now
        
        try:
            from services.token_manager import token_manager
            if token_type == "broadcaster":
                return token_manager.refresh_broadcaster_token()
            else:
                return token_manager.refresh_bot_token()
        except Exception as e:
            logger.error(f"Error refrescando token: {e}")
            log_service.add_log('error', f'Error refrescando token en link_manager: {e}', 'token_manager')
            return False
    
    def _get_cached_banned_users(self) -> List[Dict]:
        now = time.time()
        if now - self._banned_cache_time < self._banned_cache_ttl:
            return self._banned_cache
        
        self._banned_cache = self._fetch_banned_users()
        self._banned_cache_time = now
        return self._banned_cache
    
    def _fetch_banned_users(self) -> List[Dict]:
        try:
            token = self._get_broadcaster_token()
            if not token:
                logger.error("No hay token del streamer disponible")
                log_service.add_log('error', 'No hay token del streamer disponible para obtener baneados', 'token_manager')
                return []
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Client-Id": settings.CLIENT_ID
            }
            
            all_banned = []
            cursor = None
            first = 100
            max_retries = 1
            
            while True:
                try:
                    url = f"https://api.twitch.tv/helix/moderation/banned?broadcaster_id={settings.BROADCASTER_ID}&first={first}"
                    if cursor:
                        url += f"&after={cursor}"
                    
                    response = requests.get(url, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        users = data.get('data', [])
                        all_banned.extend(users)
                        pagination = data.get('pagination', {})
                        cursor = pagination.get('cursor')
                        if not cursor:
                            break
                    
                    elif response.status_code == 401:
                        logger.warning("Token del streamer expirado, intentando refrescar...")
                        log_service.add_log('warning', 'Token del streamer expirado al obtener baneados, refrescando...', 'token_manager')
                        if self._refresh_token_if_needed("broadcaster") and max_retries > 0:
                            max_retries -= 1
                            token = self._get_broadcaster_token()
                            headers["Authorization"] = f"Bearer {token}"
                            continue
                        else:
                            logger.error("No se pudo refrescar el token del streamer")
                            log_service.add_log('error', 'No se pudo refrescar el token del streamer para baneados', 'token_manager')
                            break
                    else:
                        logger.error(f"Error obteniendo baneados de Twitch: {response.status_code}")
                        log_service.add_log('error', f'Error obteniendo baneados de Twitch: {response.status_code}', 'twitch_api')
                        break
                        
                except requests.exceptions.Timeout:
                    logger.error("Timeout al consultar Twitch API")
                    log_service.add_log('error', 'Timeout al consultar Twitch API para baneados', 'twitch_api')
                    break
                except Exception as e:
                    logger.error(f"Error en petición: {e}")
                    log_service.add_log('error', f'Error en petición de baneados: {e}', 'twitch_api')
                    break
            
            logger.info(f"📋 Total de usuarios baneados obtenidos: {len(all_banned)}")
            return all_banned
        except Exception as e:
            logger.error(f"Error obteniendo baneados de Twitch: {e}")
            log_service.add_log('error', f'Error obteniendo baneados de Twitch: {e}', 'twitch_api')
            return []
    
    def get_twitch_banned_users(self) -> List[Dict]:
        return self._get_cached_banned_users()
    
    def get_twitch_timeouts(self) -> List[Dict]:
        try:
            banned = self.get_twitch_banned_users()
            timeouts = []
            now = datetime.now().astimezone()
            
            for user in banned:
                end_time_str = user.get('end_time')
                if end_time_str:
                    try:
                        end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                        if end_time > now:
                            remaining = (end_time - now).total_seconds()
                            timeouts.append({
                                'user_id': user.get('user_id'),
                                'user_login': user.get('user_login', 'Desconocido'),
                                'user_name': user.get('user_name', user.get('user_login', 'Desconocido')),
                                'reason': user.get('reason', 'No especificada'),
                                'end_time': end_time_str,
                                'remaining_seconds': int(remaining)
                            })
                    except Exception as e:
                        logger.debug(f"Error parseando end_time: {e}")
                        continue
            
            logger.info(f"⏰ Encontrados {len(timeouts)} usuarios en timeout de Twitch")
            return timeouts
        except Exception as e:
            logger.error(f"Error obteniendo timeouts de Twitch: {e}")
            log_service.add_log('error', f'Error obteniendo timeouts de Twitch: {e}', 'twitch_api')
            return []
    
    def is_user_in_timeout(self, user_id: str) -> bool:
        try:
            timeouts = self.get_twitch_timeouts()
            for user in timeouts:
                if user.get('user_id') == user_id:
                    return True
            return False
        except Exception:
            return False
    
    def is_user_banned(self, user_id: str) -> bool:
        try:
            banned = self.get_twitch_banned_users()
            for user in banned:
                if user.get('user_id') == user_id:
                    if user.get('end_time') is None:
                        return True
            return False
        except Exception:
            return False
    
    def remove_twitch_ban(self, user_id: str) -> bool:
        try:
            token = self._get_token()
            if not token:
                logger.error("No hay token del bot disponible")
                log_service.add_log('error', 'No hay token del bot disponible para remover ban', 'token_manager')
                return False
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Client-Id": settings.CLIENT_ID
            }
            
            url = f"https://api.twitch.tv/helix/moderation/bans?broadcaster_id={settings.BROADCASTER_ID}&moderator_id={settings.BOT_ID}&user_id={user_id}"
            
            response = requests.delete(url, headers=headers, timeout=10)
            
            if response.status_code == 204:
                logger.info(f"✅ Ban removido para usuario {user_id}")
                log_service.add_log('info', f'Ban removido para usuario {user_id}', 'moderation')
                if user_id in self.banned_users:
                    del self.banned_users[user_id]
                if user_id in self.link_warnings:
                    del self.link_warnings[user_id]
                if user_id in self.warning_users:
                    del self.warning_users[user_id]
                if user_id in self.timeout_users:
                    del self.timeout_users[user_id]
                if user_id in self.timeout_user_names:
                    del self.timeout_user_names[user_id]
                self._save_data()
                self._banned_cache = []
                self._banned_cache_time = 0
                return True
            elif response.status_code == 401:
                logger.warning("Token del bot expirado, intentando refrescar...")
                log_service.add_log('warning', 'Token expirado al remover ban, refrescando...', 'token_manager')
                if self._refresh_token_if_needed("bot"):
                    return self.remove_twitch_ban(user_id)
                return False
            else:
                logger.error(f"Error removiendo ban: {response.status_code} - {response.text}")
                log_service.add_log('error', f'Error removiendo ban para {user_id}: {response.status_code}', 'twitch_api')
                return False
        except Exception as e:
            logger.error(f"Error removiendo ban: {e}")
            log_service.add_log('error', f'Error removiendo ban para {user_id}: {e}', 'twitch_api')
            return False
    
    def remove_twitch_timeout(self, user_id: str) -> bool:
        try:
            token = self._get_token()
            if not token:
                logger.error("No hay token del bot disponible")
                log_service.add_log('error', 'No hay token del bot disponible para remover timeout', 'token_manager')
                return False
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Client-Id": settings.CLIENT_ID
            }
            
            url = f"https://api.twitch.tv/helix/moderation/bans?broadcaster_id={settings.BROADCASTER_ID}&moderator_id={settings.BOT_ID}&user_id={user_id}"
            
            response = requests.delete(url, headers=headers, timeout=10)
            
            if response.status_code == 204:
                logger.info(f"✅ Timeout removido para usuario {user_id}")
                log_service.add_log('info', f'Timeout removido para usuario {user_id}', 'moderation')
                if user_id in self.timeout_users:
                    del self.timeout_users[user_id]
                if user_id in self.timeout_user_names:
                    del self.timeout_user_names[user_id]
                if user_id in self.link_warnings:
                    self.link_warnings[user_id] = 1
                    self.warning_users[user_id] = self.timeout_user_names.get(user_id, user_id)
                self._save_data()
                self._banned_cache = []
                self._banned_cache_time = 0
                return True
            elif response.status_code == 401:
                logger.warning("Token del bot expirado, intentando refrescar...")
                log_service.add_log('warning', 'Token expirado al remover timeout, refrescando...', 'token_manager')
                if self._refresh_token_if_needed("bot"):
                    return self.remove_twitch_timeout(user_id)
                return False
            else:
                logger.error(f"Error removiendo timeout: {response.status_code} - {response.text}")
                log_service.add_log('error', f'Error removiendo timeout para {user_id}: {response.status_code}', 'twitch_api')
                return False
        except Exception as e:
            logger.error(f"Error removiendo timeout: {e}")
            log_service.add_log('error', f'Error removiendo timeout para {user_id}: {e}', 'twitch_api')
            return False
    
    def check_user_status(self, user_id: str) -> Dict:
        try:
            banned = self.get_twitch_banned_users()
            for user in banned:
                if user.get('user_id') == user_id:
                    end_time_str = user.get('end_time')
                    is_timeout = end_time_str is not None
                    if is_timeout:
                        try:
                            end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                            now = datetime.now().astimezone()
                            if end_time <= now:
                                return {
                                    'banned': False,
                                    'user_id': user_id,
                                    'user_name': user.get('user_login', 'Desconocido'),
                                    'message': 'El timeout ha expirado'
                                }
                            remaining = (end_time - now).total_seconds()
                        except Exception:
                            remaining = 0
                    else:
                        remaining = 0
                    
                    return {
                        'banned': True,
                        'user_id': user_id,
                        'user_name': user.get('user_login', 'Desconocido'),
                        'reason': user.get('reason', 'No especificada'),
                        'end_time': end_time_str,
                        'is_timeout': is_timeout,
                        'remaining': self._format_remaining(remaining) if remaining > 0 else 'Permanente'
                    }
            
            return {
                'banned': False,
                'user_id': user_id,
                'user_name': 'Desconocido',
                'message': 'Usuario no está baneado ni en timeout'
            }
        except Exception as e:
            logger.error(f"Error verificando estado de usuario: {e}")
            log_service.add_log('error', f'Error verificando estado de usuario {user_id}: {e}', 'twitch_api')
            return {'banned': False, 'user_id': user_id, 'error': str(e)}
    
    def get_user_name_by_id(self, user_id: str) -> str:
        try:
            if user_id in self.warning_users:
                return self.warning_users[user_id]
            if user_id in self.timeout_user_names:
                return self.timeout_user_names[user_id]
            if user_id in self.banned_users:
                return self.banned_users[user_id].get('name', user_id)
            
            token = self._get_broadcaster_token()
            if not token:
                return user_id
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Client-Id": settings.CLIENT_ID
            }
            
            url = f"https://api.twitch.tv/helix/users?id={user_id}"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                users = data.get('data', [])
                if users:
                    return users[0].get('login', user_id)
            return user_id
        except Exception as e:
            logger.error(f"Error obteniendo nombre de usuario: {e}")
            log_service.add_log('error', f'Error obteniendo nombre de usuario {user_id}: {e}', 'twitch_api')
            return user_id
    
    # ============================================
    # FUNCIONES PARA EL DASHBOARD
    # ============================================
    
    def clear_warnings(self, user_id: str) -> int:
        count = warning_manager.clear_warnings(user_id, 'link')
        if user_id in self.link_warnings:
            del self.link_warnings[user_id]
        if user_id in self.warning_users:
            del self.warning_users[user_id]
        self._save_data()
        logger.info(f"🧹 Advertencias de enlaces limpiadas para usuario {user_id} ({count})")
        log_service.add_log('info', f'Advertencias de enlaces limpiadas para usuario {user_id}', 'moderation')
        return count
    
    def get_warning_count(self, user_id: str) -> int:
        return warning_manager.get_warning_count(user_id, 'link')
    
    def get_all_warnings(self) -> Dict[str, Dict]:
        result = {}
        for user_id, count in self.link_warnings.items():
            user_name = self.warning_users.get(user_id, user_id)
            result[user_id] = {
                'warnings': count,
                'user_name': user_name
            }
        return result
    
    def get_banned_users(self) -> Dict[str, Dict]:
        return self.banned_users.copy()
    
    def remove_ban(self, user_id: str) -> bool:
        if user_id in self.banned_users:
            del self.banned_users[user_id]
            if user_id in self.link_warnings:
                del self.link_warnings[user_id]
            if user_id in self.warning_users:
                del self.warning_users[user_id]
            if user_id in self.timeout_users:
                del self.timeout_users[user_id]
            if user_id in self.timeout_user_names:
                del self.timeout_user_names[user_id]
            self._save_data()
            logger.info(f"🔓 Ban removido para usuario {user_id}")
            log_service.add_log('info', f'Ban removido para usuario {user_id}', 'moderation')
            return True
        return False
    
    def get_timeout_users(self) -> Dict[str, float]:
        now = time.time()
        active_timeouts = {}
        expired = []
        for user_id, end_time in self.timeout_users.items():
            if end_time <= now:
                expired.append(user_id)
                if user_id in self.link_warnings:
                    self.link_warnings[user_id] = 1
                    self.warning_users[user_id] = self.timeout_user_names.get(user_id, user_id)
            else:
                remaining = end_time - now
                active_timeouts[user_id] = remaining
        
        for user_id in expired:
            del self.timeout_users[user_id]
            if user_id in self.timeout_user_names:
                del self.timeout_user_names[user_id]
        
        if expired:
            self._save_data()
        
        return active_timeouts
    
    def _format_remaining(self, seconds: float) -> str:
        if seconds <= 0:
            return "0s"
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        if minutes > 0:
            return f"{minutes}m {secs}s"
        return f"{secs}s"
    
    def get_timeout_users_with_names(self) -> Dict[str, Dict]:
        timeouts = self.get_timeout_users()
        result = {}
        for user_id, remaining in timeouts.items():
            user_name = self.timeout_user_names.get(user_id, user_id)
            result[user_id] = {
                'remaining': remaining,
                'user_name': user_name,
                'remaining_formatted': self._format_remaining(remaining)
            }
        return result
    
    def remove_timeout(self, user_id: str) -> bool:
        if user_id in self.timeout_users:
            del self.timeout_users[user_id]
            if user_id in self.timeout_user_names:
                del self.timeout_user_names[user_id]
            self._save_data()
            logger.info(f"⏰ Timeout removido para usuario {user_id}")
            log_service.add_log('info', f'Timeout removido para usuario {user_id}', 'moderation')
            return True
        return False

    def force_refresh_cache(self):
        self._banned_cache = []
        self._banned_cache_time = 0
        logger.info("🔄 Caché de baneados forzada a recargar")
        log_service.add_log('info', 'Caché de baneados forzada a recargar', 'bot')


link_manager = LinkManager()