import time
import psycopg2.extras
from typing import Optional, Dict, List
from .database import get_db_connection

class TokenRepository:
    """Repositorio para operaciones CRUD de tokens OAuth en PostgreSQL."""

    @staticmethod
    def get_token(provider: str, account: str) -> Optional[Dict]:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(
                    "SELECT provider, account, access_token, refresh_token, expires_at, updated_at FROM oauth_tokens WHERE provider = %s AND account = %s",
                    (provider, account)
                )
                row = cur.fetchone()
                return dict(row) if row else None

    @staticmethod
    def save_token(provider: str, account: str, access_token: str, refresh_token: Optional[str] = None, expires_in: Optional[int] = None):
        expires_at = int(time.time() + expires_in) if expires_in else None
        with get_db_connection() as conn:
            with conn.cursor() as cur:
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

    @staticmethod
    def update_access_token(provider: str, account: str, access_token: str, expires_in: int):
        expires_at = int(time.time() + expires_in)
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE oauth_tokens SET access_token = %s, expires_at = %s, updated_at = EXTRACT(EPOCH FROM NOW())::BIGINT WHERE provider = %s AND account = %s",
                    (access_token, expires_at, provider, account)
                )
            conn.commit()

    @staticmethod
    def update_refresh_token(provider: str, account: str, refresh_token: str):
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE oauth_tokens SET refresh_token = %s, updated_at = EXTRACT(EPOCH FROM NOW())::BIGINT WHERE provider = %s AND account = %s",
                    (refresh_token, provider, account)
                )
            conn.commit()

    @staticmethod
    def delete_token(provider: str, account: str):
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM oauth_tokens WHERE provider = %s AND account = %s",
                    (provider, account)
                )
            conn.commit()

    @staticmethod
    def token_exists(provider: str, account: str) -> bool:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM oauth_tokens WHERE provider = %s AND account = %s",
                    (provider, account)
                )
                return cur.fetchone() is not None

    @staticmethod
    def get_all_tokens() -> List[Dict]:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT provider, account, access_token, refresh_token, expires_at, updated_at FROM oauth_tokens")
                rows = cur.fetchall()
                return [dict(row) for row in rows]