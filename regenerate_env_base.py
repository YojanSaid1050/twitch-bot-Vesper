#!/usr/bin/env python3
"""
Regenerador completo del archivo .env
- Escribe todas las variables fijas (CLIENT_ID, SECRET, IDs, Spotify, EventSub, etc.)
- Luego ejecuta generate_tokens_manual.py para obtener nuevos tokens del bot y streamer
"""

import os
import sys
import subprocess
from pathlib import Path

# ============================================
# VALORES FIJOS (NO CAMBIAN)
# ============================================
ENV_CONTENT = """# Tokens actualizados con TODOS los scopes
BOT_NICK=VesperBotx
CHANNEL=xyojansaidx

# ============================================
# TOKEN DEL BOT (VesperBotx) - ESCRITURA
# ============================================
BOT_TOKEN=pendiente
BOT_REFRESH_TOKEN=pendiente

# ============================================
# TOKEN DEL STREAMER (xyojansaidx) - LECTURA
# ============================================
BROADCASTER_TOKEN=pendiente
BROADCASTER_REFRESH_TOKEN=pendiente

# ============================================
# CREDENCIALES DE LA APLICACIÓN
# ============================================
CLIENT_ID=rbh1xnq6nyre67hz3q8btq7id6n1r1
CLIENT_SECRET=90zk3l5khv8wrua0zaf59vlumwym79

# ============================================
# IDs (estos NO cambian)
# ============================================
BROADCASTER_ID=472904893
BOT_ID=1512887346

# ============================================
# SPOTIFY
# ============================================
SPOTIFY_CLIENT_ID=d1a7b6987ad1426fb9207befa71cb3cc
SPOTIFY_CLIENT_SECRET=9133217abbd44349a225cf1b63751134

# ============================================
# EVENTSUB
# ============================================
EVENTSUB_CALLBACK_URL=https://twitch-bot-vesper.onrender.com
TWITCH_WEBHOOK_SECRET=e7f497ce2605392f02feef41368d6de30317908e922ddefd21f3acaf34f902c3
BOT_WEBHOOK_PORT=5001
BOT_WEBHOOK_URL=http://localhost:5001/webhook

APP_ACCESS_TOKEN=6aw5xrvihw6cxnfz736mctsu7danu5
"""

ENV_PATH = Path(__file__).parent / ".env"


def main():
    print("=" * 60)
    print("🔄 REGENERADOR COMPLETO DEL ARCHIVO .env")
    print("=" * 60)
    
    # 1. Escribir el .env base
    print("📝 Escribiendo archivo .env con valores fijos...")
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write(ENV_CONTENT)
    print("✅ Archivo .env creado con valores fijos.")
    
    # 2. Ejecutar el generador de tokens para obtener los tokens del bot y streamer
    print("\n🔑 Ahora ejecutaremos el generador de tokens para obtener los tokens del bot y streamer.")
    print("   - El streamer se abrirá en Brave (opción 1 o 3).")
    print("   - El bot se abrirá en Chrome (opción 2 o 3).")
    print("   Sigue las instrucciones en pantalla.\n")
    
    generator_script = Path(__file__).parent / "generate_tokens_manual.py"
    
    if not generator_script.exists():
        print("❌ No se encontró generate_tokens_manual.py en el directorio actual.")
        print("   Asegúrate de que el script esté presente.")
        sys.exit(1)
    
    # Ejecutar el generador
    try:
        subprocess.run([sys.executable, str(generator_script)], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al ejecutar el generador: {e}")
        sys.exit(1)
    
    print("\n✅ Proceso completado. El archivo .env ahora tiene todos los tokens actualizados.")
    print("👉 Reinicia el bot para que los nuevos tokens tomen efecto.")


if __name__ == "__main__":
    main()