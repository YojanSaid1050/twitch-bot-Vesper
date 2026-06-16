"""
Manejador de base de datos SQLite
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

from utils.logger import get_logger

logger = get_logger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "bot_data.db"


class DatabaseManager:
    """Manejador de base de datos"""
    
    def __init__(self):
        self.db_path = DB_PATH
        self._init_db()
    
    def _init_db(self):
        """Inicializar tablas"""
        DB_PATH.parent.mkdir(exist_ok=True)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabla de comandos personalizados
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS custom_commands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command_name TEXT NOT NULL,
                    response TEXT NOT NULL,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    cooldown INTEGER DEFAULT 0,
                    UNIQUE(command_name)
                )
            """)
            
            # Tabla de advertencias
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS warnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    user_name TEXT NOT NULL,
                    reason TEXT,
                    warned_by TEXT,
                    warned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(id)
                )
            """)
            
            # Tabla de enlaces sociales
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS social_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL UNIQUE,
                    url TEXT NOT NULL
                )
            """)
            
            # Insertar enlaces por defecto
            default_links = [
                ("discord", "https://discord.gg/invite"),
                ("twitter", "https://twitter.com/"),
                ("instagram", "https://instagram.com/"),
                ("youtube", "https://youtube.com/"),
                ("tiktok", "https://tiktok.com/@")
            ]
            
            for platform, default_url in default_links:
                cursor.execute("""
                    INSERT OR IGNORE INTO social_links (platform, url)
                    VALUES (?, ?)
                """, (platform, default_url))
            
            conn.commit()
            logger.info("✅ Base de datos inicializada")
    
    @contextmanager
    def _get_connection(self):
        """Context manager para conexiones"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    # ========== COMANDOS PERSONALIZADOS ==========
    
    def add_command(self, name: str, response: str, created_by: str = "system", cooldown: int = 0) -> bool:
        """Agregar comando personalizado"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO custom_commands (command_name, response, created_by, cooldown)
                    VALUES (?, ?, ?, ?)
                """, (name.lower(), response, created_by, cooldown))
                conn.commit()
                logger.info(f"Comando personalizado agregado: {name}")
                return True
        except sqlite3.IntegrityError:
            return False
    
    def get_command(self, name: str) -> Optional[Dict]:
        """Obtener comando personalizado"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM custom_commands WHERE command_name = ?", (name.lower(),))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_all_commands(self) -> List[Dict]:
        """Obtener todos los comandos personalizados"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT command_name FROM custom_commands ORDER BY command_name")
            return [dict(row) for row in cursor.fetchall()]
    
    def remove_command(self, name: str) -> bool:
        """Eliminar comando personalizado"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM custom_commands WHERE command_name = ?", (name.lower(),))
            conn.commit()
            return cursor.rowcount > 0
    
    # ========== SISTEMA DE ADVERTENCIAS ==========
    
    def add_warning(self, user_id: str, user_name: str, reason: str, warned_by: str) -> int:
        """Agregar advertencia"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO warnings (user_id, user_name, reason, warned_by)
                VALUES (?, ?, ?, ?)
            """, (user_id, user_name, reason, warned_by))
            conn.commit()
            return cursor.lastrowid
    
    def get_warnings(self, user_id: str) -> List[Dict]:
        """Obtener advertencias de un usuario"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM warnings WHERE user_id = ? ORDER BY warned_at DESC
            """, (user_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def clear_warnings(self, user_id: str) -> int:
        """Limpiar advertencias de un usuario"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM warnings WHERE user_id = ?", (user_id,))
            conn.commit()
            return cursor.rowcount
    
    # ========== ENLACES SOCIALES ==========
    
    def get_social_link(self, platform: str) -> Optional[str]:
        """Obtener enlace social"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT url FROM social_links WHERE platform = ?", (platform.lower(),))
            row = cursor.fetchone()
            return row["url"] if row else None
    
    def set_social_link(self, platform: str, url: str) -> bool:
        """Actualizar enlace social"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO social_links (platform, url)
                VALUES (?, ?)
            """, (platform.lower(), url))
            conn.commit()
            return True


# Instancia global
db = DatabaseManager()