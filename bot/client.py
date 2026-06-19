# bot/client.py
"""
Cliente principal del bot
"""

import asyncio
from twitchio.ext import commands

from config import settings
from bot.events import EventHandler
from bot.permissions import permission_checker
from services.token_manager import token_manager
from services.config_service import config_service
from services.chat_settings import ChatSettings
from security.anti_spam import anti_spam
from utils.logger import get_logger
from services.log_service import log_service

logger = get_logger(__name__)
chat_settings = ChatSettings()


class Bot(commands.Bot):

    def __init__(self):
        # ===== SEPARADOR =====
        logger.info("=" * 50)
        logger.info("🕯️ INICIALIZANDO RELICARIO")
        logger.info("=" * 50)
        log_service.add_log('info', 'Inicializando el relicario...', 'bot')

        token_manager.start_auto_refresh()

        super().__init__(
            token=settings.BOT_TOKEN,
            prefix="!",
            initial_channels=[settings.CHANNEL]
        )

        self.channel_name = settings.CHANNEL
        self.event_handler = EventHandler(self)

        # Registrar comandos
        from commands import register_commands
        register_commands(self)

        # Inicializar servicios de EventSub y notificaciones (sin suscribir aún)
        self._init_eventsub_services()

        # Cargar comandos personalizados iniciales
        self._load_custom_commands()

        # Registrar callback para cambios en config_service
        config_service.on_change(self._on_config_change)

        logger.info("✅ Relicario despertado correctamente")
        log_service.add_log('info', 'Relicario despertado correctamente', 'bot')

    def _load_custom_commands(self):
        custom_commands = config_service.get_custom_commands()
        logger.info(f"📜 Ecos personalizados cargados: {len(custom_commands)}")
        for name, data in custom_commands.items():
            logger.info(f"   !{name} -> {data.get('response', '')[:30]}...")

    def _on_config_change(self):
        """Callback cuando cambia la configuración"""
        try:
            custom_commands = config_service.get_custom_commands()
            logger.info(f"🔄 Configuración actualizada: {len(custom_commands)} ecos")
            try:
                from commands.custom import refresh_cache
                refresh_cache()
            except Exception as e:
                logger.error(f"Error recargando caché de ecos: {e}")
                log_service.add_log('error', f'Error recargando caché de ecos: {e}', 'bot')

            try:
                anti_spam.reload_banned_words()
                logger.info(f"🔄 Palabras prohibidas recargadas: {len(anti_spam.banned_words)}")
            except Exception as e:
                logger.error(f"Error recargando palabras prohibidas: {e}")
                log_service.add_log('error', f'Error recargando palabras prohibidas: {e}', 'bot')

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.apply_chat_settings())
            except RuntimeError:
                logger.warning("⚠️ No hay event loop, ejecutando apply_chat_settings de forma síncrona")
                log_service.add_log('warning', 'No hay event loop, ejecutando apply_chat_settings de forma síncrona', 'bot')
                try:
                    asyncio.run(self.apply_chat_settings())
                except Exception as e:
                    logger.error(f"Error en fallback de apply_chat_settings: {e}")
                    log_service.add_log('error', f'Error en fallback de apply_chat_settings: {e}', 'bot')
        except Exception as e:
            logger.error(f"Error en _on_config_change: {e}")
            log_service.add_log('error', f'Error en _on_config_change: {e}', 'bot')

    async def apply_chat_settings(self):
        try:
            slow_mode = config_service.get_slow_mode()
            if slow_mode.get('enabled', False):
                await chat_settings.set_slow_mode(True, slow_mode.get('seconds', 10))
                logger.info(f"⏳ Modo lento activado: {slow_mode.get('seconds', 10)}s")
                log_service.add_log('info', f'Modo lento activado: {slow_mode.get("seconds", 10)}s', 'bot')
            else:
                await chat_settings.set_slow_mode(False)
                logger.info("⏳ Modo lento desactivado")
                log_service.add_log('info', 'Modo lento desactivado', 'bot')

            follower_mode = config_service.get_follower_mode()
            if follower_mode.get('enabled', False):
                await chat_settings.set_follower_mode(True, follower_mode.get('minutes', 10))
                logger.info(f"🚪 Modo seguidores activado: {follower_mode.get('minutes', 10)}m")
                log_service.add_log('info', f'Modo seguidores activado: {follower_mode.get("minutes", 10)}m', 'bot')
            else:
                await chat_settings.set_follower_mode(False)
                logger.info("🚪 Modo seguidores desactivado")
                log_service.add_log('info', 'Modo seguidores desactivado', 'bot')

            emote_mode = config_service.get_emote_mode()
            await chat_settings.set_emote_mode(emote_mode)
            logger.info(f"😶 Modo emotes: {'activado' if emote_mode else 'desactivado'}")
            log_service.add_log('info', f'Modo emotes: {"activado" if emote_mode else "desactivado"}', 'bot')

            subscriber_mode = config_service.get_subscriber_mode()
            await chat_settings.set_subscriber_mode(subscriber_mode)
            logger.info(f"👑 Modo suscriptores: {'activado' if subscriber_mode else 'desactivado'}")
            log_service.add_log('info', f'Modo suscriptores: {"activado" if subscriber_mode else "desactivado"}', 'bot')
        except Exception as e:
            logger.error(f"Error aplicando settings de chat: {e}")
            log_service.add_log('error', f'Error aplicando settings de chat: {e}', 'bot')

    def _init_eventsub_services(self):
        """
        Inicializa los servicios de EventSub y notificaciones,
        pero NO suscribe eventos aún (se hará en event_ready).
        """
        try:
            from services.eventsub_service import eventsub_service
            from services.notification_service import notification_service

            # Vincular el bot a los servicios
            eventsub_service.set_bot(self)
            notification_service.set_bot(self)

            logger.info("🔗 Servicios de EventSub vinculados al bot")
            log_service.add_log('info', 'Servicios de EventSub vinculados al bot', 'bot')
        except ImportError as e:
            logger.warning(f"⚠️ Error cargando servicios de EventSub: {e}")
            log_service.add_log('warning', f'Error cargando servicios de EventSub: {e}', 'bot')
        except Exception as e:
            logger.error(f"❌ Error inicializando servicios de EventSub: {e}")
            log_service.add_log('error', f'Error inicializando servicios de EventSub: {e}', 'bot')

    async def _subscribe_eventsub(self):
        """
        Suscribe a los eventos de EventSub.
        Se llama después de que el bot esté conectado y el webhook esté activo.
        """
        try:
            from services.eventsub_service import eventsub_service

            if settings.EVENTSUB_CALLBACK_URL and settings.TWITCH_WEBHOOK_SECRET:
                logger.info("📡 Iniciando suscripción a EventSub...")
                log_service.add_log('info', 'Iniciando suscripción a EventSub', 'bot')
                eventsub_service.subscribe_to_events()
                logger.info("✅ EventSub configurado correctamente")
                log_service.add_log('info', 'EventSub configurado correctamente', 'bot')
            else:
                logger.warning("⚠️ EventSub no configurado (faltan URL o secret)")
                log_service.add_log('warning', 'EventSub no configurado (faltan URL o secret)', 'bot')
        except Exception as e:
            logger.error(f"❌ Error en suscripción EventSub: {e}")
            log_service.add_log('error', f'Error en suscripción EventSub: {e}', 'bot')

    async def start_follow_polling(self):
        try:
            from services.notification_service import notification_service
            await asyncio.sleep(3)
            if self.connected_channels:
                notification_service.channel = self.connected_channels[0]
                logger.info(f"📺 Canal: {notification_service.channel.name}")
            notification_service.start_follow_polling()
            logger.info("✅ Polling de follows iniciado")
            log_service.add_log('info', 'Polling de follows iniciado', 'bot')
        except Exception as e:
            logger.error(f"❌ Error iniciando polling: {e}")
            log_service.add_log('error', f'Error iniciando polling de follows: {e}', 'bot')

    async def event_ready(self):
        # ===== SEPARADOR =====
        logger.info("=" * 50)
        logger.info("🔮 CONECTADO AL CANAL")
        logger.info("=" * 50)

        # Ejecutar eventos de preparación
        await self.event_handler.on_ready()

        # Iniciar polling de follows
        await self.start_follow_polling()

        # Aplicar configuraciones del chat
        await self.apply_chat_settings()

        # ===== SUSCRIBIR A EVENTSUB AHORA QUE EL BOT ESTÁ CONECTADO =====
        await self._subscribe_eventsub()

        logger.info("=" * 50)
        logger.info("✅ RELICARIO LISTO PARA SERVIR")
        logger.info("=" * 50)

    async def event_message(self, message):
        await self.event_handler.on_message(message)

    async def event_command_error(self, context, error):
        await self.event_handler.on_command_error(context, error)

    async def event_subscription(self, channel, user, sub_type, sub_plan):
        await self.event_handler.event_subscription(channel, user, sub_type, sub_plan)

    async def event_subscription_gift(self, channel, user, recipient, sub_plan, sub_type):
        await self.event_handler.event_subscription_gift(channel, user, recipient, sub_plan, sub_type)

    async def event_resub(self, channel, user, months, sub_plan, message=None):
        await self.event_handler.event_resub(channel, user, months, sub_plan, message)

    async def event_raid(self, channel, user, viewers):
        await self.event_handler.event_raid(channel, user, viewers)

    async def event_host(self, channel, user, viewers):
        await self.event_handler.event_host(channel, user, viewers)

    def is_staff(self, ctx) -> bool:
        return permission_checker.is_staff(ctx.message)

    async def close(self):
        try:
            from services.eventsub_service import eventsub_service
            eventsub_service.stop()
        except:
            pass
        try:
            from services.notification_service import notification_service
            notification_service.stop_polling()
        except:
            pass
        token_manager.stop_auto_refresh()
        log_service.add_log('info', 'Bot cerrado correctamente', 'bot')
        await super().close()