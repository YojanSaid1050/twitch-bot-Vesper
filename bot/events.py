"""
Manejo de eventos del bot
"""

from twitchio import Message
from twitchio.ext import commands as twitch_commands
from utils.logger import get_logger
from bot.permissions import permission_checker
from security import anti_spam
from services.moderation_actions import ModerationActions
from services.notification_service import notification_service
from services.link_manager import link_manager
from services.warning_manager import warning_manager
from services.config_service import config_service
from services.timers_service import timers_service
from exceptions import ResourceNotFoundError, TwitchAPIError
from services.log_service import log_service

logger = get_logger(__name__)
mod_actions = ModerationActions()


class EventHandler:

    def __init__(self, bot):
        self.bot = bot
        notification_service.set_bot(bot)

    async def on_ready(self):
        logger.info(f"✅ Conectado como {self.bot.nick}")
        log_service.add_log('info', f'Bot conectado como {self.bot.nick}', 'bot')

        if hasattr(self.bot, 'channel_name'):
            logger.info(f"📺 Canal: {self.bot.channel_name}")
            channel = self.bot.get_channel(self.bot.channel_name)
        elif self.bot.connected_channels:
            channel = self.bot.connected_channels[0]
            logger.info(f"📺 Canal: {channel.name}")
        else:
            logger.info("📺 No hay canales conectados")
            log_service.add_log('warning', 'No hay canales conectados', 'bot')
            return

        if channel:
            timers_service.start(channel)
            # event_ready se dispara también en cada reconexión: saludar solo una vez
            if not getattr(self, '_greeted', False):
                self._greeted = True
                await channel.send("🕯️ El vigilante despierta... los ecos del vacío están a tu disposición.")
                log_service.add_log('info', f'Mensaje de bienvenida enviado a {channel.name}', 'bot')

    @staticmethod
    def _auto_timeout_seconds() -> int:
        """Duración del silencio automático configurada en el dashboard (minutos)."""
        try:
            minutes = int(config_service.get('moderation.auto_timeout_minutes', 10))
        except (TypeError, ValueError):
            minutes = 10
        return max(1, min(minutes, 20160)) * 60

    async def _punish(self, message: Message, action: str, reason: str, type_desc: str,
                      count: int, max_w: int, warning_text: str) -> None:
        """Aplica advertencia / timeout / ban temporal a un mensaje infractor."""
        name = message.author.name
        user_id = str(message.author.id)

        if action == 'warning':
            await message.channel.send(warning_text)
        elif action == 'timeout':
            seconds = self._auto_timeout_seconds()
            try:
                await mod_actions.timeout(name, seconds, reason, user_id=user_id)
                await message.channel.send(
                    f"🔇 {name} silenciado {seconds // 60} minutos por {type_desc} "
                    f"(advertencia {count}/{max_w})."
                )
                log_service.add_log('info', f'Timeout a {name} por {type_desc}', 'moderation')
            except Exception as e:
                logger.error(f"Error aplicando timeout: {e}")
                await message.channel.send(f"⚠️ Error al silenciar a {name}")
        elif action == 'ban':
            # Las sanciones automáticas son baneos temporales (14 días);
            # el baneo permanente queda reservado al comando manual !ban.
            try:
                await mod_actions.ban(name, reason, duration=link_manager.BAN_DURATION, user_id=user_id)
                await message.channel.send(
                    f"🔨 {name} desterrado 14 días por {type_desc} "
                    f"(advertencia {count}/{max_w})."
                )
                log_service.add_log('warning', f'Ban temporal a {name} por {type_desc}', 'moderation')
            except Exception as e:
                logger.error(f"Error aplicando ban: {e}")
                await message.channel.send(f"⚠️ Error al desterrar a {name}")

    async def on_message(self, message: Message):
        if message.echo:
            return

        timers_service.on_chat_line()

        # Verificar si es staff (mod o broadcaster)
        is_staff = permission_checker.is_staff(message)
        is_vip = bool(getattr(message.author, 'is_vip', False))
        max_w = warning_manager.get_max_warnings()

        # ========== ANTI-SPAM (palabras prohibidas, mayúsculas, flood) ==========
        if not is_staff:
            is_spam, action, warning_type, reason = anti_spam.check_message(
                str(message.author.id),
                message.content,
                is_vip=is_vip,
                is_staff=is_staff
            )

            if is_spam:
                logger.warning(f"🚫 Spam detectado de {message.author.name}: {reason}")
                log_service.add_log('warning', f'Spam detectado de {message.author.name}: {reason}', 'moderation')
                await mod_actions.delete_message(message.id)

                count = warning_manager.get_warning_count(str(message.author.id), warning_type)
                type_names = {
                    'caps': 'mayúsculas excesivas',
                    'rate': 'envío rápido de mensajes',
                    'repeat': 'mensajes repetidos',
                    'word': 'palabra prohibida'
                }
                type_desc = type_names.get(warning_type, warning_type)
                await self._punish(
                    message, action, f"Spam: {reason}", type_desc, count, max_w,
                    f"⚠️ {message.author.name}, el vacío detecta ecos no deseados. "
                    f"Advertencia {count}/{max_w} por {type_desc}."
                )
                return

        # ========== CONTROL DE ENLACES ==========
        if not is_staff and not is_vip:
            link_result = await link_manager.check_message(
                str(message.author.id),
                message.author.name,
                message.content,
                is_staff=is_staff,
                is_vip=is_vip
            )

            if link_result:
                action, reason, blocked_links = link_result
                count = warning_manager.get_warning_count(str(message.author.id), 'link')
                await mod_actions.delete_message(message.id)
                remaining = max(0, max_w - count)
                await self._punish(
                    message, action, reason, 'enlaces prohibidos', count, max_w,
                    f"⚠️ {message.author.name}, enlaces prohibidos. Advertencia {count}/{max_w}. "
                    f"Quedan {remaining} avisos antes del silencio. Pide a un mod un !permit."
                )
                # El mensaje se ha borrado: no ejecutar comandos que contuviera
                return

        # Procesar comandos
        await self.bot.handle_commands(message)

    async def on_command_error(self, context, error):
        from exceptions import PermissionDeniedError, TwitchAPIError, ValidationError

        if isinstance(error, twitch_commands.CommandNotFound):
            return

        error_msg = None
        command_name = context.command.name if context.command else "desconocido"

        if isinstance(error, PermissionDeniedError):
            error_msg = str(error)
            log_service.add_log('warning', f'Permiso denegado en comando !{command_name}: {error}', 'bot_commands')
        elif isinstance(error, ValidationError):
            error_msg = f"❌ {error}"
            log_service.add_log('warning', f'Error de validación en comando !{command_name}: {error}', 'bot_commands')
        elif isinstance(error, TwitchAPIError):
            logger.error(f"API Error en comando '{command_name}': {error}")
            error_msg = f"❌ El vacío no responde: {str(error)[:100]}"
            log_service.add_log('error', f'API Error en comando !{command_name}: {error}', 'twitch_api')
        else:
            logger.error(f"Error no manejado en comando '{command_name}': {error}")
            log_service.add_log('error', f'Error no manejado en comando !{command_name}: {error}', 'bot_commands')

        if error_msg and context.channel:
            await context.reply(error_msg)

    # Eventos de notificación (follows, subs, raids) → estadísticas
    async def event_follow(self, channel, user):
        logger.info(f"⭐ Nuevo follow de {user.name}")
        log_service.add_log('info', f'Nuevo follow de {user.name}', 'stats')
        await notification_service.on_follow(channel, user)

    async def event_subscription(self, channel, user, sub_type, sub_plan, months=None):
        logger.info(f"🎉 Nueva suscripción de {user.name} - {sub_plan}")
        log_service.add_log('info', f'Nueva suscripción de {user.name} - {sub_plan}', 'stats')
        await notification_service.on_subscribe(channel, user, sub_plan, sub_type)

    async def event_raid(self, channel, user, viewers):
        logger.info(f"⚔️ Raid entrante de {user.name} con {viewers} espectadores")
        log_service.add_log('info', f'Raid entrante de {user.name} con {viewers} espectadores', 'stats')
        await notification_service.on_raid(channel, user, viewers)

    async def event_raid_go(self, channel, target, viewers):
        logger.info(f"⚔️ Raid saliente a {target} con {viewers} espectadores")
        log_service.add_log('info', f'Raid saliente a {target} con {viewers} espectadores', 'stats')
        await notification_service.on_raid_go(channel, target, viewers)

    async def event_host(self, channel, user, viewers):
        logger.info(f"🏠 Host de {user.name} con {viewers} espectadores")
        log_service.add_log('info', f'Host de {user.name} con {viewers} espectadores', 'stats')
        await notification_service.on_host(channel, user, viewers)

    async def on_user_join(self, channel, user):
        # Opcional: log de usuarios que se unen (puede ser muy ruidoso)
        pass

    async def on_subscription(self, channel, user, sub_type, sub_plan):
        logger.info(f"🎉 Nuevo suscriptor: {user.name}")
        log_service.add_log('info', f'Nuevo suscriptor: {user.name}', 'stats')
        await self.event_subscription(channel, user, sub_type, sub_plan)

    async def on_resubscription(self, channel, user, sub_plan, months, message=None):
        logger.info(f"🔄 Re-suscripción: {user.name} - {months} meses")
        log_service.add_log('info', f'Re-suscripción: {user.name} - {months} meses', 'stats')
        await self.event_subscription(channel, user, 'resub', sub_plan, months)

    async def on_raid(self, channel, user, viewers):
        logger.info(f"⚔️ Raid entrante de {user.name} con {viewers} espectadores")
        log_service.add_log('info', f'Raid entrante de {user.name} con {viewers} espectadores', 'stats')
        await self.event_raid(channel, user, viewers)