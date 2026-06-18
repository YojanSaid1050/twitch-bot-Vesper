import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from utils.logger import get_logger
from services.log_service import log_service

logger = get_logger(__name__)

CONFIG_PATH = Path(__file__).parent.parent / "data" / "config.json"


class ConfigService:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not ConfigService._initialized:
            self.config = {}
            self._load_config()
            ConfigService._initialized = True
            self._callbacks = []

    def _load_config(self):
        try:
            if CONFIG_PATH.exists():
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                logger.info("Configuración cargada")
            else:
                self.config = self._get_default_config()
                self._save_config()
                logger.info("Configuración por defecto creada")
        except Exception as e:
            logger.error(f"Error cargando configuración: {e}")
            log_service.add_log('error', f'Error cargando configuración: {e}', 'config_service')
            self.config = self._get_default_config()

    def _get_default_config(self) -> Dict:
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

    def _save_config(self):
        try:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            self._notify_change()
        except Exception as e:
            logger.error(f"Error guardando configuración: {e}")
            log_service.add_log('error', f'Error guardando configuración: {e}', 'config_service')

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

    def add_custom_command(self, name: str, response: str, cooldown: int = 0) -> bool:
        commands = self.get_custom_commands()
        commands[name] = {
            'response': response,
            'cooldown': cooldown,
            'created_at': datetime.now().isoformat()
        }
        log_service.add_log('info', f'Comando personalizado creado: !{name}', 'config_service')
        return self.set('custom_commands', commands)

    def remove_custom_command(self, name: str) -> bool:
        commands = self.get_custom_commands()
        if name in commands:
            del commands[name]
            log_service.add_log('info', f'Comando personalizado eliminado: !{name}', 'config_service')
            return self.set('custom_commands', commands)
        return False

    # ---- WARNINGS (sistema de warns por staff) ----
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
        log_service.add_log('info', f'Advertencia añadida a {user_name}: {reason}', 'config_service')
        return warning_id

    def get_warnings(self, user_id: str) -> List[Dict]:
        warnings = self.get('warnings', [])
        return [w for w in warnings if w.get('user_id') == user_id]

    def clear_warnings(self, user_id: str) -> int:
        warnings = self.get('warnings', [])
        count = len([w for w in warnings if w.get('user_id') == user_id])
        warnings = [w for w in warnings if w.get('user_id') != user_id]
        self.set('warnings', warnings)
        log_service.add_log('info', f'Advertencias limpiadas para usuario {user_id} ({count})', 'config_service')
        return count

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


config_service = ConfigService()