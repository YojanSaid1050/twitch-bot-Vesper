import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

def get_db_connection():
    # Si no está en el entorno, intentar cargar desde .env
    if not os.environ.get("DATABASE_URL"):
        load_dotenv()
    
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL no configurada en variables de entorno")
    
    return psycopg2.connect(database_url)

def init_db():
    with get_db_connection() as conn:
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
            # Tabla bot_config
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bot_config (
                    id SERIAL PRIMARY KEY,
                    config_key TEXT NOT NULL UNIQUE,
                    config_value JSONB NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        conn.commit()
        print("✅ Tablas creadas/verificadas correctamente")

# Inicializar al importar
try:
    init_db()
except Exception as e:
    print(f"⚠️ No se pudo inicializar la base de datos PostgreSQL: {e}")