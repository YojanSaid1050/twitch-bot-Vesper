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
            await channel.send("🕯️ El vigilante despierta... los ecos del vacío están a tu disposición.")
            log_service.add_log('info', f'Mensaje de bienvenida enviado a {channel.name}', 'bot')

    async def on_message(self, message: Message):
        if message.echo:
            return

        # No mostramos cada mensaje en consola para evitar ruido, solo los relevantes (comandos, spam, etc.)
        # Si quieres ver todos los mensajes, descomenta la siguiente línea:
        # logger.info(f"{message.author.name}: {message.content}")

        # Verificar si es staff (mod o broadcaster)
        is_staff = permission_checker.is_staff(message)
        is_vip = message.author.is_vip if hasattr(message.author, 'is_vip') else False

        # ========== ANTI-SPAM (palabras prohibidas, etc) ==========
        if not is_staff:
            is_spam, action, warning_type, reason = anti_spam.check_message(
                message.author.id,
                message.content,
                is_vip=is_vip,
                is_staff=is_staff
            )

            if is_spam:
                logger.warning(f"🚫 Spam detectado de {message.author.name}: {reason}")
                log_service.add_log('warning', f'Spam detectado de {message.author.name}: {reason}', 'anti_spam')
                
                # Siempre eliminar el mensaje
                try:
                    success = await mod_actions.delete_message(message.id)
                    if success:
                        logger.info(f"🗑️ Mensaje eliminado de {message.author.name} (spam)")
                    else:
                        logger.warning(f"⚠️ No se pudo eliminar mensaje de {message.author.name} (spam)")
                except Exception as e:
                    logger.error(f"Error eliminando mensaje por spam: {e}")
                
                # Obtener conteo actual para mostrar
                count = warning_manager.get_warning_count(message.author.id, warning_type)
                max_w = warning_manager.get_max_warnings()
                
                # Mapeo de tipos a nombres legibles
                type_names = {
                    'caps': 'mayúsculas excesivas',
                    'rate': 'envío rápido de mensajes',
                    'repeat': 'mensajes repetidos',
                    'word': 'palabra prohibida'
                }
                type_desc = type_names.get(warning_type, warning_type)
                
                # Aplicar acción según advertencia
                if action == 'warning':
                    await message.channel.send(
                        f"⚠️ {message.author.name}, el vacío detecta ecos no deseados. "
                        f"Advertencia {count}/{max_w} por {type_desc}."
                    )
                elif action == 'timeout':
                    try:
                        await mod_actions.timeout(message.author.name, 600, f"Spam repetido: {reason}")
                        await message.channel.send(
                            f"🔇 {message.author.name} silenciado 10 minutos por {type_desc} "
                            f"(advertencia {count}/{max_w})."
                        )
                    except Exception as e:
                        logger.error(f"Error aplicando timeout por spam: {e}")
                        await message.channel.send(f"⚠️ Error al silenciar a {message.author.name}")
                elif action == 'ban':
                    try:
                        await mod_actions.ban(message.author.name, f"Spam excesivo: {reason}")
                        await message.channel.send(
                            f"🔨 {message.author.name} desterrado por {type_desc} "
                            f"(advertencia {count}/{max_w})."
                        )
                    except Exception as e:
                        logger.error(f"Error aplicando ban por spam: {e}")
                        await message.channel.send(f"⚠️ Error al desterrar a {message.author.name}")
                return

        # ========== CONTROL DE ENLACES ==========
        if not is_staff and not is_vip:
            link_result = await link_manager.check_message(
                message.author.id,
                message.author.name,
                message.content,
                is_staff=is_staff,
                is_vip=is_vip
            )

            if link_result:
                action, reason, blocked_links = link_result
                count = warning_manager.get_warning_count(message.author.id, 'link')
                max_w = warning_manager.get_max_warnings()

                # Siempre eliminar el mensaje
                try:
                    success = await mod_actions.delete_message(message.id)
                    if success:
                        logger.info(f"🗑️ Mensaje eliminado de {message.author.name}: {message.content[:50]}...")
                    else:
                        logger.warning(f"⚠️ No se pudo eliminar el mensaje de {message.author.name}")
                        try:
                            await message.delete()
                        except Exception as e:
                            logger.error(f"Fallback también falló: {e}")
                except Exception as e:
                    logger.error(f"Error eliminando mensaje: {e}")
                    try:
                        await message.delete()
                    except Exception as e2:
                        logger.error(f"Todos los intentos de eliminar mensaje fallaron: {e2}")

                # Acción según advertencia
                if action == 'warning':
                    remaining = max_w - count
                    await message.channel.send(
                        f"⚠️ {message.author.name}, enlaces prohibidos. "
                        f"Advertencia {count}/{max_w}. "
                        f"Quedan {remaining} avisos antes del silencio."
                    )
                    logger.info(f"🚫 Enlace bloqueado de {message.author.name} - Advertencia {count}/{max_w}")
                    log_service.add_log('info', f'Enlace bloqueado de {message.author.name} - Advertencia {count}', 'link_manager')

                elif action == 'timeout':
                    try:
                        await mod_actions.timeout(message.author.name, link_manager.TIMEOUT_DURATION, reason)
                        await message.channel.send(
                            f"🔇 {message.author.name} silenciado {link_manager.TIMEOUT_DURATION // 60} minutos "
                            f"por enlaces prohibidos (advertencia {count}/{max_w})."
                        )
                        logger.info(f"⏰ Timeout a {message.author.name} por enlaces prohibidos")
                        log_service.add_log('info', f'Timeout a {message.author.name} por enlaces prohibidos', 'moderation')
                    except Exception as e:
                        logger.error(f"Error aplicando timeout: {e}")
                        await message.channel.send(f"⚠️ Error al silenciar a {message.author.name}")

                elif action == 'ban':
                    try:
                        await mod_actions.ban(message.author.name, reason)
                        await message.channel.send(
                            f"🔨 {message.author.name} desterrado por enlaces prohibidos "
                            f"(advertencia {count}/{max_w})."
                        )
                        logger.info(f"🔨 Ban a {message.author.name} por enlaces prohibidos")
                        log_service.add_log('info', f'Ban a {message.author.name} por enlaces prohibidos', 'moderation')
                    except Exception as e:
                        logger.error(f"Error aplicando ban: {e}")
                        await message.channel.send(f"⚠️ Error al desterrar a {message.author.name}")

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

    # Eventos de notificación (follows, subs, raids) – ya tienen su propia lógica en notification_service
    # Aquí solo los redirigimos, pero podemos añadir logs más claros.
    async def event_follow(self, channel, user):
        logger.info(f"⭐ Nuevo follow de {user.name}")
        await notification_service.on_follow(channel, user)

    async def event_subscription(self, channel, user, sub_type, sub_plan, months=None):
        logger.info(f"🎉 Nueva suscripción de {user.name} - {sub_plan}")
        await notification_service.on_subscribe(channel, user, sub_plan, sub_type)

    async def event_raid(self, channel, user, viewers):
        logger.info(f"⚔️ Raid entrante de {user.name} con {viewers} espectadores")
        await notification_service.on_raid(channel, user, viewers)

    async def event_raid_go(self, channel, target, viewers):
        logger.info(f"⚔️ Raid saliente a {target} con {viewers} espectadores")
        await notification_service.on_raid_go(channel, target, viewers)

    async def event_host(self, channel, user, viewers):
        logger.info(f"🏠 Host de {user.name} con {viewers} espectadores")
        await notification_service.on_host(channel, user, viewers)

    async def on_user_join(self, channel, user):
        # Opcional: log de usuarios que se unen (puede ser muy ruidoso)
        pass

    async def on_subscription(self, channel, user, sub_type, sub_plan):
        logger.info(f"🎉 Nuevo suscriptor: {user.name}")
        log_service.add_log('info', f'Nuevo suscriptor: {user.name}', 'twitch_events')
        await self.event_subscription(channel, user, sub_type, sub_plan)

    async def on_resubscription(self, channel, user, sub_plan, months, message=None):
        logger.info(f"🔄 Re-suscripción: {user.name} - {months} meses")
        log_service.add_log('info', f'Re-suscripción: {user.name} - {months} meses', 'twitch_events')
        await self.event_subscription(channel, user, 'resub', sub_plan, months)

    async def on_raid(self, channel, user, viewers):
        logger.info(f"⚔️ Raid entrante de {user.name} con {viewers} espectadores")
        log_service.add_log('info', f'Raid entrante de {user.name} con {viewers} espectadores', 'twitch_events')
        await self.event_raid(channel, user, viewers)