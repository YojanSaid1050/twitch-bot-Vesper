"""
Comandos relacionados con la gestión del stream
"""

from twitchio.ext import commands

from services import StreamManager
from exceptions import ResourceNotFoundError, TwitchAPIError
from utils import validate_title, validate_game_name
from bot.permissions import permission_checker, PermissionLevel


def setup_stream_commands(bot):
    """Registrar comandos de stream"""
    stream_manager = StreamManager()
    
    @bot.command(name="title")
    async def title_command(ctx: commands.Context):
        """Cambiar título del stream (solo staff)"""
        # Verificar permisos
        if not permission_checker.is_staff(ctx.message):
            return
        
        # Extraer título (todo después del comando)
        parts = ctx.message.content.split(" ", 1)
        
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !title Nuevo título del stream")
            return
        
        title = parts[1].strip()
        
        # Validar título
        is_valid, error_msg = validate_title(title)
        if not is_valid:
            await ctx.send(f"❌ {error_msg}")
            return
        
        try:
            await stream_manager.update_title(title)
            await ctx.send(f"🕯️ The stream’s fate has been rewritten: {title}")
        except TwitchAPIError as e:
            await ctx.send(f"❌ Error: {e.message}")
    
    @bot.command(name="game", aliases=["juego", "category"])
    async def game_command(ctx: commands.Context):
        """Cambiar categoría/juego del stream (solo staff)"""
        if not permission_checker.is_staff(ctx.message):
            return
        
        parts = ctx.message.content.split(" ", 1)
        
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !game VALORANT")
            return
        
        game_name = parts[1].strip()
        
        # Validar nombre
        is_valid, error_msg = validate_game_name(game_name)
        if not is_valid:
            await ctx.send(f"❌ {error_msg}")
            return
        
        try:
            game_id, actual_name = await stream_manager.update_game(game_name)
            await ctx.send(f"⚔️ The descent continues into: {actual_name}")
        except ResourceNotFoundError:
            await ctx.send("❌ No echo responds from the void (category not found).")
        except TwitchAPIError as e:
            await ctx.send(f"❌ Error: {e.message}")
    
    @bot.command(name="marker")
    async def marker_command(ctx: commands.Context):
        """Crear un marker en el stream (solo staff)"""
        if not permission_checker.is_staff(ctx.message):
            return
        
        try:
            marker_id = await stream_manager.create_marker()
            await ctx.send("🔥 A fragment of time has been sealed in silence.")
        except TwitchAPIError as e:
            await ctx.send(f"❌ Error: {e.message}")