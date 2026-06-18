import os
from pathlib import Path
from dotenv import load_dotenv
from config.env_manager import env_manager
from database.token_repository import TokenRepository
from utils.logger import get_logger

# Cargar .env local solo si existe (para desarrollo)
load_dotenv()

logger = get_logger(__name__)

class Settings:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._load_static_config()
        self._load_tokens()
        self._initialized = True
        self._validate()
        if not os.environ.get("DATABASE_URL"):
            logger.warning("⚠️ DATABASE_URL no configurada. Los tokens no se persistirán correctamente.")

    def _load_static_config(self):
        """
        Carga configuración fija.
        Prioriza las variables del entorno del sistema (os.environ).
        Si no están, intenta cargarlas desde .env (a través de env_manager).
        """
        # Primero, intentar desde os.environ (producción)
        self.CLIENT_ID = os.environ.get("CLIENT_ID", "")
        self.CLIENT_SECRET = os.environ.get("CLIENT_SECRET", "")
        self.CHANNEL = os.environ.get("CHANNEL", "")
        self.BOT_NICK = os.environ.get("BOT_NICK", "")
        self.BOT_ID = os.environ.get("BOT_ID", "")
        self.BROADCASTER_ID = os.environ.get("BROADCASTER_ID", "")
        self.SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID", "")
        self.SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET", "")
        self.EVENTSUB_CALLBACK_URL = os.environ.get("EVENTSUB_CALLBACK_URL", "")
        self.TWITCH_WEBHOOK_SECRET = os.environ.get("TWITCH_WEBHOOK_SECRET", "")
        self.BOT_WEBHOOK_PORT = int(os.environ.get("BOT_WEBHOOK_PORT", "5001"))
        self.BOT_WEBHOOK_URL = os.environ.get("BOT_WEBHOOK_URL", "http://localhost:5001/webhook")
        self.DASHBOARD_SECRET_KEY = os.environ.get("DASHBOARD_SECRET_KEY", "supersecretkey_change_me")

        # Si alguna variable obligatoria sigue vacía, intentar cargarla desde .env (fallback)
        if not self.CLIENT_ID or not self.CLIENT_SECRET:
            env_vars = env_manager.reload()
            if not self.CLIENT_ID:
                self.CLIENT_ID = env_vars.get("CLIENT_ID", "")
            if not self.CLIENT_SECRET:
                self.CLIENT_SECRET = env_vars.get("CLIENT_SECRET", "")
            if not self.CHANNEL:
                self.CHANNEL = env_vars.get("CHANNEL", "")
            if not self.BOT_NICK:
                self.BOT_NICK = env_vars.get("BOT_NICK", "")
            if not self.BOT_ID:
                self.BOT_ID = env_vars.get("BOT_ID", "")
            if not self.BROADCASTER_ID:
                self.BROADCASTER_ID = env_vars.get("BROADCASTER_ID", "")

    def _load_tokens(self):
        """Carga tokens desde PostgreSQL. Si no existen, los migra desde .env."""
        token_mapping = {
            ("twitch", "bot"): ("BOT_TOKEN", "BOT_REFRESH_TOKEN"),
            ("twitch", "broadcaster"): ("BROADCASTER_TOKEN", "BROADCASTER_REFRESH_TOKEN"),
            ("twitch", "app"): ("APP_ACCESS_TOKEN", None),
            ("spotify", "default"): (None, "SPOTIFY_REFRESH_TOKEN"),
        }

        for (provider, account), (access_attr, refresh_attr) in token_mapping.items():
            token_data = TokenRepository.get_token(provider, account)
            if token_data:
                if access_attr:
                    setattr(self, access_attr, token_data.get("access_token", ""))
                if refresh_attr:
                    setattr(self, refresh_attr, token_data.get("refresh_token", ""))
            else:
                # Migrar desde .env si existe
                env_vars = env_manager.reload()
                access = env_vars.get(access_attr, "") if access_attr else None
                refresh = env_vars.get(refresh_attr, "") if refresh_attr else None

                if access or refresh:
                    TokenRepository.save_token(provider, account, access or "", refresh)
                    if access_attr:
                        setattr(self, access_attr, access or "")
                    if refresh_attr:
                        setattr(self, refresh_attr, refresh or "")
                    logger.info(f"✅ Migrado token {provider}/{account} desde .env a PostgreSQL")
                else:
                    if access_attr:
                        setattr(self, access_attr, "")
                    if refresh_attr:
                        setattr(self, refresh_attr, "")

        # Atributo adicional para Spotify access token (no guardado en settings)
        self.SPOTIFY_ACCESS_TOKEN = None

    def reload(self):
        """Recarga configuración y tokens desde PostgreSQL."""
        self._load_static_config()
        self._load_tokens()
        self._validate()
        logger.info("🔄 Configuración recargada")

    @property
    def BOT_HEADERS(self):
        return {
            "Authorization": f"Bearer {self.BOT_TOKEN}",
            "Client-Id": self.CLIENT_ID,
            "Content-Type": "application/json"
        }

    @property
    def BROADCASTER_HEADERS(self):
        return {
            "Authorization": f"Bearer {self.BROADCASTER_TOKEN}",
            "Client-Id": self.CLIENT_ID,
            "Content-Type": "application/json"
        }

    # Métodos para actualizar tokens (usados por TokenManager)
    def update_bot_token(self, new_token: str, expires_in: int):
        self.BOT_TOKEN = new_token
        TokenRepository.update_access_token("twitch", "bot", new_token, expires_in)

    def update_broadcaster_token(self, new_token: str, expires_in: int):
        self.BROADCASTER_TOKEN = new_token
        TokenRepository.update_access_token("twitch", "broadcaster", new_token, expires_in)

    def update_app_token(self, new_token: str, expires_in: int = 5184000):
        self.APP_ACCESS_TOKEN = new_token
        TokenRepository.update_access_token("twitch", "app", new_token, expires_in)

    def update_bot_refresh_token(self, new_refresh: str):
        self.BOT_REFRESH_TOKEN = new_refresh
        TokenRepository.update_refresh_token("twitch", "bot", new_refresh)

    def update_broadcaster_refresh_token(self, new_refresh: str):
        self.BROADCASTER_REFRESH_TOKEN = new_refresh
        TokenRepository.update_refresh_token("twitch", "broadcaster", new_refresh)

    def update_spotify_refresh_token(self, new_refresh: str):
        self.SPOTIFY_REFRESH_TOKEN = new_refresh
        TokenRepository.update_refresh_token("spotify", "default", new_refresh)

    def _validate(self):
        required = {
            "CLIENT_ID": self.CLIENT_ID,
            "CLIENT_SECRET": self.CLIENT_SECRET,
            "BROADCASTER_ID": self.BROADCASTER_ID,
            "BOT_ID": self.BOT_ID,
            "CHANNEL": self.CHANNEL,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(f"❌ Variables obligatorias faltantes: {', '.join(missing)}")

        if not self.BOT_REFRESH_TOKEN:
            logger.warning("⚠️ BOT_REFRESH_TOKEN no configurado en base de datos.")
        if not self.BROADCASTER_REFRESH_TOKEN:
            logger.warning("⚠️ BROADCASTER_REFRESH_TOKEN no configurado en base de datos.")
        if not self.SPOTIFY_REFRESH_TOKEN:
            logger.warning("⚠️ SPOTIFY_REFRESH_TOKEN no configurado en base de datos.")

settings = Settings()