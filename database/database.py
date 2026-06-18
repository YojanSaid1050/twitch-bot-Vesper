import os
import psycopg2
import psycopg2.extras

def get_db_connection():
    """
    Retorna una conexión a PostgreSQL usando DATABASE_URL.
    """
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL no configurada en variables de entorno")
    conn = psycopg2.connect(database_url)
    return conn

def init_db():
    """Crea la tabla oauth_tokens si no existe."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
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
        conn.commit()

# Inicializar al importar (si DATABASE_URL está configurada)
try:
    init_db()
except Exception as e:
    print(f"⚠️ No se pudo inicializar la base de datos PostgreSQL: {e}")