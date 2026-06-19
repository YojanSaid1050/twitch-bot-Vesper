"""
Comandos relacionados con la gestión del stream
"""

from twitchio.ext import commands

from services import StreamManager
from services.log_service import log_service
from exceptions import ResourceNotFoundError, TwitchAPIError
from utils import validate_title, validate_game_name
from bot.permissions import permission_checker, PermissionLevel


def setup_stream_commands(bot):
    """Registrar comandos de stream"""
    stream_manager = StreamManager()
    
    @bot.command(name="title")
    async def title_command(ctx: commands.Context):
        """Cambiar título del stream (solo staff)"""
        if not permission_checker.is_staff(ctx.message):
            return
        
        parts = ctx.message.content.split(" ", 1)
        
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !title Nuevo título del ritual")
            return
        
        title = parts[1].strip()
        author = ctx.author.name
        
        is_valid, error_msg = validate_title(title)
        if not is_valid:
            await ctx.send(f"❌ {error_msg}")
            return
        
        try:
            await stream_manager.update_title(title)
            await ctx.send(f"🕯️ El destino del ritual ha sido reescrito: {title}")
            log_service.add_log('info', f'Título del stream cambiado a "{title}" por {author}', 'moderation')
        except TwitchAPIError as e:
            await ctx.send(f"❌ Error: {e.message}")
            log_service.add_log('error', f'Error de Twitch al cambiar título: {e.message}', 'twitch_api')
        except Exception as e:
            await ctx.send(f"❌ Error inesperado: {e}")
            log_service.add_log('error', f'Error inesperado al cambiar título: {e}', 'bot')
    
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
        author = ctx.author.name
        
        is_valid, error_msg = validate_game_name(game_name)
        if not is_valid:
            await ctx.send(f"❌ {error_msg}")
            return
        
        try:
            game_id, actual_name = await stream_manager.update_game(game_name)
            await ctx.send(f"⚔️ El descenso continúa hacia: {actual_name}")
            log_service.add_log('info', f'Juego del stream cambiado a "{actual_name}" por {author}', 'moderation')
        except ResourceNotFoundError:
            await ctx.send("❌ El vacío no responde... categoría no encontrada.")
            log_service.add_log('warning', f'Categoría no encontrada: {game_name}', 'twitch_api')
        except TwitchAPIError as e:
            await ctx.send(f"❌ Error: {e.message}")
            log_service.add_log('error', f'Error de Twitch al cambiar juego: {e.message}', 'twitch_api')
        except Exception as e:
            await ctx.send(f"❌ Error inesperado: {e}")
            log_service.add_log('error', f'Error inesperado al cambiar juego: {e}', 'bot')
    
    @bot.command(name="marker")
    async def marker_command(ctx: commands.Context):
        """Crear un marker en el stream (solo staff)"""
        if not permission_checker.is_staff(ctx.message):
            return
        
        author = ctx.author.name
        
        try:
            marker_id = await stream_manager.create_marker()
            await ctx.send("🔮 Un fragmento de tiempo ha sido sellado en el silencio.")
            log_service.add_log('info', f'Marker creado por {author} (ID: {marker_id})', 'bot')  # Sistema
        except TwitchAPIError as e:
            await ctx.send(f"❌ Error: {e.message}")
            log_service.add_log('error', f'Error de Twitch al crear marker: {e.message}', 'twitch_api')
        except Exception as e:
            await ctx.send(f"❌ Error inesperado: {e}")
            log_service.add_log('error', f'Error inesperado al crear marker: {e}', 'bot')