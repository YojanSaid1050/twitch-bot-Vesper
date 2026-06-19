#!/usr/bin/env python3
"""
Twitch Bot - Punto de entrada principal
Inicia el servidor combinado (webhook + dashboard) y el bot
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# ===== CARGAR VARIABLES DE ENTORNO =====
load_dotenv()

import signal
import threading
import time
import asyncio
import requests
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from bot.client import Bot
from web.dashboard import app, set_bot_instance, wait_for_tokens
from web.webhook import set_bot_instance as set_webhook_bot
from utils.logger import setup_logger
from services.token_manager import token_manager
from services.log_service import log_service
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


def run_combined_server():
    """Inicia el servidor combinado (webhook + dashboard) en el puerto asignado."""
    port = int(os.getenv("PORT", "10000"))
    logger.info(f"🚀 Iniciando servidor combinado (webhook + dashboard) en el puerto {port}")
    app.config['START_TIME'] = datetime.now()
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)


def wait_for_server_ready(port=None, timeout=60, check_interval=1):
    """
    Espera a que el servidor combinado esté listo.
    
    Args:
        port: Puerto donde escucha el servidor
        timeout: Tiempo máximo de espera en segundos
        check_interval: Intervalo entre verificaciones
    
    Returns:
        bool: True si el servidor está listo
    """
    if port is None:
        port = int(os.getenv("PORT", "10000"))
    
    # Intentar primero con /health (disponible en dashboard)
    health_url = f"http://localhost:{port}/health"
    logger.info(f"⏳ Esperando que el servidor esté listo en {health_url}...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            resp = requests.get(health_url, timeout=2)
            if resp.status_code == 200:
                logger.info("✅ Servidor combinado listo (health check OK)")
                return True
        except:
            pass
        
        # Fallback: intentar con /twitch/webhook
        try:
            webhook_url = f"http://localhost:{port}/twitch/webhook"
            resp = requests.get(webhook_url, timeout=2)
            if resp.status_code == 200:
                logger.info("✅ Servidor combinado listo (webhook check OK)")
                return True
        except:
            pass
        
        time.sleep(check_interval)
    
    logger.warning(f"⚠️ Timeout esperando servidor después de {timeout}s")
    return False


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
        logger.info("✅ Event loop creado")
        log_service.add_log('info', 'Event loop creado', 'main')

    logger.info(f"📺 Canal: {settings.CHANNEL}")
    logger.info(f"🤖 Bot: {settings.BOT_NICK}")

    # ============================================================
    # 1. INICIAR SERVIDOR COMBINADO (webhook + dashboard)
    # ============================================================
    server_thread = threading.Thread(target=run_combined_server, daemon=True)
    server_thread.start()

    # ============================================================
    # 2. ESPERAR A QUE EL SERVIDOR ESTÉ LISTO
    # ============================================================
    # Pequeña pausa inicial para que el servidor tenga tiempo de arrancar
    time.sleep(2)
    
    if wait_for_server_ready(timeout=60):
        logger.info("✅ Servidor combinado activo")
        log_service.add_log('info', 'Servidor combinado activo', 'main')
    else:
        logger.warning("⚠️ Servidor no disponible, continuando de todos modos...")
        log_service.add_log('warning', 'Servidor no disponible, continuando', 'main')

    # ============================================================
    # 3. CREAR Y EJECUTAR EL BOT
    # ============================================================
    try:
        bot = Bot()
        bot_instance = bot
        set_bot_instance(bot)       # Dashboard
        set_webhook_bot(bot)        # Webhook
        log_service.add_log('info', 'Bot creado y registrado en dashboard y webhook', 'main')

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