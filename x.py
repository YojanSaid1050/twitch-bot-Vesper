#!/usr/bin/env python3
"""
Sincroniza los tokens OAuth desde el archivo .env hacia PostgreSQL.
- Lee el .env y extrae BOT_TOKEN, BOT_REFRESH_TOKEN, BROADCASTER_TOKEN,
  BROADCASTER_REFRESH_TOKEN, APP_ACCESS_TOKEN y SPOTIFY_REFRESH_TOKEN.
- Además, sincroniza MODERATOR_ACCESS_TOKEN (usando los mismos valores que broadcaster)
  y MODERATOR_USER_ID (como configuración en bot_config).
- Conecta a la base de datos usando DATABASE_URL del .env o argumento.
- Inserta o actualiza los registros en la tabla oauth_tokens.
- Crea la tabla si no existe.
"""

import os
import sys
import argparse
import time
import json
from pathlib import Path
from typing import Dict, Optional

# Intentar importar dependencias
try:
    import psycopg2
    import psycopg2.extras
    from dotenv import load_dotenv
except ImportError as e:
    print(f"❌ Error: {e}. Asegúrate de tener instalados psycopg2-binary y python-dotenv.")
    print("   pip install psycopg2-binary python-dotenv")
    sys.exit(1)


# ============================================================
# 1. LECTURA DEL .env
# ============================================================

def load_env(env_path: str = ".env") -> Dict[str, str]:
    """Lee el archivo .env y devuelve un diccionario con las variables."""
    env_vars = {}
    if not Path(env_path).exists():
        print(f"❌ No se encontró el archivo {env_path}")
        sys.exit(1)

    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            env_vars[key.strip()] = value.strip()
    return env_vars


# ============================================================
# 2. CONEXIÓN Y CREACIÓN DE TABLAS
# ============================================================

def get_db_connection(db_url: str):
    """Obtiene una conexión a PostgreSQL."""
    try:
        conn = psycopg2.connect(db_url)
        return conn
    except Exception as e:
        print(f"❌ Error conectando a la base de datos: {e}")
        sys.exit(1)


def ensure_tables(conn):
    """Crea las tablas necesarias si no existen."""
    with conn.cursor() as cur:
        # Tabla oauth_tokens
        cur.execute("""
            CREATE TABLE IF NOT EXISTS oauth_tokens (
                provider TEXT NOT NULL,
                account TEXT NOT NULL,
                access_token TEXT,
                refresh_token TEXT,
                expires_at BIGINT,
                updated_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT,
                PRIMARY KEY (provider, account)
            )
        """)
        # Tabla bot_config (para guardar MODERATOR_USER_ID y otras configuraciones)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bot_config (
                id SERIAL PRIMARY KEY,
                config_key TEXT NOT NULL UNIQUE,
                config_value JSONB NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


# ============================================================
# 3. ACTUALIZACIÓN O INSERCIÓN DE TOKENS
# ============================================================

def upsert_token(conn, provider: str, account: str, access_token: Optional[str],
                 refresh_token: Optional[str], expires_in: Optional[int]):
    """
    Inserta o actualiza un token en la tabla oauth_tokens.
    Si el registro ya existe, actualiza solo los campos proporcionados.
    Si no existe, lo inserta.
    """
    expires_at = int(time.time() + expires_in) if expires_in else None

    with conn.cursor() as cur:
        # Verificar si existe
        cur.execute(
            "SELECT 1 FROM oauth_tokens WHERE provider = %s AND account = %s",
            (provider, account)
        )
        exists = cur.fetchone() is not None

        if not exists:
            # Insertar nuevo registro
            cur.execute("""
                INSERT INTO oauth_tokens (provider, account, access_token, refresh_token, expires_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, EXTRACT(EPOCH FROM NOW())::BIGINT)
            """, (provider, account, access_token, refresh_token, expires_at))
            print(f"   ✅ Insertado {provider}/{account}")
        else:
            # Construir UPDATE dinámico
            set_clauses = []
            params = []
            if access_token is not None:
                set_clauses.append("access_token = %s")
                params.append(access_token)
            if refresh_token is not None:
                set_clauses.append("refresh_token = %s")
                params.append(refresh_token)
            if expires_in is not None:
                set_clauses.append("expires_at = EXTRACT(EPOCH FROM NOW())::BIGINT + %s")
                params.append(expires_in)
            if not set_clauses:
                print(f"   ⏭ No hay cambios para {provider}/{account}")
                return

            set_clauses.append("updated_at = EXTRACT(EPOCH FROM NOW())::BIGINT")
            params.extend([provider, account])

            query = f"""
                UPDATE oauth_tokens
                SET {', '.join(set_clauses)}
                WHERE provider = %s AND account = %s
            """
            cur.execute(query, params)
            print(f"   ✅ Actualizado {provider}/{account}")


