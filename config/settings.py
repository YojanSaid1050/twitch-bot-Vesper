# config/settings.py
import os
import sys
import codecs
import json
import psycopg2
from pathlib import Path
from dotenv import load_dotenv
from config.env_manager import env_manager
from database.token_repository import TokenRepository
from utils.logger import get_logger

# Forzar UTF-8 en stdout/stderr para emojis
if sys.stdout.encoding != 'UTF-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
if sys.stderr.encoding != 'UTF-8':
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

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
        self._load_ids_from_db()  # ← NUEVO: carga IDs desde PostgreSQL
        self._load_tokens()
        self._initialized = True
        self._validate()
        if not os.environ.get("DATABASE_URL"):
            logger.warning("⚠️ DATABASE_URL no configurada. Los tokens no se persistirán correctamente.")

    def _load_static_config(self):
        """Carga variables estáticas desde .env (fallback)."""
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

        # MODERATOR_USER_ID: por defecto BOT_ID
        self.MODERATOR_USER_ID = os.environ.get("MODERATOR_USER_ID", self.BOT_ID)

    def _load_ids_from_db(self):
        """
        Carga los IDs desde la tabla bot_config de PostgreSQL,
        sobrescribiendo los valores del .env si existen.
        """
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            return

        try:
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT config_key, config_value FROM bot_config
                WHERE config_key IN ('broadcaster_id', 'bot_id', 'moderator_user_id')
            """)
            rows = cursor.fetchall()
            cursor.close()
            conn.close()

            for key, value_json in rows:
                value = json.loads(value_json) if isinstance(value_json, str) else value_json
                if key == 'broadcaster_id' and value:
                    self.BROADCASTER_ID = str(value)
                    logger.info(f"✅ Cargado BROADCASTER_ID = {self.BROADCASTER_ID} desde PostgreSQL")
                elif key == 'bot_id' and value:
                    self.BOT_ID = str(value)
                    logger.info(f"✅ Cargado BOT_ID = {self.BOT_ID} desde PostgreSQL")
                elif key == 'moderator_user_id' and value:
                    self.MODERATOR_USER_ID = str(value)
                    logger.info(f"✅ Cargado MODERATOR_USER_ID = {self.MODERATOR_USER_ID} desde PostgreSQL")

            # Si MODERATOR_USER_ID no se encontró, usar BOT_ID (que ya se cargó)
            if not getattr(self, "MODERATOR_USER_ID", "") and self.BOT_ID:
                self.MODERATOR_USER_ID = self.BOT_ID
                logger.info(f"🔁 MODERATOR_USER_ID = BOT_ID ({self.BOT_ID}) (por defecto)")

        except Exception as e:
            logger.warning(f"⚠️ No se pudieron cargar IDs desde PostgreSQL: {e}")

    def _load_tokens(self):
        """Carga tokens desde PostgreSQL. Si no existen, los migra desde .env."""
        token_mapping = {
            ("twitch", "bot"): ("BOT_TOKEN", "BOT_REFRESH_TOKEN"),
            ("twitch", "broadcaster"): ("BROADCASTER_TOKEN", "BROADCASTER_REFRESH_TOKEN"),
            ("twitch", "app"): ("APP_ACCESS_TOKEN", None),
            ("twitch", "moderator"): ("MODERATOR_ACCESS_TOKEN", "MODERATOR_REFRESH_TOKEN"),
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

        logger.info("🔁 El token de MODERATOR se sincronizará con el BOT al actualizar el BOT_TOKEN.")

    def reload(self):
        self._load_static_config()
        self._load_ids_from_db()
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

    # ============================================================
    # MÉTODOS DE ACTUALIZACIÓN
    # ============================================================

    def update_bot_token(self, new_token: str, expires_in: int):
        self.BOT_TOKEN = new_token
        TokenRepository.update_access_token("twitch", "bot", new_token, expires_in)
        logger.info(f"✅ Token BOT actualizado (expira en {expires_in//60}m)")
        # Sincronizar moderador con el bot
        self._sync_moderator_token(new_token, expires_in)

    def _sync_moderator_token(self, new_token: str, expires_in: int):
        self.MODERATOR_ACCESS_TOKEN = new_token
        TokenRepository.update_access_token("twitch", "moderator", new_token, expires_in)
        logger.info(f"✅ Token MODERATOR sincronizado con BOT (expira en {expires_in//60}m)")

    def update_broadcaster_token(self, new_token: str, expires_in: int):
        self.BROADCASTER_TOKEN = new_token
        TokenRepository.update_access_token("twitch", "broadcaster", new_token, expires_in)
        logger.info(f"✅ Token BROADCASTER actualizado (expira en {expires_in//60}m)")

    def update_app_token(self, new_token: str, expires_in: int = 5184000):
        self.APP_ACCESS_TOKEN = new_token
        TokenRepository.update_access_token("twitch", "app", new_token, expires_in)
        logger.info(f"✅ Token APP actualizado (expira en {expires_in//3600}h)")

    def update_bot_refresh_token(self, new_refresh: str):
        self.BOT_REFRESH_TOKEN = new_refresh
        TokenRepository.update_refresh_token("twitch", "bot", new_refresh)
        logger.info("✅ Refresh token BOT actualizado")
        self._sync_moderator_refresh_token(new_refresh)

    def _sync_moderator_refresh_token(self, new_refresh: str):
        self.MODERATOR_REFRESH_TOKEN = new_refresh
        TokenRepository.update_refresh_token("twitch", "moderator", new_refresh)
        logger.info("✅ Refresh token MODERATOR sincronizado con BOT")

    def update_broadcaster_refresh_token(self, new_refresh: str):
        self.BROADCASTER_REFRESH_TOKEN = new_refresh
        TokenRepository.update_refresh_token("twitch", "broadcaster", new_refresh)
        logger.info("✅ Refresh token BROADCASTER actualizado")

    def update_spotify_refresh_token(self, new_refresh: str):
        self.SPOTIFY_REFRESH_TOKEN = new_refresh
        TokenRepository.update_refresh_token("spotify", "default", new_refresh)
        logger.info("✅ Refresh token SPOTIFY actualizado")

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