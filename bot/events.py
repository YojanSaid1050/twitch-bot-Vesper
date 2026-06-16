"""
Manejadores de eventos del bot
"""

from twitchio import Message

from utils.logger import get_logger
from bot.permissions import permission_checker
from security import anti_spam
from services.moderation_actions import ModerationActions
from services.notification_service import notification_service
from services.clip_service import clip_service
from services.stats_service import stats_service


logger = get_logger(__name__)
mod_actions = ModerationActions()


class EventHandler:
    """
    Maneja eventos del bot (mensajes, joins, etc)
    """
    
    def __init__(self, bot):
        self.bot = bot
        notification_service.set_bot(bot)
    
    async def on_ready(self):
        """Evento cuando el bot está listo"""
        logger.info(f"✅ Conectado como {self.bot.nick}")
        
        # Usar channel_name si existe, sino obtener del primer canal conectado
        if hasattr(self.bot, 'channel_name'):
            logger.info(f"📺 Canal: {self.bot.channel_name}")
            channel = self.bot.get_channel(self.bot.channel_name)
        elif self.bot.connected_channels:
            channel = self.bot.connected_channels[0]
            logger.info(f"📺 Canal: {channel.name}")
        else:
            logger.info("📺 No hay canales conectados aún")
            return
        
        if channel:
            await channel.send("🕯️ The watcher awakens... commands are now available.")
    
    async def on_message(self, message: Message):
        """
        Evento cuando se recibe un mensaje
        """
        # Ignorar mensajes del propio bot
        if message.echo:
            return
        
        # LOGGING
        logger.info(f"{message.author.name}: {message.content}")
        
        # ========== ANTI-SPAM ==========
        # No aplicar anti-spam a staff
        if not permission_checker.is_staff(message):
            is_spam, reason = anti_spam.check_message(message.author.id, message.content)
            
            if is_spam:
                logger.warning(f"Spam detectado de {message.author.name}: {reason}")
                # Timeout de 1 minuto por spam
                await mod_actions.timeout(message.author.name, 60, f"Spam detectado: {reason}")
                
                # Enviar advertencia
                await message.channel.send(f"⚠️ {message.author.name}, por favor evita spam. Silenciado por 60s.")
                return  # No procesar el comando si es spam
        
        # ========== PROCESAR COMANDOS ==========
        await self.bot.handle_commands(message)
    
    async def on_command_error(self, context, error):
        """Manejo global de errores"""
        from exceptions import PermissionDeniedError, TwitchAPIError, ValidationError
        
        error_msg = None
        
        if isinstance(error, PermissionDeniedError):
            error_msg = str(error)
        elif isinstance(error, ValidationError):
            error_msg = f"❌ {error}"
        elif isinstance(error, TwitchAPIError):
            logger.error(f"API Error: {error}")
            error_msg = f"❌ Error con Twitch: {str(error)[:100]}"
        else:
            logger.error(f"Error en comando {context.command.name}: {error}")
            error_msg = "❌ Algo salió mal en la oscuridad..."
        
        if error_msg and context.channel:
            await context.reply(error_msg)
    
    # ========== NOTIFICACIONES DE EVENTOS ==========
    
    async def event_follow(self, channel, user):
        """
        Evento cuando alguien sigue el canal
        Este método debe ser llamado desde el bot o desde un webhook
        """
        await notification_service.on_follow(channel, user)
    
    async def event_subscription(self, channel, user, sub_type, sub_plan, months=None):
        """
        Evento cuando alguien se suscribe o renueva suscripción
        
        Args:
            channel: Canal donde ocurrió
            user: Usuario que se suscribió
            sub_type: Tipo de suscripción ('sub', 'resub')
            sub_plan: Plan ('prime', '1000', '2000', '3000')
            months: Meses de suscripción (para resub)
        """
        await notification_service.on_subscribe(channel, user, sub_plan, sub_type)
    
    async def event_raid(self, channel, user, viewers):
        """
        Evento cuando alguien hace raid al canal
        
        Args:
            channel: Canal que recibe la raid
            user: Usuario que hizo la raid
            viewers: Número de espectadores en la raid
        """
        await notification_service.on_raid(channel, user, viewers)
    
    async def event_raid_go(self, channel, target, viewers):
        """
        Evento cuando el canal hace raid a otro
        
        Args:
            channel: Canal que envía la raid
            target: Canal destino
            viewers: Número de espectadores
        """
        await notification_service.on_raid_go(channel, target, viewers)
    
    async def event_host(self, channel, user, viewers):
        """
        Evento cuando alguien hospeda el canal
        
        Args:
            channel: Canal hospedado
            user: Usuario que hospeda
            viewers: Número de espectadores
        """
        await notification_service.on_host(channel, user, viewers)
    
    # ========== EVENTOS LEGACY DE TWITCHIO (si los soporta) ==========
    
    async def on_user_join(self, channel, user):
        """Evento cuando alguien se une al chat"""
        # Opcional: mensaje de bienvenida
        pass
    
    async def on_subscription(self, channel, user, sub_type, sub_plan):
        """
        Evento de suscripción de TwitchIO (legacy)
        """
        logger.info(f"🎉 Nuevo suscriptor: {user.name}")
        await self.event_subscription(channel, user, sub_type, sub_plan)
    
    async def on_resubscription(self, channel, user, sub_plan, months, message=None):
        """
        Evento de re-suscripción de TwitchIO (legacy)
        """
        logger.info(f"🔄 Re-suscripción: {user.name} - {months} meses")
        await self.event_subscription(channel, user, 'resub', sub_plan, months)
    
    async def on_raid(self, channel, user, viewers):
        """
        Evento de raid de TwitchIO (legacy)
        """
        logger.info(f"⚔️ Raid entrante de {user.name} con {viewers} espectadores")
        await self.event_raid(channel, user, viewers)