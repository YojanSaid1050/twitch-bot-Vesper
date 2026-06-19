from twitchio.ext import commands
from services.moderation_actions import ModerationActions
from services.stats_service import stats_service
from services.warns_system import warns_system
from services.config_service import config_service
from services.log_service import log_service
from bot.permissions import permission_checker
from exceptions import TwitchAPIError, ResourceNotFoundError


def setup_staff_commands(bot):
    mod_actions = ModerationActions()

    @bot.command(name="shoutout", aliases=["so", "saludo"])
    async def shoutout_command(ctx):
        if not permission_checker.is_staff(ctx.message):
            return

        parts = ctx.message.content.split()
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !shoutout @streamer")
            return

        username = parts[1].lstrip('@')
        user_id = await mod_actions.get_user_id(username)
        author = ctx.author.name

        if not user_id:
            await ctx.send(f"❌ No encuentro a {username} en los anales")
            log_service.add_log('warning', f'No se encontró usuario {username} para shoutout', 'bot')
            return

        stats = stats_service
        original_id = stats.broadcaster_id
        stats.broadcaster_id = user_id
        stream_info = await stats.get_stream_info()
        stats.broadcaster_id = original_id

        try:
            if stream_info:
                game = stream_info.get("game_name", "desconocido")
                viewers = stream_info.get("viewer_count", 0)
                await ctx.send(f"🎭 El eco del vacío alza la voz... Shoutout para {username}! Juega {game} con {viewers} almas: https://twitch.tv/{username}")
            else:
                await ctx.send(f"🎭 El eco del vacío alza la voz... Shoutout para {username}! https://twitch.tv/{username}")
            
            log_service.add_log('info', f'Shoutout a {username} por {author}', 'moderation')
        except Exception as e:
            await ctx.send(f"❌ Error al obtener info de {username}")
            log_service.add_log('error', f'Error en shoutout a {username}: {e}', 'twitch_api')

    @bot.command(name="announce", aliases=["anuncio"])
    async def announce_command(ctx):
        if not permission_checker.is_staff(ctx.message):
            return

        parts = ctx.message.content.split(" ", 1)
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !announce <mensaje>")
            return

        message = parts[1]
        author = ctx.author.name
        await ctx.send(f"📢 **ANUNCIO DEL RELICARIO** 📢\n🔮 {message}\n📢 {'=' * 20} 📢")
        log_service.add_log('info', f'Anuncio publicado por {author}: "{message}"', 'moderation')

    @bot.command(name="warn")
    async def warn_command(ctx):
        if not permission_checker.is_staff(ctx.message):
            return

        parts = ctx.message.content.split()
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !warn @usuario <razón>")
            return

        username = parts[1].lstrip('@')
        user_id = await mod_actions.get_user_id(username)
        author = ctx.author.name

        if not user_id:
            await ctx.send(f"❌ No encuentro a {username}")
            log_service.add_log('warning', f'No se encontró usuario {username} para warn', 'bot')
            return

        reason = " ".join(parts[2:]) if len(parts) > 2 else "Comportamiento inapropiado"
        warning_count, action_taken = await warns_system.add_warning(
            user_id, username, reason, ctx.author.name
        )

        await ctx.send(f"⚠️ {username} advertido ({warning_count}/{warns_system.MAX_WARNS}) → {reason}")
        log_service.add_log('warning', f'Advertencia aplicada a {username} ({warning_count}/{warns_system.MAX_WARNS}) por {author}. Razón: "{reason}"', 'moderation')

        if action_taken:
            await ctx.send(f"🔇 {username} silenciado por acumular demasiadas advertencias")
            log_service.add_log('warning', f'Timeout automático a {username} por exceder advertencias ({warning_count}/{warns_system.MAX_WARNS})', 'moderation')

    @bot.command(name="warnings")
    async def warnings_command(ctx):
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
                log_service.add_log('warning', f'No se encontró usuario {username} para consultar warnings', 'bot')
                return

        warnings = config_service.get_warnings(user_id)
        if not warnings:
            await ctx.send(f"📜 {username} no tiene advertencias")
            return

        await ctx.send(f"📜 {username} tiene {len(warnings)} advertencia(s):")
        for i, warn in enumerate(warnings[:3], 1):
            await ctx.send(f"  {i}. {warn['reason']} (por {warn['warned_by']})")

    @bot.command(name="clearwarns")
    async def clear_warns_command(ctx):
        if not permission_checker.is_staff(ctx.message):
            return

        parts = ctx.message.content.split()
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !clearwarns @usuario")
            return

        username = parts[1].lstrip('@')
        user_id = await mod_actions.get_user_id(username)
        author = ctx.author.name

        if not user_id:
            await ctx.send(f"❌ No encuentro a {username}")
            log_service.add_log('warning', f'No se encontró usuario {username} para clearwarns', 'bot')
            return

        try:
            cleared = config_service.clear_warnings(user_id)
            if cleared > 0:
                await ctx.send(f"🧹 {cleared} advertencia(s) borradas de {username}")
                log_service.add_log('info', f'Advertencias limpiadas para {username} ({cleared} eliminadas) por {author}', 'moderation')
            else:
                await ctx.send(f"📜 {username} no tenía advertencias")
        except Exception as e:
            await ctx.send(f"❌ Error al limpiar advertencias: {e}")
            log_service.add_log('error', f'Error al limpiar advertencias de {username}: {e}', 'bot')