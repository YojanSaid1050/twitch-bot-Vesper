"""
Comandos para comerciales
"""

from twitchio.ext import commands

from services.commercial import CommercialManager
from exceptions import TwitchAPIError
from bot.permissions import permission_checker


def setup_commercial_commands(bot):
    """Registrar comandos de comerciales"""
    commercial_manager = CommercialManager()
    
    @bot.command(name="commercial", aliases=["com", "ad"])
    async def commercial_command(ctx: commands.Context):
        """Reproducir un comercial (solo staff)"""
        if not permission_checker.is_staff(ctx.message):
            return
        
        parts = ctx.message.content.split()
        duration = 30
        
        if len(parts) > 1:
            try:
                duration = int(parts[1])
                if duration not in commercial_manager.VALID_DURATIONS:
                    await ctx.send(f"❌ Duración inválida. Opciones: {commercial_manager.VALID_DURATIONS} segundos")
                    return
            except ValueError:
                await ctx.send(f"❌ Usa: !commercial [30|60|90|120|150|180]")
                return
        
        try:
            result = await commercial_manager.run_commercial(duration)
            duration_seconds = result["duration"]
            retry_after = result["retry_after"]
            
            if duration_seconds >= 60:
                duration_min = duration_seconds // 60
                await ctx.send(f"📺 El altar se cubre de un velo... comercial de {duration_min} minutos. El silencio durará {retry_after} segundos.")
            else:
                await ctx.send(f"📺 El altar se cubre de un velo... comercial de {duration_seconds} segundos. El silencio durará {retry_after} segundos.")
                
        except ValueError as e:
            await ctx.send(f"❌ {e}")
        except TwitchAPIError as e:
            if "only one commercial" in str(e).lower():
                await ctx.send("⏳ Ya hay un velo en curso. Espera unos segundos.")
            else:
                await ctx.send(f"❌ Error: {e.message}")