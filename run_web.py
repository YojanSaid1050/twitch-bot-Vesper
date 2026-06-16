#!/usr/bin/env python3
"""
Ejecutar servidor EventSub localmente
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from web.app import app

if __name__ == "__main__":
    print("🚀 Iniciando servidor EventSub local...")
    app.run(host='0.0.0.0', port=5001, debug=True)