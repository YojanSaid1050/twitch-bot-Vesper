#!/usr/bin/env python3
"""
Twitch Bot - Punto de entrada principal
Inicia el bot y el dashboard en el mismo proceso
"""

import sys
import signal
import threading
import time
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from bot.client import Bot
from web.dashboard import run_dashboard, set_bot_instance, wait_for_tokens
from utils.logger import setup_logger
from services.token_manager import token_manager
from services.config_service import config_service
from services.log_service import log_service

logger = setup_logger()


def signal_handler(sig, frame):
    """Manejar señales de cierre (Ctrl+C)"""
    logger.info("🛑 Recibida señal de cierre...")
    log_service.add_log('info', 'Señal de cierre recibida (Ctrl+C)', 'main')
    try:
        token_manager.stop_auto_refresh()
    except:
        pass
    sys.exit(0)


def start_dashboard():
    """Iniciar el dashboard después de que el bot esté listo y los tokens sean válidos"""
    max_wait = 60
    waited = 0
    
    # Esperar a que el bot esté inicializado
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
    """Punto de entrada principal"""
    global bot_instance
    
    # Configurar manejadores de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("🕯️ Iniciando VesperBot...")
    log_service.add_log('info', 'Iniciando VesperBot...', 'main')

    # ===== NUEVO: CREAR Y CONFIGURAR EL EVENT LOOP =====
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # Si no hay loop, crear uno nuevo
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Iniciar dashboard en hilo separado
    dashboard_thread = threading.Thread(target=start_dashboard, daemon=True)
    dashboard_thread.start()

    try:
        # Crear y ejecutar el bot
        bot = Bot()
        bot_instance = bot
        set_bot_instance(bot)
        log_service.add_log('info', 'Bot creado y registrado en el dashboard', 'main')
        
        # Ejecutar el bot (bloquea hasta que termine)
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


if __name__ == "__main__":
    main()