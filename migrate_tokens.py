#!/usr/bin/env python3
"""
Migrar todos los tokens desde .env a PostgreSQL.
Ejecutar: python migrate_tokens.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras

# Cargar .env local
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# Configurar DATABASE_URL (debe estar en .env o en entorno)
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL no configurada")
    sys.exit(1)

# Tokens a migrar: (provider, account, access_key, refresh_key, expires_in_opcional)
tokens = [
    ("twitch", "bot", "BOT_TOKEN", "BOT_REFRESH_TOKEN", 14400),
    ("twitch", "broadcaster", "BROADCASTER_TOKEN", "BROADCASTER_REFRESH_TOKEN", 14400),
    ("twitch", "app", "APP_ACCESS_TOKEN", None, 5184000),
    ("spotify", "default", None, "SPOTIFY_REFRESH_TOKEN", 3600),
]

def migrate():
    print("🔄 Migrando tokens desde .env a PostgreSQL...")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    for provider, account, access_key, refresh_key, expires_in in tokens:
        access_token = os.getenv(access_key) if access_key else None
        refresh_token = os.getenv(refresh_key) if refresh_key else None

        if not access_token and not refresh_token:
            print(f"⚠️ No hay datos para {provider}/{account}, omitiendo.")
            continue

        # Si no hay access_token pero sí refresh, dejamos access_token vacío (caso Spotify)
        if not access_token:
            access_token = ""

        print(f"📥 Migrando {provider}/{account}...")
        print(f"   access_token: {access_token[:10] if access_token else 'N/A'}...")
        print(f"   refresh_token: {refresh_token[:10] if refresh_token else 'N/A'}...")

        expires_at = None
        if expires_in and access_token:
            import time
            expires_at = int(time.time() + expires_in)

        cur.execute("""
            INSERT INTO oauth_tokens (provider, account, access_token, refresh_token, expires_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, EXTRACT(EPOCH FROM NOW())::BIGINT)
            ON CONFLICT (provider, account) DO UPDATE SET
                access_token = EXCLUDED.access_token,
                refresh_token = EXCLUDED.refresh_token,
                expires_at = EXCLUDED.expires_at,
                updated_at = EXCLUDED.updated_at
        """, (provider, account, access_token, refresh_token, expires_at))

    conn.commit()
    cur.close()
    conn.close()
    print("✅ Migración completada.")

if __name__ == "__main__":
    migrate()