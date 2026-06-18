from twitchio.ext import commands
from services.moderation_actions import ModerationActions
from services.stats_service import stats_service
from services.warns_system import warns_system
from services.config_service import config_service
from bot.permissions import permission_checker


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

        if not user_id:
            await ctx.send(f"❌ No encuentro a {username} en los anales")
            return

        stats = stats_service
        original_id = stats.broadcaster_id
        stats.broadcaster_id = user_id
        stream_info = await stats.get_stream_info()
        stats.broadcaster_id = original_id

        if stream_info:
            game = stream_info.get("game_name", "desconocido")
            viewers = stream_info.get("viewer_count", 0)
            await ctx.send(f"🎭 El eco del vacío alza la voz... Shoutout para {username}! Juega {game} con {viewers} almas: https://twitch.tv/{username}")
        else:
            await ctx.send(f"🎭 El eco del vacío alza la voz... Shoutout para {username}! https://twitch.tv/{username}")

    @bot.command(name="announce", aliases=["anuncio"])
    async def announce_command(ctx):
        if not permission_checker.is_staff(ctx.message):
            return

        parts = ctx.message.content.split(" ", 1)
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !announce <mensaje>")
            return

        message = parts[1]
        await ctx.send(f"📢 **ANUNCIO DEL RELICARIO** 📢\n🔮 {message}\n📢 {'=' * 20} 📢")

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

        if not user_id:
            await ctx.send(f"❌ No encuentro a {username}")
            return

        reason = " ".join(parts[2:]) if len(parts) > 2 else "Comportamiento inapropiado"
        warning_count, action_taken = await warns_system.add_warning(
            user_id, username, reason, ctx.author.name
        )

        await ctx.send(f"⚠️ {username} advertido ({warning_count}/{warns_system.MAX_WARNS}) → {reason}")

        if action_taken:
            await ctx.send(f"🔇 {username} silenciado por acumular demasiadas advertencias")

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

        if not user_id:
            await ctx.send(f"❌ No encuentro a {username}")
            return

        cleared = config_service.clear_warnings(user_id)
        if cleared > 0:
            await ctx.send(f"🧹 {cleared} advertencia(s) borradas de {username}")
        else:
            await ctx.send(f"📜 {username} no tenía advertencias")