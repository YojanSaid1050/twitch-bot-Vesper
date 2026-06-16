"""
Módulo de comandos del bot
"""

from .basic import setup_basic_commands
from .stream import setup_stream_commands
from .moderation import setup_moderation_commands
from .commercial import setup_commercial_commands
from .interaction import setup_interaction_commands
from .stats import setup_stats_commands
from .staff import setup_staff_commands
from .custom import setup_custom_commands
from .social import setup_social_commands
from .spotify_controls import setup_spotify_controls
from .clips import setup_clip_commands

# Intentar importar comandos de Spotify (opcional)
try:
    from .spotify import setup_spotify_commands
    SPOTIFY_AVAILABLE = True
except ImportError:
    SPOTIFY_AVAILABLE = False
    print("⚠️ Spotify no disponible. Instala spotipy: pip install spotipy")


def register_commands(bot):
    """Registrar todos los comandos"""
    setup_basic_commands(bot)
    setup_stream_commands(bot)
    setup_moderation_commands(bot)
    setup_commercial_commands(bot)
    setup_interaction_commands(bot)
    setup_stats_commands(bot)
    setup_staff_commands(bot)
    setup_custom_commands(bot)
    setup_social_commands(bot)
    setup_spotify_controls(bot)
    setup_clip_commands(bot)
    
    if SPOTIFY_AVAILABLE:
        setup_spotify_commands(bot)