def upsert_config(conn, key: str, value):
    """Guarda un valor en la tabla bot_config."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO bot_config (config_key, config_value, updated_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (config_key) DO UPDATE SET
                config_value = EXCLUDED.config_value,
                updated_at = EXCLUDED.updated_at
        """, (key, json.dumps(value)))
        conn.commit()


# ============================================================
# 4. MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Sincroniza tokens del .env a PostgreSQL."
    )
    parser.add_argument(
        "--db-url",
        help="URL de la base de datos (ej: postgresql://user:pass@host/db)",
        default=None
    )
    parser.add_argument(
        "--env-file",
        help="Ruta al archivo .env (por defecto: .env)",
        default=".env"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra lo que se va a hacer sin ejecutar cambios"
    )
    args = parser.parse_args()

    # Cargar .env
    env = load_env(args.env_file)

    # Obtener DATABASE_URL
    db_url = args.db_url or env.get("DATABASE_URL")
    if not db_url:
        print("❌ No se encontró DATABASE_URL en el .env ni se proporcionó como argumento.")
        sys.exit(1)

    # Definir los tokens a sincronizar
    # El token de moderador usará los mismos valores que broadcaster
    broadcaster_token = env.get("BROADCASTER_TOKEN", "")
    broadcaster_refresh = env.get("BROADCASTER_REFRESH_TOKEN", "")

    tokens = [
        {
            "provider": "twitch",
            "account": "bot",
            "access_token": env.get("BOT_TOKEN"),
            "refresh_token": env.get("BOT_REFRESH_TOKEN"),
            "expires_in": 14400  # 4 horas
        },
        {
            "provider": "twitch",
            "account": "broadcaster",
            "access_token": broadcaster_token,
            "refresh_token": broadcaster_refresh,
            "expires_in": 14400
        },
        {
            "provider": "twitch",
            "account": "app",
            "access_token": env.get("APP_ACCESS_TOKEN"),
            "refresh_token": None,
            "expires_in": 5184000  # 60 días
        },
        {
            "provider": "twitch",
            "account": "moderator",
            "access_token": broadcaster_token,  # Mismo que broadcaster
            "refresh_token": broadcaster_refresh,
            "expires_in": 14400
        },
        {
            "provider": "spotify",
            "account": "default",
            "access_token": None,  # No se guarda en settings, pero por si acaso
            "refresh_token": env.get("SPOTIFY_REFRESH_TOKEN"),
            "expires_in": 3600  # 1 hora (para el access_token, aunque no lo usamos)
        }
    ]

    # Mostrar resumen
    print("\n" + "="*60)
    print("🔄 SINCRONIZACIÓN DE TOKENS A POSTGRESQL")
    print("="*60)
    print(f"📁 Archivo .env: {args.env_file}")
    print(f"🗄️  Base de datos: {db_url.split('@')[-1] if '@' in db_url else db_url}")
    print("\n📋 Tokens a sincronizar:")
    for t in tokens:
        provider = t["provider"].ljust(12)
        account = t["account"].ljust(14)
        access = "✅" if t["access_token"] else "❌"
        refresh = "✅" if t["refresh_token"] else "❌"
        print(f"   {provider} / {account}  | Access: {access}  Refresh: {refresh}")
    print("="*60)

    if args.dry_run:
        print("🔍 Modo dry-run activado. No se ejecutarán cambios.")
        return

    confirm = input("❓ ¿Sincronizar estos tokens con la base de datos? (s/N): ").strip().lower()
    if confirm not in ("s", "si", "y", "yes"):
        print("⏹ Operación cancelada.")
        return

    # Conectar y sincronizar
    conn = get_db_connection(db_url)
    try:
        ensure_tables(conn)
        for t in tokens:
            upsert_token(
                conn,
                provider=t["provider"],
                account=t["account"],
                access_token=t["access_token"],
                refresh_token=t["refresh_token"],
                expires_in=t["expires_in"]
            )

        # Guardar MODERATOR_USER_ID en bot_config
        moderator_user_id = env.get("MODERATOR_USER_ID", env.get("BROADCASTER_ID", ""))
        if moderator_user_id:
            upsert_config(conn, "moderator_user_id", moderator_user_id)
            print(f"   ✅ Guardado MODERATOR_USER_ID = {moderator_user_id} en bot_config")

        conn.commit()
        print("\n✅ ¡Todos los tokens fueron sincronizados correctamente!")
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error durante la sincronización: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()