"""
Comandos para integración con Spotify (Song Request)
"""

from twitchio.ext import commands

from services.spotify_service import spotify_service
from bot.permissions import permission_checker, PermissionLevel
from utils.logger import get_logger

logger = get_logger(__name__)


def setup_spotify_commands(bot):
    """Registrar comandos de Spotify"""
    
    @bot.command(name="sr", aliases=["songrequest", "spotify"])
    async def song_request(ctx: commands.Context):
        """
        Solicitar una canción en Spotify (todos pueden usar)
        
        Uso: !sr <nombre de canción o artista>
        Ejemplo: !sr Bohemian Rhapsody
        """
        parts = ctx.message.content.split(" ", 1)
        
        if len(parts) < 2:
            await ctx.send("🕯️ Uso: !sr <nombre de canción o artista>")
            await ctx.send("🎵 Ejemplo: !sr Bohemian Rhapsody")
            return
        
        query = parts[1].strip()
        
        # Verificar que Spotify está configurado
        if not spotify_service.sp:
            await ctx.send("❌ Spotify no está configurado. Contacta al streamer.")
            return
        
        await ctx.send(f"🎵 Buscando '{query}' en el abismo...")
        
        # Buscar la canción
        track = spotify_service.search_track(query)
        
        if not track:
            await ctx.send(f"❌ El eco no responde... '{query}' no se encontró en el reino musical.")
            return
        
        # Verificar si ya está en la cola
        if spotify_service.is_track_in_queue(track['id']):
            await ctx.send(f"⚠️ {track['name']} - {track['artist']} ya aguarda en la cola del ritual. No se puede conjurar dos veces la misma melodía.")
            return
        
        # Verificar si ya fue reproducida recientemente
        in_history, position = spotify_service.is_track_in_history(track['id'])
        
        if in_history:
            # Calcular cuántas canciones faltan para que salga del historial
            remaining = 10 - position + 1
            await ctx.send(
                f"⚠️ {track['name']} - {track['artist']} ya resonó en el altar recientemente. "
                f"El eco aún perdura, espera un poco. ({remaining} canciones para conjurarla de nuevo)"
            )
            return
        
        # Añadir a la cola
        success = spotify_service.add_to_queue(track['id'], track)
        
        if success:
            duration_seconds = track['duration_ms'] // 1000
            duration_min = duration_seconds // 60
            duration_sec = duration_seconds % 60
            
            await ctx.send(
                f"🎵 {ctx.author.name} ha conjurado {track['name']} - {track['artist']} "
                f"({duration_min}:{duration_sec:02d}) en la cola del ritual 🕯️"
            )
        else:
            await ctx.send(
                f"⚠️ El hechizo falló... Asegúrate de que Spotify esté abierto y la música fluya en el altar."
            )
    
    @bot.command(name="current", aliases=["nowplaying", "np"])
    async def current_track(ctx: commands.Context):
        """Mostrar canción actual de Spotify (todos pueden usar)"""
        if not spotify_service.sp:
            await ctx.send("❌ Spotify no está configurado en el reino.")
            return
        
        track = spotify_service.get_current_track()
        
        if not track:
            await ctx.send("🕯️ El silencio reina... no hay música en el altar en este momento.")
        else:
            await ctx.send(f"🎵 Actualmente sonando en el ritual: {track['name']} - {track['artist']} 🕯️")
    
    @bot.command(name="skip", aliases=["next"])
    async def skip_track(ctx: commands.Context):
        """Saltar a la siguiente canción (solo mods, VIP y streamer)"""
        # Verificar nivel de permiso (mod, VIP o streamer)
        user_level = permission_checker.get_user_level(ctx.message)
        if user_level < PermissionLevel.VIP:
            await ctx.send("🕯️ Solo los elegidos (VIP, mods o el invocador) pueden invocar el siguiente encantamiento.")
            return
        
        if not spotify_service.sp:
            await ctx.send("❌ Spotify no está configurado en el reino.")
            return
        
        success = spotify_service.skip_track()
        
        if success:
            await ctx.send("⏭️ La melodía cesa... siguiente encantamiento en el altar 🎵")
        else:
            await ctx.send("❌ El hechizo falló... no se pudo invocar la siguiente canción.")
    
    @bot.command(name="pause")
    async def pause_playback(ctx: commands.Context):
        """Pausar la música (solo mods, VIP y streamer)"""
        # Verificar nivel de permiso (mod, VIP o streamer)
        user_level = permission_checker.get_user_level(ctx.message)
        if user_level < PermissionLevel.VIP:
            await ctx.send("🕯️ Solo los elegidos (VIP, mods o el invocador) pueden pausar el ritual.")
            return
        
        if not spotify_service.sp:
            await ctx.send("❌ Spotify no está configurado en el reino.")
            return
        
        if not spotify_service.is_playing():
            await ctx.send("🕯️ El altar ya está en silencio... no hay música que pausar.")
            return
        
        success = spotify_service.pause_playback()
        
        if success:
            await ctx.send("⏸️ El ritual se detiene... la música descansa en el altar. 🕯️")
        else:
            await ctx.send("❌ No se pudo pausar la melodía. ¿El hechizo se resiste?")
    
    @bot.command(name="resume", aliases=["play"])
    async def resume_playback(ctx: commands.Context):
        """Reanudar la música (solo mods, VIP y streamer)"""
        # Verificar nivel de permiso (mod, VIP o streamer)
        user_level = permission_checker.get_user_level(ctx.message)
        if user_level < PermissionLevel.VIP:
            await ctx.send("🕯️ Solo los elegidos (VIP, mods o el invocador) pueden reanudar el ritual.")
            return
        
        if not spotify_service.sp:
            await ctx.send("❌ Spotify no está configurado en el reino.")
            return
        
        if spotify_service.is_playing():
            await ctx.send("🎵 La música ya fluye en el altar... no es necesario reanudar.")
            return
        
        success = spotify_service.resume_playback()
        
        if success:
            await ctx.send("▶️ El ritual continúa... la música vuelve a fluir en el altar. 🎵")
        else:
            await ctx.send("❌ No se pudo reanudar la melodía. ¿El hechizo se resiste?")