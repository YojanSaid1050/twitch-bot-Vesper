import json
from typing import Dict, Any
import psycopg2.extras
from .database import get_db_connection

class ConfigRepository:
    @staticmethod
    def get_config() -> Dict[str, Any]:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT config_value FROM bot_config WHERE config_key = 'main'")
                row = cur.fetchone()
                return row['config_value'] if row else {}

    @staticmethod
    def save_config(config: Dict[str, Any]):
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO bot_config (config_key, config_value, updated_at)
                    VALUES ('main', %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (config_key) DO UPDATE SET
                        config_value = EXCLUDED.config_value,
                        updated_at = EXCLUDED.updated_at
                """, (json.dumps(config),))
            conn.commit()