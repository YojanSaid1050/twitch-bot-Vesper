import os
import threading
from pathlib import Path
from typing import Optional

class EnvManager:
    _lock = threading.Lock()
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.env_path = Path(__file__).parent.parent / ".env"
        self._initialized = True

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        if not self.env_path.exists():
            return default
        with open(self.env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                k, _, v = line.partition("=")
                if k == key:
                    return v
        return default

    def set(self, key: str, value: str) -> bool:
        # Este método ya no se usa para tokens, pero se mantiene por si acaso
        with self._lock:
            lines = []
            if self.env_path.exists():
                with open(self.env_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            updated = False
            for i, line in enumerate(lines):
                if line.startswith(f"{key}="):
                    lines[i] = f"{key}={value}\n"
                    updated = True
                    break
            if not updated:
                lines.append(f"{key}={value}\n")
            tmp_path = self.env_path.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self.env_path)
            return True

    def reload(self) -> dict:
        env_vars = {}
        if not self.env_path.exists():
            return env_vars
        with open(self.env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                k, _, v = line.partition("=")
                env_vars[k] = v
        return env_vars

env_manager = EnvManager()