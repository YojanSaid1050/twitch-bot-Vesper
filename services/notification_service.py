"""
Servicio de notificaciones para eventos de Twitch
"""

from typing import Optional, Dict
from datetime import datetime

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class NotificationService:
    """Servicio para manejar notificaciones de eventos"""
    
    def __init__(self):
        self.bot = None
    
    def set_bot(self, bot):
        """Establecer referencia al bot para enviar mensajes"""
        self.bot = bot
    
    async def on_follow(self, channel, user):
        """Notificación de nuevo seguidor"""
        message = f"🕯️ Una nueva alma se une al ritual... ¡Bienvenido {user.name}! Que la oscuridad te guíe. 🖤"
        await channel.send(message)
        logger.info(f"Nuevo seguidor: {user.name}")
    
    async def on_subscribe(self, channel, user, sub_plan, sub_type):
        """Notificación de nueva suscripción"""
        # Tipos de suscripción
        tier_messages = {
            "prime": f"🎭 {user.name} se ha suscrito con Twitch Prime. Los antiguos dioses te sonríen.",
            "1000": f"👑 {user.name} se ha unido al círculo de Tier 1. ¡La llama se aviva!",
            "2000": f"⚔️ {user.name} asciende al Tier 2. ¡Las leyendas hablan de tu poder!",
            "3000": f"🐉 {user.name} alcanza el Tier 3. ¡INMORTAL! El altar tiembla ante tu presencia."
        }
        
        message = tier_messages.get(sub_plan, f"🎉 {user.name} se ha suscrito. ¡Bienvenido a la cofradía!")
        
        # Mensaje especial para re-suscripciones
        if sub_type == "resub":
            months = 1  # Se puede obtener de los datos del evento
            message = f"🔄 {user.name} renueva su juramento por {months} mes(es). ¡La lealtad es eterna!"
        
        await channel.send(message)
        logger.info(f"Nuevo suscriptor: {user.name} - Plan: {sub_plan}")
    
    async def on_raid(self, channel, user, viewers):
        """Notificación de raid entrante"""
        message = f"⚔️ ¡UNA HORDA LLEGA! {user.name} nos invade con {viewers} almas. ¡Preparaos para el caos ritual! 🐉"
        await channel.send(message)
        logger.info(f"Raid entrante de {user.name} con {viewers} espectadores")
    
    async def on_raid_go(self, channel, target, viewers):
        """Notificación de raid saliente (cuando el streamer hace raid a otro)"""
        message = f"🚀 El ritual se expande... ¡Vamos a invadir {target} con {viewers} almas! ¡QUE LA OSCURIDAD NOS ACOMPAÑE! 🌑"
        await channel.send(message)
        logger.info(f"Raid saliente hacia {target} con {viewers} espectadores")
    
    async def on_host(self, channel, user, viewers):
        """Notificación de host entrante"""
        message = f"🏰 {user.name} hospeda el ritual con {viewers} almas. ¡Bienvenidos a todos! 🕯️"
        await channel.send(message)
        logger.info(f"Host de {user.name} con {viewers} espectadores")


# Instancia global
notification_service = NotificationService()