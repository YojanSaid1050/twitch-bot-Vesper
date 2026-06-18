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
    
    @bot.command(name="remove", aliases=["remover", "del"])
    async def remove_from_queue(ctx: commands.Context):
        """Eliminar canción de la cola por posición (solo mods, VIP y streamer)"""
        user_level = permission_checker.get_user_level(ctx.message)
        if user_level < PermissionLevel.VIP:
            await ctx.send("🕯️ Solo los elegidos (VIP, mods o el invocador) pueden retirar melodías de la cola.")
            return
        
        if not spotify_service.sp:
            await ctx.send("❌ El altar de Spotify no está invocado.")
            return
        
        parts = ctx.message.content.split()
        
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !remove <número de posición>")
            await ctx.send("🎵 Ejemplo: !remove 3 (elimina el canto en posición 3)")
            return
        
        try:
            position = int(parts[1])
            removed = spotify_service.remove_from_queue_by_position(position)
            
            if removed:
                await ctx.send(f"🗑️ {removed} ha sido borrada de la memoria del ritual.")
            else:
                await ctx.send(f"❌ Posición {position} inválida. La cola tiene {spotify_service.get_queue_count()} cantos.")
        except ValueError:
            await ctx.send("❌ Usa un número válido. Ejemplo: !remove 2")
    
    @bot.command(name="clearqueue", aliases=["limpiarcola", "clearcola"])
    async def clear_queue(ctx: commands.Context):
        """Limpiar toda la cola de Spotify (solo mods, VIP y streamer)"""
        user_level = permission_checker.get_user_level(ctx.message)
        if user_level < PermissionLevel.VIP:
            await ctx.send("🕯️ Solo los elegidos (VIP, mods o el invocador) pueden purificar la cola del ritual.")
            return
        
        if not spotify_service.sp:
            await ctx.send("❌ El altar de Spotify no está invocado.")
            return
        
        count = spotify_service.clear_queue()
        
        if count > 0:
            await ctx.send(f"🧹 {count} melodías han sido devueltas al silencio. El altar respira... 🕯️")
        else:
            await ctx.send("🕯️ La cola ya estaba vacía... no hay nada que limpiar.")
    
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