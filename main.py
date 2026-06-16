#!/usr/bin/env python3
"""
Twitch Bot - Punto de entrada principal
"""

import sys
import signal
from pathlib import Path

# Agregar el directorio actual al path para imports relativos
sys.path.insert(0, str(Path(__file__).parent))

from bot.client import Bot
from utils.logger import setup_logger
from services.token_manager import token_manager


logger = setup_logger()


def signal_handler(sig, frame):
    """Manejar señal de cierre"""
    logger.info("🛑 Recibida señal de cierre...")
    try:
        token_manager.stop_auto_refresh()
    except:
        pass
    sys.exit(0)


def main():
    """Punto de entrada principal"""
    # Configurar manejador de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("🕯️ Iniciando el bot...")
    
    try:
        # Crear y ejecutar el bot
        bot = Bot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("⏹️ Bot detenido por el usuario")
        try:
            token_manager.stop_auto_refresh()
        except:
            pass
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
        try:
            token_manager.stop_auto_refresh()
        except:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()