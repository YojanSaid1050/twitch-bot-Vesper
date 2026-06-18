"""
Comandos básicos del bot
"""

from twitchio.ext import commands
import time

bot_start_time = time.time()


def setup_basic_commands(bot):
    """Registrar comandos básicos"""
    
    @bot.command(name="hola")
    async def hello_command(ctx: commands.Context):
        """Saludo del bot"""
        await ctx.send(f"🕯️ El vacío saluda a {ctx.author.name}, el eco reconoce tu presencia.")
    
    @bot.command(name="ping")
    async def ping_command(ctx: commands.Context):
        """Verificar si el bot está vivo"""
        response_time = round((time.time() - bot_start_time) * 1000)
        await ctx.send(f"🕯️ Pong! {response_time}ms desde que el relicario despertó.")
    
    @bot.command(name="comandos", aliases=["commands", "help"])
    async def help_command(ctx: commands.Context):
        """Mostrar comandos disponibles"""
        help_text = (
            "🕯️ Ecos disponibles: !hola, !ping, !8ball, !dado, !moneda, !elige, "
            "!lurk, !unlurk, !uptime, !viewers, !title, !game, !marker, "
            "!commercial, !slow, !followers, !emote, !subscribers, !timeout, !ban, "
            "!unban, !clear, !vip, !unvip, !shoutout, !announce, !warn, !warnings, "
            "!clearwarns, !comando, !discord, !twitter, !instagram, !youtube, !tiktok"
        )
        await ctx.send(help_text)