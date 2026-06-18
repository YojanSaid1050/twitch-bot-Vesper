"""
Comandos de control de Spotify (cola, volumen, etc)
"""

from twitchio.ext import commands

from services.spotify_service import spotify_service
from bot.permissions import permission_checker, PermissionLevel


def setup_spotify_controls(bot):
    """Registrar comandos de control de Spotify"""
    
    @bot.command(name="queue", aliases=["cola", "q"])
    async def show_queue(ctx: commands.Context):
        """Mostrar cola actual de Spotify (todos pueden usar)"""
        if not spotify_service.sp:
            await ctx.send("❌ El altar de Spotify no está invocado.")
            return
        
        queue_list = spotify_service.get_queue_list()
        
        if not queue_list:
            await ctx.send("🕯️ La cola del ritual está vacía... ¡Invoca música con !sr!")
            return
        
        if len(queue_list) <= 5:
            songs = [f"{q['position']}. {q['name']} - {q['artist']}" for q in queue_list]
            await ctx.send(f"🎵 Cola del ritual ({len(queue_list)} cantos): {', '.join(songs)}")
        else:
            await ctx.send(f"🎵 Cola del ritual ({len(queue_list)} cantos):")
            for q in queue_list[:5]:
                await ctx.send(f"  {q['position']}. {q['name']} - {q['artist']}")
            remaining = len(queue_list) - 5
            if remaining > 0:
                await ctx.send(f"  ... y {remaining} cantos más. Usa !queue para ver todos en el susurro privado.")
    
    @bot.command(name="volumen", aliases=["volume", "vol"])
    async def set_volume(ctx: commands.Context):
        """Ajustar volumen de Spotify (solo mods, VIP y streamer)"""
        user_level = permission_checker.get_user_level(ctx.message)
        if user_level < PermissionLevel.VIP:
            await ctx.send("🕯️ Solo los elegidos (VIP, mods o el invocador) pueden controlar la fuerza del sonido.")
            return
        
        if not spotify_service.sp:
            await ctx.send("❌ El altar de Spotify no está invocado.")
            return
        
        parts = ctx.message.content.split()
        
        if len(parts) < 2:
            current_vol = spotify_service.get_volume()
            if current_vol is not None:
                await ctx.send(f"🎵 Volumen actual del altar: {current_vol}%")
            else:
                await ctx.send("🎵 No se pudo obtener el volumen actual. ¿Hay música sonando?")
            return
        
        try:
            volume = int(parts[1])
            if volume < 0 or volume > 100:
                await ctx.send("❌ El volumen debe estar entre 0 y 100.")
                return
            
            success = spotify_service.set_volume(volume)
            
            if success:
                await ctx.send(f"🔊 Volumen del altar ajustado a {volume}%")
            else:
                await ctx.send("❌ El hechizo no surtió efecto... no se pudo ajustar el altar.")
        except ValueError:
            await ctx.send("❌ Usa un número entre 0 y 100. Ejemplo: !volumen 50")