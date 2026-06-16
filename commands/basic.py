"""
Comandos básicos del bot
"""

from twitchio.ext import commands
import time

# Almacenar tiempo de inicio del bot
bot_start_time = time.time()


def setup_basic_commands(bot):
    """Registrar comandos básicos"""
    
    @bot.command(name="hola")
    async def hello_command(ctx: commands.Context):
        """Saludo del bot"""
        await ctx.send(f"🕯️ Greetings, {ctx.author.name}… the silence acknowledges you.")
    
    @bot.command(name="ping")
    async def ping_command(ctx: commands.Context):
        """Verificar si el bot está vivo"""
        response_time = round((time.time() - bot_start_time) * 1000)
        await ctx.send(f"🕯️ Pong! {response_time}ms desde inicio")
    
    @bot.command(name="comandos", aliases=["commands", "help"])
    async def help_command(ctx: commands.Context):
        """Mostrar comandos disponibles"""
        help_text = (
            "🕯️ Comandos disponibles: !hola, !ping, !8ball, !dado, !moneda, !elige, "
            "!lurk, !unlurk, !uptime, !viewers, !title, !game, !marker, "
            "!commercial, !slow, !followers, !emote, !subscribers, !timeout, !ban, "
            "!unban, !clear, !vip, !unvip, !shoutout, !announce, !warn, !warnings, "
            "!clearwarns, !comando, !discord, !twitter, !instagram, !youtube, !tiktok"
        )
        await ctx.send(help_text)