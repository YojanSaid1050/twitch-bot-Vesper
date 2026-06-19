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

sys.path.insert(0, str(Path(__file__).parent))

from bot.client import Bot
from web.dashboard import run_dashboard, set_bot_instance, wait_for_tokens
from utils.logger import setup_logger
from services.token_manager import token_manager
from services.config_service import config_service
from services.log_service import log_service
from config import settings  # <--- IMPORTAR SETTINGS

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

    # ===== USAR SETTINGS EN VEZ DE CONFIG_SERVICE =====
    logger.info(f"📺 Canal: {settings.CHANNEL}")
    logger.info(f"🤖 Bot: {settings.BOT_NICK}")

    dashboard_thread = threading.Thread(target=start_dashboard, daemon=True)
    dashboard_thread.start()

    try:
        bot = Bot()
        bot_instance = bot
        set_bot_instance(bot)
        log_service.add_log('info', 'Bot creado y registrado en el dashboard', 'main')

        # SEPARADOR ANTES DE CONEXIÓN
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