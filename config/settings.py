"""
Configuración central del bot
"""

import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()


class Settings:
    """Configuración global del bot (Singleton)"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        """Cargar configuración desde .env"""
        # Tokens (limpiar prefix oauth: si existe)
        self.BOT_TOKEN = os.getenv("BOT_TOKEN", "").replace("oauth:", "")
        self.BOT_REFRESH_TOKEN = os.getenv("BOT_REFRESH_TOKEN", "")
        self.BROADCASTER_TOKEN = os.getenv("BROADCASTER_TOKEN", "").replace("oauth:", "")
        self.BROADCASTER_REFRESH_TOKEN = os.getenv("BROADCASTER_REFRESH_TOKEN", "")
        
        # App Access Token (para EventSub)
        self.APP_ACCESS_TOKEN = os.getenv("APP_ACCESS_TOKEN", "")
        
        # IDs y cliente
        self.CLIENT_ID = os.getenv("CLIENT_ID", "")
        self.CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")
        self.BROADCASTER_ID = os.getenv("BROADCASTER_ID", "")
        self.BOT_ID = os.getenv("BOT_ID", "")
        
        # Canal y nombre del bot
        self.CHANNEL = os.getenv("CHANNEL", "")
        self.BOT_NICK = os.getenv("BOT_NICK", "")
        
        # Spotify credentials
        self.SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
        self.SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
        
        # EventSub configuration
        self.EVENTSUB_CALLBACK_URL = os.getenv("EVENTSUB_CALLBACK_URL", "")
        self.TWITCH_WEBHOOK_SECRET = os.getenv("TWITCH_WEBHOOK_SECRET", "")
        self.BOT_WEBHOOK_PORT = int(os.getenv("BOT_WEBHOOK_PORT", "5001"))
        self.BOT_WEBHOOK_URL = os.getenv("BOT_WEBHOOK_URL", "http://localhost:5001/webhook")
        
        # Headers para API (se actualizarán dinámicamente)
        self._update_headers()
        
        # Validar configuración
        self._validate()
    
    def _update_headers(self):
        """Actualizar headers con los tokens actuales"""
        self.BOT_HEADERS = {
            "Authorization": f"Bearer {self.BOT_TOKEN}",
            "Client-Id": self.CLIENT_ID,
            "Content-Type": "application/json"
        }
        
        self.BROADCASTER_HEADERS = {
            "Authorization": f"Bearer {self.BROADCASTER_TOKEN}",
            "Client-Id": self.CLIENT_ID,
            "Content-Type": "application/json"
        }
    
    def update_bot_token(self, new_token: str):
        """Actualizar token del bot"""
        self.BOT_TOKEN = new_token
        self._update_headers()
        self._save_to_env("BOT_TOKEN", f"oauth:{new_token}")
    
    def update_broadcaster_token(self, new_token: str):
        """Actualizar token del streamer"""
        self.BROADCASTER_TOKEN = new_token
        self._update_headers()
        self._save_to_env("BROADCASTER_TOKEN", f"oauth:{new_token}")
    
    def update_app_token(self, new_token: str):
        """Actualizar App Access Token"""
        self.APP_ACCESS_TOKEN = new_token
        self._save_to_env("APP_ACCESS_TOKEN", new_token)
    
    def _save_to_env(self, key: str, value: str):
        """Guardar cambio en .env (opcional, para persistencia)"""
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        
        try:
            with open(env_path, "r") as f:
                lines = f.readlines()
            
            updated = False
            for i, line in enumerate(lines):
                if line.startswith(f"{key}="):
                    lines[i] = f"{key}={value}\n"
                    updated = True
                    break
            
            if not updated:
                lines.append(f"{key}={value}\n")
            
            with open(env_path, "w") as f:
                f.writelines(lines)
            
            print(f"✅ {key} actualizado en .env")
        except Exception as e:
            print(f"⚠️ No se pudo actualizar .env: {e}")
    
    def _validate(self):
        """Validar que todas las variables necesarias existen"""
        required = [
            ("BOT_TOKEN", self.BOT_TOKEN),
            ("BROADCASTER_TOKEN", self.BROADCASTER_TOKEN),
            ("CLIENT_ID", self.CLIENT_ID),
            ("CLIENT_SECRET", self.CLIENT_SECRET),
            ("BROADCASTER_ID", self.BROADCASTER_ID),
            ("BOT_ID", self.BOT_ID),
            ("CHANNEL", self.CHANNEL),
        ]
        
        missing = [name for name, value in required if not value]
        
        if not self.BOT_REFRESH_TOKEN:
            print("⚠️ BOT_REFRESH_TOKEN no configurado. Los tokens expirarán cada 4 horas.")
        if not self.BROADCASTER_REFRESH_TOKEN:
            print("⚠️ BROADCASTER_REFRESH_TOKEN no configurado. Los tokens expirarán cada 4 horas.")
        
        if not self.APP_ACCESS_TOKEN:
            print("⚠️ APP_ACCESS_TOKEN no configurado. Las notificaciones de subs/raids no funcionarán.")
        
        if not self.EVENTSUB_CALLBACK_URL:
            print("⚠️ EVENTSUB_CALLBACK_URL no configurado. Las notificaciones automáticas no funcionarán.")
        if not self.TWITCH_WEBHOOK_SECRET:
            print("⚠️ TWITCH_WEBHOOK_SECRET no configurado. Las notificaciones automáticas no funcionarán.")
        
        if missing:
            raise ValueError(
                f"❌ Variables de entorno faltantes: {', '.join(missing)}\n"
                "Revisa tu archivo .env"
            )


# Instancia global
settings = Settings()