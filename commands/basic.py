"""
Comandos básicos del bot
"""

from twitchio.ext import commands
import time

from bot.permissions import permission_checker
from utils.cooldowns import cooldowns
from utils.formatters import format_duration_long

bot_start_time = time.time()

PUBLIC_COMMANDS = (
    "!hola !ping !8ball !dado !moneda !elige !lurk !unlurk !uptime !viewers "
    "!followage !quote !clip !sr !np !discord !twitter !instagram !youtube !tiktok"
)
STAFF_COMMANDS = (
    "!title !game !marker !commercial !slow !followers !emote !subscribers !timeout "
    "!ban !unban !clear !vip !unvip !so !announce !warn !warnings !clearwarns !permit "
    "!comando !timer !quote add"
)


def setup_basic_commands(bot):
    """Registrar comandos básicos"""

    @bot.command(name="hola")
    async def hello_command(ctx: commands.Context):
        """Saludo del bot"""
        await ctx.send(f"🕯️ El vacío saluda a {ctx.author.name}, el eco reconoce tu presencia.")

    @bot.command(name="ping")
    async def ping_command(ctx: commands.Context):
        """Verificar si el bot está vivo"""
        # Antes mostraba los milisegundos desde el arranque como si fuera latencia
        uptime = format_duration_long(time.time() - bot_start_time)
        await ctx.send(f"🕯️ Pong! El relicario lleva despierto {uptime}.")

    @bot.command(name="comandos", aliases=["commands", "help"])
    async def help_command(ctx: commands.Context):
        """Mostrar comandos disponibles (lista generada, incluye los personalizados)"""
        is_staff = permission_checker.is_staff(ctx.message)
        if not is_staff and not cooldowns.try_use("help", global_seconds=15):
            return

        from commands.custom import get_cached_commands
        custom = " ".join(f"!{name}" for name in sorted(get_cached_commands()))

        await ctx.send(f"🕯️ Ecos disponibles: {PUBLIC_COMMANDS}"[:500])
        if custom:
            await ctx.send(f"📜 Ecos del canal: {custom}"[:500])
        if is_staff:
            await ctx.send(f"🛡️ Ecos de guardianes: {STAFF_COMMANDS}"[:500])
