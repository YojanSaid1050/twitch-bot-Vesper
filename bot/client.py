"""
Cliente principal del bot
"""

from twitchio.ext import commands

from config import settings
from bot.events import EventHandler
from bot.permissions import permission_checker
from commands import register_commands
from services.token_manager import token_manager
from utils.logger import get_logger


logger = get_logger(__name__)


class Bot(commands.Bot):
    """
    Cliente principal del bot de Twitch
    """
    
    def __init__(self):
        logger.info("🕯️ Inicializando el bot...")
        
        # Iniciar sistema de auto-refresh de tokens
        token_manager.start_auto_refresh()
        
        # Inicializar bot padre
        super().__init__(
            token=settings.BOT_TOKEN,
            prefix="!",
            initial_channels=[settings.CHANNEL]
        )
        
        # Guardar el canal para uso posterior
        self.channel_name = settings.CHANNEL
        
        # Inicializar manejadores
        self.event_handler = EventHandler(self)
        
        # Registrar comandos
        register_commands(self)
        
        # Iniciar servicio de EventSub (notificaciones automáticas)
        self._init_eventsub()
        
        logger.info("✅ Bot inicializado correctamente")
    
    def _init_eventsub(self):
        """Inicializar servicio de EventSub para notificaciones"""
        try:
            from services.eventsub_service import eventsub_service
            
            # Configurar el bot en el servicio
            eventsub_service.set_bot(self)
            
            # Iniciar servidor webhook local
            eventsub_service.start_webhook_server()
            
            # Suscribirse a eventos si hay callback URL configurada
            if settings.EVENTSUB_CALLBACK_URL and settings.TWITCH_WEBHOOK_SECRET:
                eventsub_service.subscribe_to_events()
                logger.info("✅ EventSub configurado correctamente")
            else:
                logger.warning("⚠️ EventSub no configurado. Las notificaciones automáticas no funcionarán.")
                
        except ImportError as e:
            logger.warning(f"⚠️ No se pudo cargar EventSub: {e}")
        except Exception as e:
            logger.error(f"❌ Error inicializando EventSub: {e}")
    
    # ============================================
    # EVENTOS
    # ============================================
    
    async def event_ready(self):
        """Evento cuando el bot está listo"""
        await self.event_handler.on_ready()
    
    async def event_message(self, message):
        """Evento cuando se recibe un mensaje"""
        await self.event_handler.on_message(message)
    
    async def event_command_error(self, context, error):
        """Evento cuando un comando falla"""
        await self.event_handler.on_command_error(context, error)
    
    # ============================================
    # EVENTOS DE TWITCHIO PARA NOTIFICACIONES
    # ============================================
    
    async def event_subscription(self, channel, user, sub_type, sub_plan):
        """Evento de suscripción (nativo de TwitchIO)"""
        await self.event_handler.event_subscription(channel, user, sub_type, sub_plan)
    
    async def event_subscription_gift(self, channel, user, recipient, sub_plan, sub_type):
        """Evento de regalo de suscripción"""
        await self.event_handler.event_subscription_gift(channel, user, recipient, sub_plan, sub_type)
    
    async def event_resub(self, channel, user, months, sub_plan, message=None):
        """Evento de re-suscripción"""
        await self.event_handler.event_resub(channel, user, months, sub_plan, message)
    
    async def event_raid(self, channel, user, viewers):
        """Evento de raid entrante"""
        await self.event_handler.event_raid(channel, user, viewers)
    
    async def event_host(self, channel, user, viewers):
        """Evento de host"""
        await self.event_handler.event_host(channel, user, viewers)
    
    # ============================================
    # MÉTODOS DE UTILIDAD
    # ============================================
    
    def is_staff(self, ctx) -> bool:
        """
        Verificar si el usuario es staff (mod o broadcaster)
        Método de conveniencia para mantener compatibilidad
        """
        return permission_checker.is_staff(ctx.message)
    
    async def close(self):
        """Cerrar el bot correctamente"""
        try:
            from services.eventsub_service import eventsub_service
            eventsub_service.stop()
        except:
            pass
        
        token_manager.stop_auto_refresh()
        await super().close()