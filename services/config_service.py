import json
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime

from utils.logger import get_logger
from services.log_service import log_service

logger = get_logger(__name__)


class ConfigService:
    _instance = None
    _initialized = False
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not ConfigService._initialized:
            self.config = {}
            self._callbacks = []
            self._load_config()
            ConfigService._initialized = True

    def _get_default_config(self) -> Dict:
        """Estructura de configuración por defecto."""
        return {
            "dashboard": {
                "enabled": True,
                "port": 5002,
                "password": "admin123",
                "session_timeout": 3600
            },
            "bot_icon": "🕯️",
            "moderation": {
                "banned_words": [],
                "max_warnings": 3,
                "auto_timeout_minutes": 10,
                "slow_mode": {"enabled": False, "seconds": 10},
                "follower_mode": {"enabled": False, "minutes": 10},
                "emote_mode": False,
                "subscriber_mode": False
            },
            "allowed_links": {},
            "social_links": {
                "discord": "https://discord.gg/invite",
                "twitter": "https://twitter.com/",
                "instagram": "https://instagram.com/",
                "youtube": "https://youtube.com/",
                "tiktok": "https://tiktok.com/@"
            },
            "spotify": {
                "enabled": True,
                "history_limit": 10,
                "default_volume": 50
            },
            "custom_commands": {},
            "quotes": [],
            "timers": {},
            "warnings": [],
            "link_management": {
                "warnings": {},
                "warning_users": {},
                "banned": {},
                "timeouts": {},
                "timeout_names": {}
            },
            "stats_history": [],
            "warning_manager": {
                "warnings": {}
            }
        }

    def _load_config(self):
        """Carga la configuración exclusivamente desde PostgreSQL."""
        try:
            from database.config_repository import ConfigRepository
            pg_config = ConfigRepository.get_config()
            if pg_config:
                self.config = pg_config
                logger.info("Configuración cargada desde PostgreSQL")
                return
        except Exception as e:
            logger.warning(f"No se pudo cargar desde PostgreSQL: {e}")

        # Si no hay datos en PostgreSQL, usar valores por defecto y guardarlos
        logger.info("No hay configuración en PostgreSQL. Creando valores por defecto...")
        self.config = self._get_default_config()
        self._save_config()

    def _save_config(self):
        """Guarda la configuración exclusivamente en PostgreSQL."""
        with self._lock:
            try:
                from database.config_repository import ConfigRepository
                ConfigRepository.save_config(self.config)
                logger.debug("Configuración guardada en PostgreSQL")
            except Exception as e:
                logger.error(f"Error guardando configuración en PostgreSQL: {e}")
                log_service.add_log('error', f'Error guardando configuración en PostgreSQL: {e}', 'config_service')
            self._notify_change()

    def _notify_change(self):
        for callback in self._callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error en callback: {e}")

    def on_change(self, callback):
        self._callbacks.append(callback)

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split('.')
        value = self.config
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any) -> bool:
        keys = key.split('.')
        config = self.config
        try:
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            config[keys[-1]] = value
            self._save_config()
            return True
        except Exception as e:
            logger.error(f"Error estableciendo {key}: {e}")
            log_service.add_log('error', f'Error estableciendo {key}: {e}', 'config_service')
            return False

    # ---- DASHBOARD ----
    def get_dashboard_password(self) -> str:
        return self.get('dashboard.password', 'admin123')

    def set_dashboard_password(self, password: str) -> bool:
        return self.set('dashboard.password', password)

    # ---- BOT ICON ----
    def get_bot_icon(self) -> str:
        return self.get('bot_icon', '🕯️')

    def set_bot_icon(self, icon: str) -> bool:
        return self.set('bot_icon', icon)

    # ---- BANNED WORDS ----
    def get_banned_words(self) -> List[str]:
        return self.get('moderation.banned_words', [])

    def add_banned_word(self, word: str) -> bool:
        words = self.get_banned_words()
        if word.lower() not in [w.lower() for w in words]:
            words.append(word)
            return self.set('moderation.banned_words', words)
        return False

    def remove_banned_word(self, word: str) -> bool:
        words = self.get_banned_words()
        words = [w for w in words if w.lower() != word.lower()]
        return self.set('moderation.banned_words', words)

    # ---- ALLOWED LINKS ----
    def get_allowed_links(self) -> Dict[str, bool]:
        return self.get('allowed_links', {})

    def add_allowed_link(self, domain: str) -> bool:
        links = self.get_allowed_links()
        domain = domain.lower().strip()
        links[domain] = True
        return self.set('allowed_links', links)

    def remove_allowed_link(self, domain: str) -> bool:
        links = self.get_allowed_links()
        domain = domain.lower().strip()
        if domain in links:
            del links[domain]
            return self.set('allowed_links', links)
        return False

    # ---- MODERATION SETTINGS ----
    def get_slow_mode(self) -> Dict:
        return self.get('moderation.slow_mode', {'enabled': False, 'seconds': 10})

    def set_slow_mode(self, enabled: bool, seconds: int = 10) -> bool:
        return self.set('moderation.slow_mode', {'enabled': enabled, 'seconds': seconds})

    def get_follower_mode(self) -> Dict:
        return self.get('moderation.follower_mode', {'enabled': False, 'minutes': 10})

    def set_follower_mode(self, enabled: bool, minutes: int = 10) -> bool:
        return self.set('moderation.follower_mode', {'enabled': enabled, 'minutes': minutes})

    def get_emote_mode(self) -> bool:
        return self.get('moderation.emote_mode', False)

    def set_emote_mode(self, enabled: bool) -> bool:
        return self.set('moderation.emote_mode', enabled)

    def get_subscriber_mode(self) -> bool:
        return self.get('moderation.subscriber_mode', False)

    def set_subscriber_mode(self, enabled: bool) -> bool:
        return self.set('moderation.subscriber_mode', enabled)

    def get_max_warnings(self) -> int:
        return self.get('moderation.max_warnings', 3)

    def set_max_warnings(self, value: int) -> bool:
        value = max(1, min(10, value))
        return self.set('moderation.max_warnings', value)

    # ---- SOCIAL LINKS ----
    def get_social_link(self, platform: str) -> str:
        return self.get(f'social_links.{platform}', '')

    def set_social_link(self, platform: str, url: str) -> bool:
        return self.set(f'social_links.{platform}', url)

    # ---- CUSTOM COMMANDS ----
    def get_custom_commands(self) -> Dict:
        return self.get('custom_commands', {})

    CUSTOM_COMMAND_LEVELS = ('everyone', 'sub', 'vip', 'mod', 'owner')

    def add_custom_command(self, name: str, response: str, cooldown: int = 0,
                           level: str = 'everyone', user_cooldown: int = 0) -> bool:
        commands = self.get_custom_commands()
        previous = commands.get(name, {})
        commands[name] = {
            'response': response,
            'cooldown': max(0, int(cooldown or 0)),
            'user_cooldown': max(0, int(user_cooldown or 0)),
            'level': level if level in self.CUSTOM_COMMAND_LEVELS else 'everyone',
            'count': previous.get('count', 0),
            'created_at': previous.get('created_at', datetime.now().isoformat())
        }
        log_service.add_log('info', f'Comando personalizado creado: !{name}', 'dashboard')
        return self.set('custom_commands', commands)

    def update_custom_command(self, name: str, **fields) -> bool:
        """Actualiza campos de un comando existente (response, cooldown, user_cooldown, level)."""
        commands = self.get_custom_commands()
        if name not in commands:
            return False
        cmd = dict(commands[name])
        for key, value in fields.items():
            if key in ('cooldown', 'user_cooldown', 'count'):
                cmd[key] = max(0, int(value))
            elif key == 'level':
                if value not in self.CUSTOM_COMMAND_LEVELS:
                    return False
                cmd[key] = value
            elif key == 'response':
                cmd[key] = str(value)
        commands[name] = cmd
        return self.set('custom_commands', commands)

    def increment_custom_command_count(self, name: str) -> int:
        commands = self.get_custom_commands()
        if name not in commands:
            return 0
        count = int(commands[name].get('count', 0)) + 1
        commands[name]['count'] = count
        self.set('custom_commands', commands)
        return count

    def remove_custom_command(self, name: str) -> bool:
        commands = self.get_custom_commands()
        if name in commands:
            del commands[name]
            log_service.add_log('info', f'Comando personalizado eliminado: !{name}', 'dashboard')
            return self.set('custom_commands', commands)
        return False

    # ---- WARNINGS ----
    def add_warning(self, user_id: str, user_name: str, reason: str, warned_by: str) -> int:
        warnings = self.get('warnings', [])
        warning_id = len(warnings) + 1
        warnings.append({
            'id': warning_id,
            'user_id': user_id,
            'user_name': user_name,
            'reason': reason,
            'warned_by': warned_by,
            'warned_at': datetime.now().isoformat()
        })
        self.set('warnings', warnings)
        log_service.add_log('warning', f'Advertencia añadida a {user_name}: "{reason}" por {warned_by}', 'moderation')
        return warning_id

    def get_warnings(self, user_id: str) -> List[Dict]:
        warnings = self.get('warnings', [])
        return [w for w in warnings if w.get('user_id') == user_id]

    def clear_warnings(self, user_id: str) -> int:
        warnings = self.get('warnings', [])
        count = len([w for w in warnings if w.get('user_id') == user_id])
        warnings = [w for w in warnings if w.get('user_id') != user_id]
        self.set('warnings', warnings)
        log_service.add_log('info', f'Advertencias limpiadas para usuario {user_id} ({count} eliminadas)', 'moderation')
        return count

    # ---- QUOTES (citas) ----
    def get_quotes(self) -> List[Dict]:
        return self.get('quotes', [])

    def add_quote(self, text: str, added_by: str, game: str = '') -> int:
        quotes = self.get_quotes()
        next_id = max([q.get('id', 0) for q in quotes], default=0) + 1
        quotes.append({
            'id': next_id,
            'text': text[:400],
            'added_by': added_by,
            'game': game,
            'date': datetime.now().strftime('%Y-%m-%d')
        })
        self.set('quotes', quotes)
        return next_id

    def update_quote(self, quote_id: int, text: str = None, game: str = None) -> bool:
        quotes = self.get_quotes()
        for quote in quotes:
            if quote.get('id') == quote_id:
                if text is not None:
                    quote['text'] = text[:400]
                if game is not None:
                    quote['game'] = game[:100]
                return self.set('quotes', quotes)
        return False

    def remove_quote(self, quote_id: int) -> bool:
        quotes = self.get_quotes()
        remaining = [q for q in quotes if q.get('id') != quote_id]
        if len(remaining) == len(quotes):
            return False
        return self.set('quotes', remaining)

    # ---- TIMERS (mensajes periódicos) ----
    def get_timers(self) -> Dict[str, Dict]:
        return self.get('timers', {})

    def set_timer(self, name: str, message: str, interval_minutes: int, min_lines: int = 5) -> bool:
        timers = self.get_timers()
        timers[name] = {
            'message': message[:500],
            'interval': max(1, int(interval_minutes)),
            'min_lines': max(0, int(min_lines)),
            'enabled': True,
        }
        return self.set('timers', timers)

    def toggle_timer(self, name: str, enabled: bool) -> bool:
        timers = self.get_timers()
        if name not in timers:
            return False
        timers[name]['enabled'] = bool(enabled)
        return self.set('timers', timers)

    def remove_timer(self, name: str) -> bool:
        timers = self.get_timers()
        if name not in timers:
            return False
        del timers[name]
        return self.set('timers', timers)

    # ---- SPOTIFY ----
    def get_spotify_volume(self) -> int:
        return self.get('spotify.default_volume', 50)

    def set_spotify_volume(self, volume: int) -> bool:
        volume = max(0, min(100, volume))
        return self.set('spotify.default_volume', volume)

    # ---- STATS HISTORY ----
    def get_stats_history(self, limit: int = 7) -> List[Dict]:
        history = self.get('stats_history', [])
        history = sorted(history, key=lambda x: x.get('timestamp', ''))
        return history[-limit:] if limit else history

    def add_stats_snapshot(self, followers: int, subscribers: int, cheers: int) -> bool:
        now = datetime.now().isoformat()
        history = self.get('stats_history', [])
        if history:
            last = history[-1]
            try:
                last_time = datetime.fromisoformat(last.get('timestamp', ''))
                if (datetime.now() - last_time).total_seconds() < 1800:
                    return False
            except:
                pass
        history.append({
            'timestamp': now,
            'followers': followers,
            'subscribers': subscribers,
            'cheers': cheers
        })
        if len(history) > 100:
            history = history[-100:]
        return self.set('stats_history', history)

    # ---- LINK MANAGEMENT ----
    def get_link_management(self) -> Dict:
        return self.get('link_management', {})

    def set_link_management(self, data: Dict) -> bool:
        return self.set('link_management', data)

    # ---- WARNING MANAGER ----
    def get_warning_manager_data(self) -> Dict:
        return self.get('warning_manager', {})

    def set_warning_manager_data(self, data: Dict) -> bool:
        return self.set('warning_manager', data)


# Instancia global
config_service = ConfigService()