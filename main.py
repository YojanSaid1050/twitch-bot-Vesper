#!/usr/bin/env python3
"""
Twitch Bot - Punto de entrada principal
Inicia el bot y el dashboard en el mismo proceso
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# ===== CARGAR VARIABLES DE ENTORNO ANTES DE CUALQUIER OTRA COSA =====
load_dotenv()

# Ahora el resto de importaciones
import signal
import threading
import time
import asyncio
import requests  # Añadido para verificar webhook

sys.path.insert(0, str(Path(__file__).parent))

from bot.client import Bot
from web.dashboard import run_dashboard, set_bot_instance, wait_for_tokens
from utils.logger import setup_logger
from services.token_manager import token_manager
from services.log_service import log_service
from services.eventsub_service import eventsub_service
from config import settings

logger = setup_logger()


def signal_handler(sig, frame):
    logger.info("🛑 Recibida señal de cierre...")
    log_service.add_log('info', 'Señal de cierre recibida (Ctrl+C)', 'main')
    try:
        token_manager.stop_auto_refresh()
    except:
        pass
    sys.exit(0)


def start_dashboard():
    """Inicia el dashboard en un hilo separado."""
    max_wait = 60
    waited = 0
    while not hasattr(sys.modules['__main__'], 'bot_instance') and waited < max_wait:
        time.sleep(1)
        waited += 1
    if waited >= max_wait:
        logger.warning("⚠️ Dashboard iniciado sin esperar al bot (timeout)")
        log_service.add_log('warning', 'Dashboard iniciado sin esperar al bot (timeout)', 'main')
    else:
        logger.info("✅ Bot listo, esperando tokens válidos...")
        wait_for_tokens(timeout=60)
        logger.info("🚀 Iniciando dashboard...")
        log_service.add_log('info', 'Bot listo, iniciando dashboard', 'main')
    try:
        run_dashboard()
    except Exception as e:
        logger.error(f"❌ Error en dashboard: {e}")
        log_service.add_log('critical', f'Error en dashboard: {e}', 'main')


def main():
    global bot_instance

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # BANNER INICIAL
    print("\n" + "=" * 60)
    print("🕯️  VESPERBOT - RELICARIO DEL VACÍO")
    print("=" * 60)
    print("🐍 Iniciando el ritual...")
    print("=" * 60 + "\n")

    logger.info("🕯️ Iniciando VesperBot...")
    log_service.add_log('info', 'Iniciando VesperBot...', 'main')

    # Crear event loop
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        logger.info("✅ Event loop creado y establecido para el hilo principal")
        log_service.add_log('info', 'Event loop creado para el hilo principal', 'main')

    logger.info(f"📺 Canal: {settings.CHANNEL}")
    logger.info(f"🤖 Bot: {settings.BOT_NICK}")

    # ===== INICIAR DASHBOARD (CONTINE EL WEBHOOK) =====
    dashboard_thread = threading.Thread(target=start_dashboard, daemon=True)
    dashboard_thread.start()

    # Esperar a que el dashboard esté listo (más robusto)
    logger.info("⏳ Esperando que el dashboard (webhook) esté listo...")
    webhook_ready = False
    port = os.getenv("PORT", "10000")
    for attempt in range(1, 31):  # hasta 30 intentos (30 segundos)
        try:
            url = f"http://localhost:{port}/webhook/twitch"
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                webhook_ready = True
                logger.info("✅ Webhook está activo")
                break
        except:
            pass
        time.sleep(1)
        if attempt % 5 == 0:
            logger.info(f"⏳ Intentando conectar al webhook... ({attempt}s)")

    if not webhook_ready:
        logger.warning("⚠️ Webhook no disponible después de 30s, continuando de todos modos...")

    # ===== CREAR Y EJECUTAR EL BOT =====
    try:
        bot = Bot()
        bot_instance = bot
        set_bot_instance(bot)
        log_service.add_log('info', 'Bot creado y registrado en el dashboard', 'main')

        logger.info("=" * 60)
        logger.info("🔮 Conectando al canal de Twitch...")
        logger.info("=" * 60)

        bot.run()

    except KeyboardInterrupt:
        logger.info("⏹️ Bot detenido por el usuario")
        log_service.add_log('info', 'Bot detenido por el usuario', 'main')
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
        log_service.add_log('critical', f'Error fatal al iniciar el bot: {e}', 'main')
        sys.exit(1)
    finally:
        try:
            token_manager.stop_auto_refresh()
        except:
            pass

        print("\n" + "=" * 60)
        print("🕯️  El relicario se ha apagado...")
        print("=" * 60 + "\n")


if __name__ == "__main__":
    main()