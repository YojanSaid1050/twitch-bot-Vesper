"""
Comandos de moderación del chat
"""

from twitchio.ext import commands

from services import ChatSettings
from services.moderation_actions import ModerationActions
from services.log_service import log_service
from exceptions import ValidationError, TwitchAPIError, ResourceNotFoundError
from utils import validate_slow_mode_time, validate_follower_duration
from bot.permissions import permission_checker


def setup_moderation_commands(bot):
    """Registrar comandos de moderación"""
    chat_settings = ChatSettings()
    mod_actions = ModerationActions()
    
    @bot.command(name="slow")
    async def slow_mode_command(ctx: commands.Context):
        """Activar/desactivar modo lento (solo staff)"""
        if not permission_checker.is_staff(ctx.message):
            return
        
        parts = ctx.message.content.split()
        
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !slow 10 o !slow off")
            await ctx.send("Ejemplo: !slow 30 (30 segundos entre susurros)")
            return
        
        value = parts[1].lower()
        author = ctx.author.name
        
        try:
            if value == "off":
                await chat_settings.set_slow_mode(False)
                await ctx.send("⏳ El tiempo se libera... modo lento desactivado.")
                log_service.add_log('info', f'Modo lento desactivado por {author}', 'moderation')
            else:
                seconds = int(value)
                is_valid, error_msg = validate_slow_mode_time(seconds)
                if not is_valid:
                    await ctx.send(f"❌ {error_msg}")
                    return
                await chat_settings.set_slow_mode(True, seconds)
                await ctx.send(f"⏳ El tiempo se vuelve lento... el ritual se pausa {seconds} segundos entre cada susurro.")
                log_service.add_log('info', f'Modo lento activado ({seconds}s) por {author}', 'moderation')
        except ValueError:
            await ctx.send("❌ El tiempo debe ser un número. Ejemplo: !slow 10")
        except ValidationError as e:
            await ctx.send(f"❌ {e}")
        except TwitchAPIError as e:
            await ctx.send(f"❌ Error: {e.message}")
            log_service.add_log('error', f'Error al configurar modo lento: {e.message}', 'twitch_api')
    
    @bot.command(name="followers", aliases=["follow"])
    async def followers_mode_command(ctx: commands.Context):
        """Activar/desactivar modo solo seguidores (solo staff)"""
        if not permission_checker.is_staff(ctx.message):
            return
        
        parts = ctx.message.content.split()
        
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !followers 10 o !followers off")
            await ctx.send("Ejemplo: !followers 5 (solo seguidores de 5 minutos)")
            return
        
        value = parts[1].lower()
        author = ctx.author.name
        
        try:
            if value == "off":
                await chat_settings.set_follower_mode(False)
                await ctx.send("🚪 Las puertas se abren... restricción de seguidores removida.")
                log_service.add_log('info', f'Modo seguidores desactivado por {author}', 'moderation')
            else:
                minutes = int(value)
                is_valid, error_msg = validate_follower_duration(minutes)
                if not is_valid:
                    await ctx.send(f"❌ {error_msg}")
                    return
                await chat_settings.set_follower_mode(True, minutes)
                await ctx.send(f"🚪 El umbral se guarda... solo almas que sigan al invocador desde hace {minutes} minutos pueden entrar.")
                log_service.add_log('info', f'Modo seguidores activado ({minutes}m) por {author}', 'moderation')
        except ValueError:
            await ctx.send("❌ El tiempo debe ser un número. Ejemplo: !followers 5")
        except ValidationError as e:
            await ctx.send(f"❌ {e}")
        except TwitchAPIError as e:
            await ctx.send(f"❌ Error: {e.message}")
            log_service.add_log('error', f'Error al configurar modo seguidores: {e.message}', 'twitch_api')
    
    @bot.command(name="emote", aliases=["emotesonly"])
    async def emote_mode_command(ctx: commands.Context):
        """Activar/desactivar modo solo emotes (solo staff)"""
        if not permission_checker.is_staff(ctx.message):
            return
        
        parts = ctx.message.content.split()
        
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !emote on/off")
            return
        
        value = parts[1].lower()
        author = ctx.author.name
        
        if value not in ["on", "off"]:
            await ctx.send("❌ Usa 'on' o 'off'")
            return
        
        enabled = value == "on"
        
        try:
            await chat_settings.set_emote_mode(enabled)
            if enabled:
                await ctx.send("😶 El lenguaje se transforma en iconos... solo ecos visuales a partir de ahora.")
                log_service.add_log('info', f'Modo emotes activado por {author}', 'moderation')
            else:
                await ctx.send("😶 El lenguaje vuelve a la palabra... modo emotes desactivado.")
                log_service.add_log('info', f'Modo emotes desactivado por {author}', 'moderation')
        except TwitchAPIError as e:
            await ctx.send(f"❌ Error: {e.message}")
            log_service.add_log('error', f'Error al configurar modo emotes: {e.message}', 'twitch_api')
    
    @bot.command(name="subscribers", aliases=["subonly", "submode"])
    async def subscribers_mode_command(ctx: commands.Context):
        """Activar/desactivar modo solo suscriptores (solo staff)"""
        if not permission_checker.is_staff(ctx.message):
            return
        
        parts = ctx.message.content.split()
        
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !subscribers on/off")
            return
        
        value = parts[1].lower()
        author = ctx.author.name
        
        if value not in ["on", "off"]:
            await ctx.send("❌ Usa 'on' o 'off'")
            return
        
        enabled = value == "on"
        
        try:
            await chat_settings.set_subscriber_mode(enabled)
            if enabled:
                await ctx.send("👑 El velo de los suscriptores se alza... solo los elegidos pueden alzar la voz.")
                log_service.add_log('info', f'Modo suscriptores activado por {author}', 'moderation')
            else:
                await ctx.send("👑 El velo se disipa... todos pueden hablar nuevamente.")
                log_service.add_log('info', f'Modo suscriptores desactivado por {author}', 'moderation')
        except TwitchAPIError as e:
            await ctx.send(f"❌ Error: {e.message}")
            log_service.add_log('error', f'Error al configurar modo suscriptores: {e.message}', 'twitch_api')
    
    @bot.command(name="timeout")
    async def timeout_command(ctx: commands.Context):
        """Dar timeout a un usuario (solo staff)"""
        if not permission_checker.is_staff(ctx.message):
            return
        
        content = ctx.message.content
        parts = content.split()
        
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !timeout @usuario [segundos] [razón]")
            await ctx.send("Ejemplos: !timeout @spammer 600 No hacer spam")
            await ctx.send("          !timeout @spammer No hacer spam (10 min por defecto)")
            return
        
        username = parts[1].lstrip('@')
        duration = 600
        reason_parts = []
        author = ctx.author.name
        
        found_duration = False
        for part in parts[2:]:
            if not found_duration and part.isdigit():
                duration = int(part)
                found_duration = True
            else:
                reason_parts.append(part)
        
        if duration < 1:
            duration = 1
            await ctx.send("⚠️ Duración muy baja, usando 1 segundo")
        elif duration > 1209600:
            duration = 1209600
            await ctx.send("⚠️ Duración excede 14 días, usando máximo permitido")
        
        reason = " ".join(reason_parts) if reason_parts else "No especificada"
        
        try:
            await mod_actions.timeout(username, duration, reason)
            
            if duration >= 86400:
                duration_str = f"{duration // 86400} días"
            elif duration >= 3600:
                duration_str = f"{duration // 3600} horas"
            elif duration >= 60:
                duration_str = f"{duration // 60} minutos"
            else:
                duration_str = f"{duration} segundos"
            
            await ctx.send(f"🔇 {username} ha sido silenciado por {duration_str}. Razón: {reason}")
            log_service.add_log('info', f'Timeout aplicado a {username} por {duration_str} (razón: "{reason}") por {author}', 'moderation')
        except ResourceNotFoundError:
            await ctx.send(f"❌ Usuario {username} no encontrado en los anales")
            log_service.add_log('error', f'Usuario {username} no encontrado al aplicar timeout', 'bot')
        except TwitchAPIError as e:
            await ctx.send(f"❌ Error de Twitch: {e.message}")
            log_service.add_log('error', f'Error de Twitch al aplicar timeout a {username}: {e.message}', 'twitch_api')
    
    @bot.command(name="ban")
    async def ban_command(ctx: commands.Context):
        """Banear a un usuario permanentemente (solo staff)"""
        if not permission_checker.is_staff(ctx.message):
            return
        
        parts = ctx.message.content.split()
        
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !ban @usuario [razón]")
            await ctx.send("Ejemplo: !ban @troll Comportamiento tóxico")
            return
        
        username = parts[1].lstrip('@')
        reason = " ".join(parts[2:]) if len(parts) > 2 else "No especificada"
        author = ctx.author.name
        
        try:
            await mod_actions.ban(username, reason)
            await ctx.send(f"🔨 {username} ha sido desterrado del reino. Razón: {reason}")
            log_service.add_log('warning', f'Ban aplicado a {username} (razón: "{reason}") por {author}', 'moderation')
        except ResourceNotFoundError:
            await ctx.send(f"❌ Usuario {username} no encontrado")
            log_service.add_log('error', f'Usuario {username} no encontrado al aplicar ban', 'bot')
        except TwitchAPIError as e:
            await ctx.send(f"❌ Error de Twitch: {e.message}")
            log_service.add_log('error', f'Error de Twitch al aplicar ban a {username}: {e.message}', 'twitch_api')
    
    @bot.command(name="unban")
    async def unban_command(ctx: commands.Context):
        """Desbanear a un usuario (solo staff)"""
        if not permission_checker.is_staff(ctx.message):
            return
        
        parts = ctx.message.content.split()
        
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !unban @usuario")
            return
        
        username = parts[1].lstrip('@')
        author = ctx.author.name
        
        try:
            await mod_actions.unban(username)
            await ctx.send(f"🕊️ {username} ha sido perdonado y puede regresar al reino.")
            log_service.add_log('info', f'Unban aplicado a {username} por {author}', 'moderation')
        except ResourceNotFoundError:
            await ctx.send(f"❌ Usuario {username} no encontrado o no está baneado")
            log_service.add_log('error', f'Usuario {username} no encontrado al aplicar unban', 'bot')
        except TwitchAPIError as e:
            await ctx.send(f"❌ Error de Twitch: {e.message}")
            log_service.add_log('error', f'Error de Twitch al aplicar unban a {username}: {e.message}', 'twitch_api')
    
    @bot.command(name="clear", aliases=["purge"])
    async def clear_chat_command(ctx: commands.Context):
        """Limpiar el chat completamente (solo staff)"""
        if not permission_checker.is_staff(ctx.message):
            return
        
        author = ctx.author.name
        
        try:
            await mod_actions.clear_chat()
            await ctx.send("🧹 El chat ha sido purificado. Un nuevo comienzo.")
            log_service.add_log('info', f'Chat limpiado por {author}', 'moderation')
        except TwitchAPIError as e:
            await ctx.send(f"❌ Error de Twitch: {e.message}")
            log_service.add_log('error', f'Error de Twitch al limpiar chat: {e.message}', 'twitch_api')
    
    @bot.command(name="vip")
    async def vip_command(ctx: commands.Context):
        """Agregar usuario a VIP (solo staff)"""
        if not permission_checker.is_staff(ctx.message):
            return
        
        parts = ctx.message.content.split()
        
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !vip @usuario")
            return
        
        username = parts[1].lstrip('@')
        author = ctx.author.name
        
        try:
            await mod_actions.vip(username)
            await ctx.send(f"👑 {username} ha sido elevado al rango VIP.")
            log_service.add_log('info', f'VIP añadido a {username} por {author}', 'moderation')
        except ResourceNotFoundError:
            await ctx.send(f"❌ Usuario {username} no encontrado")
            log_service.add_log('error', f'Usuario {username} no encontrado al agregar VIP', 'bot')
        except TwitchAPIError as e:
            if "already a vip" in str(e).lower():
                await ctx.send(f"⚠️ {username} ya es VIP")
            else:
                await ctx.send(f"❌ Error de Twitch: {e.message}")
                log_service.add_log('error', f'Error de Twitch al agregar VIP a {username}: {e.message}', 'twitch_api')
    
    @bot.command(name="unvip")
    async def unvip_command(ctx: commands.Context):
        """Remover usuario de VIP (solo staff)"""
        if not permission_checker.is_staff(ctx.message):
            return
        
        parts = ctx.message.content.split()
        
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !unvip @usuario")
            return
        
        username = parts[1].lstrip('@')
        author = ctx.author.name
        
        try:
            await mod_actions.unvip(username)
            await ctx.send(f"💫 {username} ha perdido el rango VIP.")
            log_service.add_log('info', f'VIP removido de {username} por {author}', 'moderation')
        except ResourceNotFoundError:
            await ctx.send(f"❌ Usuario {username} no encontrado")
            log_service.add_log('error', f'Usuario {username} no encontrado al remover VIP', 'bot')
        except TwitchAPIError as e:
            await ctx.send(f"❌ Error de Twitch: {e.message}")
            log_service.add_log('error', f'Error de Twitch al remover VIP de {username}: {e.message}', 'twitch_api')