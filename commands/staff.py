"""
Comandos avanzados para staff
"""

from twitchio.ext import commands

from services.moderation_actions import ModerationActions
from services.stats_service import stats_service
from services.warns_system import warns_system
from database import db
from bot.permissions import permission_checker


def setup_staff_commands(bot):
    """Registrar comandos de staff avanzados"""
    mod_actions = ModerationActions()
    
    @bot.command(name="shoutout", aliases=["so", "saludo"])
    async def shoutout_command(ctx: commands.Context):
        """Dar shoutout a otro streamer (solo staff)"""
        if not permission_checker.is_staff(ctx.message):
            return
        
        parts = ctx.message.content.split()
        
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !shoutout @streamer")
            return
        
        username = parts[1].lstrip('@')
        
        # Obtener info del streamer
        user_id = await mod_actions.get_user_id(username)
        
        if not user_id:
            await ctx.send(f"❌ No encuentro a {username} en el reino...")
            return
        
        # Obtener su juego actual
        stats = stats_service
        original_id = stats.broadcaster_id
        stats.broadcaster_id = user_id
        stream_info = await stats.get_stream_info()
        stats.broadcaster_id = original_id
        
        if stream_info:
            game_name = stream_info.get("game_name", "desconocido")
            viewer_count = stream_info.get("viewer_count", 0)
            await ctx.send(f"🎤 ¡Shoutout para {username}! Está jugando {game_name} con {viewer_count} espectadores. ¡Síguelo en https://twitch.tv/{username}!")
        else:
            await ctx.send(f"🎤 ¡Shoutout para {username}! No está en vivo ahora, pero igual merece tu follow. https://twitch.tv/{username}")
    
    @bot.command(name="announce", aliases=["anuncio", "aviso"])
    async def announce_command(ctx: commands.Context):
        """Enviar anuncio destacado (solo staff) - en un solo mensaje"""
        if not permission_checker.is_staff(ctx.message):
            return
        
        parts = ctx.message.content.split(" ", 1)
        
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !announce mensaje importante")
            return
        
        message = parts[1]
        
        # Enviar como un solo mensaje con formato
        await ctx.send(f"🔔 **ANUNCIO** 🔔\n📢 {message}\n🔔 {'=' * 20} 🔔")
    
    @bot.command(name="warn", aliases=["advertir"])
    async def warn_command(ctx: commands.Context):
        """Advertir a un usuario (solo staff)"""
        if not permission_checker.is_staff(ctx.message):
            return
        
        parts = ctx.message.content.split()
        
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !warn @usuario razón de la advertencia")
            await ctx.send("Ejemplo: !warn @troll No hacer spam")
            return
        
        username = parts[1].lstrip('@')
        
        # Obtener ID del usuario
        user_id = await mod_actions.get_user_id(username)
        
        if not user_id:
            await ctx.send(f"❌ No encuentro a {username}")
            return
        
        reason = " ".join(parts[2:]) if len(parts) > 2 else "Comportamiento inapropiado"
        
        # Agregar advertencia
        warning_count, action_taken, action_type = await warns_system.add_warning(
            user_id, username, reason, ctx.author.name
        )
        
        await ctx.send(f"⚠️ {username} ha sido advertido ({warning_count}/{warns_system.MAX_WARNS}) → {reason}")
        
        if action_taken:
            await ctx.send(f"🔇 {username} ha sido silenciado por alcanzar el máximo de advertencias")
    
    @bot.command(name="warnings", aliases=["advertencias", "warns"])
    async def warnings_command(ctx: commands.Context):
        """Ver advertencias de un usuario (solo staff)"""
        if not permission_checker.is_staff(ctx.message):
            return
        
        parts = ctx.message.content.split()
        
        if len(parts) < 2:
            username = ctx.author.name
            user_id = ctx.author.id
        else:
            username = parts[1].lstrip('@')
            user_id = await mod_actions.get_user_id(username)
            
            if not user_id:
                await ctx.send(f"❌ No encuentro a {username}")
                return
        
        warnings = db.get_warnings(user_id)
        
        if not warnings:
            await ctx.send(f"📜 {username} no tiene advertencias. El silencio es su virtud.")
            return
        
        await ctx.send(f"📜 {username} tiene {len(warnings)} advertencia(s):")
        for i, warn in enumerate(warnings[:3], 1):
            await ctx.send(f"  {i}. {warn['reason']} (por {warn['warned_by']})")
    
    @bot.command(name="clearwarns", aliases=["limpiarwarns", "borrarwarns"])
    async def clear_warns_command(ctx: commands.Context):
        """Limpiar advertencias de un usuario (solo staff)"""
        if not permission_checker.is_staff(ctx.message):
            return
        
        parts = ctx.message.content.split()
        
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !clearwarns @usuario")
            return
        
        username = parts[1].lstrip('@')
        user_id = await mod_actions.get_user_id(username)
        
        if not user_id:
            await ctx.send(f"❌ No encuentro a {username}")
            return
        
        cleared = db.clear_warnings(user_id)
        
        if cleared > 0:
            await ctx.send(f"🕊️ Se han borrado {cleared} advertencia(s) de {username}")
        else:
            await ctx.send(f"📜 {username} no tenía advertencias")