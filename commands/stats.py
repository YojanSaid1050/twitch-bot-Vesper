"""
Comandos de estadísticas
"""

from twitchio.ext import commands

from services.stats_service import stats_service


def setup_stats_commands(bot):
    """Registrar comandos de estadísticas"""
    
    @bot.command(name="uptime")
    async def uptime_command(ctx: commands.Context):
        """Mostrar tiempo de stream"""
        uptime_text = await stats_service.format_uptime()
        await ctx.send(uptime_text)
    
    @bot.command(name="viewers", aliases=["viewer", "espectadores"])
    async def viewers_command(ctx: commands.Context):
        """Mostrar número de espectadores"""
        viewers = await stats_service.get_viewer_count()
        
        if viewers == 0:
            await ctx.send("👁️ El altar yace en silencio... ningún alma contempla el ritual.")
        else:
            await ctx.send(f"👁️ {viewers} {'alma' if viewers == 1 else 'almas'} presencia{'n' if viewers != 1 else ''} el ritual en este momento.")