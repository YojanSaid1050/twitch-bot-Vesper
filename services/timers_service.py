"""
Timers: mensajes automáticos periódicos (estilo Nightbot).

Un timer se envía cuando se cumplen TODAS estas condiciones:
  - está activado,
  - han pasado al menos `interval` minutos desde su último envío,
  - han llegado al menos `min_lines` mensajes al chat desde su último envío
    (evita que el bot hable solo en un chat muerto),
  - el directo está en vivo.

Los timers se guardan en la configuración (clave "timers") y se gestionan con
el comando !timer.
"""

import asyncio
import time
from typing import Dict, Optional

from services.config_service import config_service
from services.log_service import log_service
from utils.command_vars import sanitize_output
from utils.logger import get_logger

logger = get_logger(__name__)

CHECK_INTERVAL_SECONDS = 30
LIVE_CACHE_SECONDS = 120


class TimersService:
    def __init__(self):
        self._channel = None
        self._task: Optional[asyncio.Task] = None
        self._lines_total = 0
        # nombre -> (instante del último envío, líneas totales en ese momento)
        self._last_sent: Dict[str, tuple] = {}
        self._live_cache = (0.0, False)

    def on_chat_line(self) -> None:
        self._lines_total += 1

    def start(self, channel) -> None:
        self._channel = channel
        if self._task and not self._task.done():
            return
        now = time.monotonic()
        # Los timers no saltan nada más arrancar: cuentan desde ahora
        for name in config_service.get_timers():
            self._last_sent.setdefault(name, (now, self._lines_total))
        self._task = asyncio.get_running_loop().create_task(self._run())
        logger.info("⏲️ Servicio de timers iniciado")

    def stop(self) -> None:
        if self._task:
            self._task.cancel()
            self._task = None

    def reset_timer(self, name: str) -> None:
        self._last_sent[name] = (time.monotonic(), self._lines_total)

    async def _is_live(self) -> bool:
        checked_at, live = self._live_cache
        if time.monotonic() - checked_at < LIVE_CACHE_SECONDS:
            return live
        try:
            from services.stats_service import stats_service
            live = bool(await stats_service.get_stream_info())
        except Exception as e:
            logger.debug(f"No se pudo comprobar si el directo está activo: {e}")
            live = False
        self._live_cache = (time.monotonic(), live)
        return live

    def due_timers(self, now: float) -> list:
        """Nombres de timers listos para enviarse (sin comprobar si hay directo)."""
        due = []
        for name, timer in config_service.get_timers().items():
            if not timer.get("enabled", True):
                continue
            last_time, last_lines = self._last_sent.setdefault(name, (now, self._lines_total))
            interval_ok = now - last_time >= int(timer.get("interval", 15)) * 60
            lines_ok = self._lines_total - last_lines >= int(timer.get("min_lines", 5))
            if interval_ok and lines_ok:
                due.append(name)
        return due

    async def _run(self) -> None:
        while True:
            try:
                await asyncio.sleep(CHECK_INTERVAL_SECONDS)
                if not self._channel:
                    continue
                due = self.due_timers(time.monotonic())
                if not due or not await self._is_live():
                    continue
                # Como mucho un timer por vuelta para no inundar el chat
                name = due[0]
                timer = config_service.get_timers().get(name)
                if not timer:
                    continue
                await self._channel.send(sanitize_output(timer.get("message", "")))
                self.reset_timer(name)
                log_service.add_log('info', f'Timer "{name}" enviado', 'bot')
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error en el servicio de timers: {e}")
                log_service.add_log('error', f'Error en timers: {e}', 'bot')


timers_service = TimersService()
