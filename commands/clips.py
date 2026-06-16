"""
Comandos para crear clips de Twitch
"""

from twitchio.ext import commands

from services.clip_service import clip_service
from services.stats_service import stats_service


def setup_clip_commands(bot):
    """Registrar comandos de clips"""
    
    @bot.command(name="clip", aliases=["clipnow", "crearclip"])
    async def create_clip(ctx: commands.Context):
        """Crear un clip del momento actual (todos pueden usar)"""
        
        # Verificar que el stream esté en vivo primero
        stream_info = await stats_service.get_stream_info()
        
        if not stream_info:
            await ctx.send("🕯️ El altar está vacío... No hay ritual activo para crear clips.")
            return
        
        await ctx.send("🎬 Conjurando un fragmento de tiempo... el clip está siendo creado.")
        
        # Crear el clip
        result = await clip_service.create_clip()
        
        if not result:
            await ctx.send("❌ El hechizo falló... no se pudo crear el clip.")
            return
        
        if not result.get("success"):
            error = result.get("error")
            
            if error == "offline":
                await ctx.send("🕯️ El ritual se detuvo... No se pueden crear clips cuando el altar está vacío.")
            elif error == "unauthorized":
                await ctx.send("❌ El altar no otorga permiso para crear clips. Contacta al invocador.")
            else:
                await ctx.send("❌ El hechizo falló... no se pudo crear el clip.")
            return
        
        # Éxito
        clip_url = result["url"]
        
        if clip_url.startswith("http"):
            await ctx.send(f"🎬 ¡El momento ha sido sellado! Clip creado: {clip_url} 🕯️")
        else:
            await ctx.send(f"🎬 {clip_url} 🕯️")
    
    @bot.command(name="cliptest")
    async def clip_test(ctx: commands.Context):
        """Verificar si el clip está disponible (solo staff)"""
        # Mantener restricción de staff para cliptest (opcional)
        # Si quieres que también cualquiera pueda usarlo, elimina esta verificación
        from bot.permissions import permission_checker
        if not permission_checker.is_staff(ctx.message):
            return
        
        # Verificar que el stream está en vivo
        stream_info = await stats_service.get_stream_info()
        
        if not stream_info:
            await ctx.send("🕯️ El altar está vacío. No hay stream en vivo para crear clips.")
        else:
            await ctx.send("✅ El ritual está activo. Los clips pueden ser conjurados con !clip")