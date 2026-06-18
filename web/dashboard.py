"""
Dashboard de configuración para el bot de Twitch
Se ejecuta en el mismo proceso que el bot
"""

import os
import sys
import asyncio
import time
import hmac
import hashlib
from pathlib import Path
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import timedelta, datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import get_logger
from services.config_service import config_service
from services.spotify_service import spotify_service
from services.stats_service import stats_service
from services.twitch_api import TwitchAPI
from services.link_manager import link_manager
from services.log_service import log_service
from services.warning_manager import warning_manager
from services.token_manager import token_manager
from exceptions import TwitchAPIError, AuthenticationError

logger = get_logger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv("DASHBOARD_SECRET_KEY", "supersecretkey_change_me")
app.permanent_session_lifetime = timedelta(hours=1)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor inicia sesión'


class User(UserMixin):
    def __init__(self, id):
        self.id = id
        self.username = "admin"


@login_manager.user_loader
def load_user(user_id):
    return User(user_id)


# Variable global para la instancia del bot
_bot_instance = None
_tokens_ready = False

# Caché para datos de Spotify
_spotify_cache = {
    'data': None,
    'timestamp': 0,
    'ttl': 10  # segundos
}


def set_bot_instance(bot):
    global _bot_instance
    _bot_instance = bot


def wait_for_tokens(timeout=60):
    global _tokens_ready
    logger.info(f"⏳ Esperando hasta {timeout}s a que los tokens sean válidos...")
    start = time.time()
    while time.time() - start < timeout:
        if token_manager.are_tokens_valid():
            _tokens_ready = True
            logger.info("✅ Tokens válidos, dashboard listo.")
            return True
        if token_manager._can_refresh():
            logger.info("🔄 Intentando refrescar tokens...")
            token_manager.refresh_all_tokens()
        time.sleep(2)
    logger.warning("⚠️ Timeout esperando tokens válidos. El dashboard puede tener errores.")
    _tokens_ready = token_manager.are_tokens_valid()
    return _tokens_ready


def get_cached_spotify_data(force_refresh=False):
    global _spotify_cache
    now = time.time()
    if not force_refresh and _spotify_cache['data'] is not None:
        if now - _spotify_cache['timestamp'] < _spotify_cache['ttl']:
            return _spotify_cache['data']
    
    data = {
        'current': None,
        'queue': spotify_service.get_queue_list() if spotify_service else [],
        'is_playing': False,
        'progress_ms': 0,
        'duration_ms': 0
    }
    if spotify_service:
        playback = spotify_service.get_playback_state()
        if playback and playback.get('track'):
            track = playback['track']
            data['current'] = {
                'name': track.get('name'),
                'artist': track.get('artist'),
                'id': track.get('id'),
                'url': track.get('url'),
                'duration_ms': track.get('duration_ms'),
                'is_playing': playback.get('is_playing', False)
            }
            data['is_playing'] = playback.get('is_playing', False)
            data['progress_ms'] = track.get('progress_ms', 0)
            data['duration_ms'] = track.get('duration_ms', 0)
        else:
            data['is_playing'] = False
    _spotify_cache['data'] = data
    _spotify_cache['timestamp'] = now
    return data


# ============================================
# RUTAS DE PÁGINAS
# ============================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        password = request.form.get('password', '')
        stored_password = config_service.get_dashboard_password()
        if password == stored_password:
            user = User(1)
            login_user(user)
            session.permanent = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='❌ Contraseña incorrecta')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    return render_template('index.html')


@app.route('/commands')
@login_required
def commands_page():
    return render_template('commands.html')


@app.route('/spotify')
@login_required
def spotify_page():
    return render_template('spotify.html')


@app.route('/moderation')
@login_required
def moderation_page():
    return render_template('moderation.html')


@app.route('/stats')
@login_required
def stats_page():
    return render_template('stats.html')


@app.route('/settings')
@login_required
def settings_page():
    return render_template('settings.html')


@app.route('/logs')
@login_required
def logs_page():
    return render_template('logs.html')


# ============================================
# API UNIFICADA (dashboard-data)
# ============================================

@app.route('/api/dashboard-data')
@login_required
def api_dashboard_data():
    force_refresh = request.args.get('force', 'false').lower() == 'true'
    if not _tokens_ready:
        if token_manager._can_refresh():
            logger.info("🔄 Tokens no listos, forzando refresco desde el dashboard...")
            token_manager.refresh_all_tokens()
        if not token_manager.are_tokens_valid():
            logger.warning("⚠️ Tokens no válidos. Devolviendo datos limitados.")
            return jsonify({
                'error': 'Tokens no válidos. Esperando refresco...',
                'timestamp': datetime.now().isoformat(),
                'status': {'connected': False, 'live': False, 'viewers': 0, 'game': 'Error', 'title': 'Error', 'uptime': 'Error'},
                'stats': {'followers': 0, 'subscribers': 0, 'commands': 0, 'banned_words': 0, 'spotify_tracks': 0, 'cheers': 0},
                'moderation': {'banned': [], 'timeouts': [], 'link_warnings': [], 'all_warnings': [], 'bot_banned': [], 'bot_timeouts': []},
                'spotify': {'current': None, 'queue': [], 'is_playing': False, 'progress_ms': 0, 'duration_ms': 0},
                'settings': {},
                'social_links': {},
                'last_follower': 'Esperando...',
                'last_subscriber': 'Esperando...',
                'stats_history': []
            })
    
    try:
        api = TwitchAPI(use_broadcaster_token=True)
        data = {
            'timestamp': datetime.now().isoformat(),
            'status': {
                'connected': True,
                'live': False,
                'viewers': 0,
                'game': 'No especificado',
                'title': 'Sin título',
                'uptime': 'Offline'
            },
            'stats': {
                'followers': 0,
                'subscribers': 0,
                'commands': 0,
                'banned_words': 0,
                'spotify_tracks': 0,
                'cheers': 0
            },
            'moderation': {
                'banned': [],
                'timeouts': [],
                'link_warnings': [],
                'all_warnings': [],
                'bot_banned': [],
                'bot_timeouts': []
            },
            'spotify': {
                'current': None,
                'queue': [],
                'is_playing': False,
                'progress_ms': 0,
                'duration_ms': 0
            },
            'settings': {
                'slow_mode': {'enabled': False, 'seconds': 10},
                'follower_mode': {'enabled': False, 'minutes': 10},
                'emote_mode': False,
                'subscriber_mode': False,
                'max_warnings': 3,
                'banned_words': []
            },
            'social_links': {},
            'last_follower': 'Esperando...',
            'last_subscriber': 'Esperando...'
        }
        
        # --- Obtener estado del stream ---
        def fetch_stream_info(retry=True):
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                stream_info = loop.run_until_complete(stats_service.get_stream_info())
                loop.close()
                return stream_info
            except AuthenticationError:
                if retry:
                    logger.warning("🔑 Token del streamer expirado, intentando refrescar...")
                    if token_manager.force_refresh_broadcaster_if_needed():
                        return fetch_stream_info(retry=False)
                raise
            except Exception as e:
                logger.debug(f"Stream info no disponible: {e}")
                return None
        
        stream_info = fetch_stream_info()
        
        def fetch_channel_info(retry=True):
            try:
                channel_result = api.get(
                    "channels",
                    params={"broadcaster_id": stats_service.broadcaster_id}
                )
                if channel_result and "data" in channel_result and channel_result["data"]:
                    return channel_result["data"][0]
                return None
            except AuthenticationError:
                if retry:
                    logger.warning("🔑 Token del streamer expirado al obtener canal, intentando refrescar...")
                    if token_manager.force_refresh_broadcaster_if_needed():
                        return fetch_channel_info(retry=False)
                raise
            except Exception as e:
                logger.error(f"Error obteniendo canal info: {e}")
                log_service.add_log('error', f'Error obteniendo info del canal: {e}', 'twitch_api')
                return None
        
        channel_info = fetch_channel_info()
        
        if stream_info:
            data['status']['live'] = True
            data['status']['viewers'] = stream_info.get("viewer_count", 0)
            data['status']['game'] = stream_info.get("game_name", "No especificado")
            data['status']['title'] = stream_info.get("title", "Sin título")
            started_at = stream_info.get("started_at")
            if started_at:
                try:
                    start_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                    uptime = datetime.now().astimezone() - start_time
                    hours = uptime.seconds // 3600
                    minutes = (uptime.seconds % 3600) // 60
                    data['status']['uptime'] = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
                except:
                    data['status']['uptime'] = "En vivo"
            else:
                data['status']['uptime'] = "En vivo"
        else:
            data['status']['live'] = False
            data['status']['title'] = channel_info.get("title", "Sin título") if channel_info else "Sin título"
            data['status']['game'] = channel_info.get("game_name", "No especificado") if channel_info else "No especificado"
            data['status']['uptime'] = "Offline"
        
        # --- Estadísticas ---
        def safe_api_call(func, *args, **kwargs):
            try:
                return func(*args, **kwargs)
            except AuthenticationError:
                logger.warning("🔑 Token expirado, refrescando...")
                token_manager.force_refresh_broadcaster_if_needed()
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error en llamada API después de refrescar: {e}")
                    return None
            except Exception as e:
                logger.debug(f"Error en llamada API: {e}")
                return None
        
        # Seguidores
        followers_result = safe_api_call(
            api.get, "channels/followers",
            params={"broadcaster_id": stats_service.broadcaster_id}
        )
        if followers_result and "total" in followers_result:
            data['stats']['followers'] = followers_result["total"]
        
        # Último seguidor
        followers_result = safe_api_call(
            api.get, "channels/followers",
            params={"broadcaster_id": stats_service.broadcaster_id, "first": 1}
        )
        if followers_result and "data" in followers_result and followers_result["data"]:
            last = followers_result["data"][0]
            data['last_follower'] = last.get('user_name', 'Desconocido')
        
        # Suscriptores
        subscribers_result = safe_api_call(
            api.get, "subscriptions",
            params={"broadcaster_id": stats_service.broadcaster_id}
        )
        if subscribers_result and "total" in subscribers_result:
            data['stats']['subscribers'] = subscribers_result["total"]
        
        # Último suscriptor
        subscribers_result = safe_api_call(
            api.get, "subscriptions",
            params={"broadcaster_id": stats_service.broadcaster_id, "first": 1}
        )
        if subscribers_result and "data" in subscribers_result and subscribers_result["data"]:
            last = subscribers_result["data"][0]
            data['last_subscriber'] = last.get('user_name', 'Desconocido')
        else:
            data['last_subscriber'] = 'Sin suscriptores' if data['stats']['subscribers'] == 0 else 'Esperando...'
        
        # Cheers/Bits
        cheers_result = safe_api_call(
            api.get, "bits/leaderboard",
            params={"broadcaster_id": stats_service.broadcaster_id, "period": "all"}
        )
        if cheers_result and "data" in cheers_result:
            total_bits = sum(item.get('score', 0) for item in cheers_result["data"])
            data['stats']['cheers'] = total_bits
        else:
            cheers_result = safe_api_call(
                api.get, "bits/leaderboard",
                params={"broadcaster_id": stats_service.broadcaster_id}
            )
            if cheers_result and "data" in cheers_result:
                total_bits = sum(item.get('score', 0) for item in cheers_result["data"])
                data['stats']['cheers'] = total_bits
        
        # Comandos personalizados
        data['stats']['commands'] = len(config_service.get_custom_commands())
        data['stats']['banned_words'] = len(config_service.get_banned_words())
        
        # --- Spotify (con caché) ---
        spotify_cache = get_cached_spotify_data(force_refresh=force_refresh)
        data['spotify'] = spotify_cache
        data['stats']['spotify_tracks'] = len(spotify_cache.get('queue', []))
        
        # --- Moderación ---
        try:
            twitch_banned = link_manager.get_twitch_banned_users()
            for user in twitch_banned:
                if user.get('end_time') is None:
                    data['moderation']['banned'].append({
                        'user_id': user.get('user_id'),
                        'user_name': user.get('user_login', user.get('user_name', 'Desconocido')),
                        'reason': user.get('reason', 'No especificada')
                    })
        except Exception as e:
            logger.error(f"Error obteniendo baneados de Twitch: {e}")
            log_service.add_log('error', f'Error obteniendo baneados de Twitch: {e}', 'link_manager')
        
        try:
            twitch_timeouts = link_manager.get_twitch_timeouts()
            for user in twitch_timeouts:
                data['moderation']['timeouts'].append({
                    'user_id': user.get('user_id'),
                    'user_name': user.get('user_name', user.get('user_login', 'Desconocido')),
                    'reason': user.get('reason', 'No especificada'),
                    'remaining_seconds': user.get('remaining_seconds', 0),
                    'remaining_formatted': link_manager._format_remaining(user.get('remaining_seconds', 0))
                })
        except Exception as e:
            logger.error(f"Error obteniendo timeouts de Twitch: {e}")
            log_service.add_log('error', f'Error obteniendo timeouts de Twitch: {e}', 'link_manager')
        
        # Todas las advertencias (warning_manager)
        try:
            all_warnings = warning_manager.get_all_warnings_summary()
            for user_id, warn_data in all_warnings.items():
                total_warnings = sum(warn_data['warnings'].values())
                types = []
                type_details = {}
                for t, count in warn_data['warnings'].items():
                    type_names = {
                        'link': 'Enlaces',
                        'word': 'Palabras prohibidas',
                        'caps': 'Mayúsculas excesivas',
                        'rate': 'Spam (velocidad)',
                        'repeat': 'Mensajes repetidos'
                    }
                    type_display = type_names.get(t, t)
                    types.append(f"{type_display}: {count}")
                    type_details[t] = count
                data['moderation']['all_warnings'].append({
                    'user_id': user_id,
                    'user_name': warn_data.get('user_name', user_id),
                    'warnings': total_warnings,
                    'max_warnings': warning_manager.get_max_warnings(),
                    'types': types,
                    'detail': type_details
                })
        except Exception as e:
            logger.error(f"Error obteniendo todas las advertencias: {e}")
            log_service.add_log('error', f'Error obteniendo todas las advertencias: {e}', 'link_manager')
        
        # Baneados y timeouts del bot (link_manager)
        try:
            bot_banned = link_manager.get_banned_users()
            for user_id, ban_data in bot_banned.items():
                data['moderation']['bot_banned'].append({
                    'user_id': user_id,
                    'user_name': ban_data.get('name', 'Desconocido'),
                    'reason': ban_data.get('reason', 'Enlaces no permitidos'),
                    'banned_at': ban_data.get('banned_at', '')
                })
        except Exception as e:
            logger.error(f"Error obteniendo baneados del bot: {e}")
            log_service.add_log('error', f'Error obteniendo baneados del bot: {e}', 'link_manager')
        
        try:
            bot_timeouts = link_manager.get_timeout_users_with_names()
            for user_id, timeout_data in bot_timeouts.items():
                data['moderation']['bot_timeouts'].append({
                    'user_id': user_id,
                    'user_name': timeout_data.get('user_name', user_id),
                    'remaining_seconds': int(timeout_data.get('remaining', 0)),
                    'remaining_formatted': timeout_data.get('remaining_formatted', '0s')
                })
        except Exception as e:
            logger.error(f"Error obteniendo timeouts del bot: {e}")
            log_service.add_log('error', f'Error obteniendo timeouts del bot: {e}', 'link_manager')
        
        # --- Configuración ---
        data['settings']['slow_mode'] = config_service.get_slow_mode()
        data['settings']['follower_mode'] = config_service.get_follower_mode()
        data['settings']['emote_mode'] = config_service.get_emote_mode()
        data['settings']['subscriber_mode'] = config_service.get_subscriber_mode()
        data['settings']['max_warnings'] = config_service.get_max_warnings()
        data['settings']['banned_words'] = config_service.get_banned_words()
        
        # --- Enlaces sociales ---
        data['social_links'] = {
            'discord': config_service.get_social_link('discord'),
            'twitter': config_service.get_social_link('twitter'),
            'instagram': config_service.get_social_link('instagram'),
            'youtube': config_service.get_social_link('youtube'),
            'tiktok': config_service.get_social_link('tiktok')
        }
        
        # --- Historial de estadísticas ---
        try:
            config_service.add_stats_snapshot(
                data['stats']['followers'],
                data['stats']['subscribers'],
                data['stats']['cheers']
            )
        except Exception as e:
            logger.debug(f"Error guardando historial: {e}")
            log_service.add_log('warning', f'Error guardando historial de estadísticas: {e}', 'config_service')
        
        data['stats_history'] = config_service.get_stats_history(limit=7)
        
        return jsonify(data)
        
    except Exception as e:
        logger.error(f"Error en /api/dashboard-data: {e}")
        log_service.add_log('critical', f'Error crítico en /api/dashboard-data: {e}', 'dashboard')
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'status': {'connected': False, 'live': False, 'viewers': 0, 'game': 'Error', 'title': 'Error', 'uptime': 'Error'},
            'stats': {'followers': 0, 'subscribers': 0, 'commands': 0, 'banned_words': 0, 'spotify_tracks': 0, 'cheers': 0},
            'moderation': {'banned': [], 'timeouts': [], 'link_warnings': [], 'all_warnings': [], 'bot_banned': [], 'bot_timeouts': []},
            'spotify': {'current': None, 'queue': [], 'is_playing': False, 'progress_ms': 0, 'duration_ms': 0},
            'settings': {},
            'social_links': {},
            'last_follower': 'Esperando...',
            'last_subscriber': 'Esperando...',
            'stats_history': []
        }), 500


# ============================================
# ENDPOINTS DE WARNINGS
# ============================================

@app.route('/api/warnings/<user_id>', methods=['DELETE'])
@login_required
def api_delete_warnings(user_id):
    try:
        data = request.json or {}
        warning_type = data.get('type')
        count = data.get('count', 0)
        
        if warning_type:
            if count > 0:
                current = warning_manager.get_warning_count(user_id, warning_type)
                new_count = max(0, current - count)
                if new_count == 0:
                    warning_manager.clear_warnings(user_id, warning_type)
                else:
                    warnings = warning_manager.warnings
                    if user_id in warnings and warning_type in warnings[user_id]:
                        warnings[user_id][warning_type] = new_count
                    warning_manager._save_data()
                log_service.add_log('info', f'Advertencias de tipo {warning_type} reducidas a {new_count} para usuario {user_id}', 'dashboard')
                return jsonify({
                    'success': True,
                    'message': f'Advertencias de tipo {warning_type} reducidas a {new_count}'
                })
            else:
                count_removed = warning_manager.clear_warnings(user_id, warning_type)
                log_service.add_log('info', f'Todas las advertencias de tipo {warning_type} eliminadas para usuario {user_id} ({count_removed} eliminadas)', 'dashboard')
                return jsonify({
                    'success': True,
                    'message': f'Todas las advertencias de tipo {warning_type} eliminadas ({count_removed})'
                })
        else:
            total = 0
            if user_id in warning_manager.warnings:
                total = sum(warning_manager.warnings[user_id].values())
                del warning_manager.warnings[user_id]
                warning_manager._save_data()
            log_service.add_log('info', f'Todas las advertencias eliminadas para usuario {user_id} ({total})', 'dashboard')
            return jsonify({
                'success': True,
                'message': f'Todas las advertencias eliminadas ({total})'
            })
    except Exception as e:
        logger.error(f"Error eliminando advertencias: {e}")
        log_service.add_log('error', f'Error eliminando advertencias: {e}', 'dashboard')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/link/warnings/<user_id>', methods=['DELETE'])
@login_required
def api_clear_link_warnings(user_id):
    try:
        data = request.json
        count = data.get('count', 0)
        if count == 0:
            removed = link_manager.clear_warnings(user_id)
            log_service.add_log('info', f'Advertencias de enlaces limpiadas para usuario {user_id}', 'dashboard')
            return jsonify({'message': f'Advertencias limpiadas: {removed}', 'success': True})
        else:
            current = link_manager.get_warning_count(user_id)
            new_count = max(0, current - count)
            if user_id in link_manager.link_warnings:
                if new_count == 0:
                    del link_manager.link_warnings[user_id]
                    if user_id in link_manager.warning_users:
                        del link_manager.warning_users[user_id]
                else:
                    link_manager.link_warnings[user_id] = new_count
            link_manager._save_data()
            log_service.add_log('info', f'Advertencias de enlaces reducidas a {new_count} para usuario {user_id}', 'dashboard')
            return jsonify({'message': f'Advertencias reducidas a {new_count}', 'success': True})
    except Exception as e:
        log_service.add_log('error', f'Error limpiando advertencias de enlaces: {e}', 'dashboard')
        return jsonify({'error': str(e)}), 500


# ============================================
# ENDPOINTS DE SPOTIFY
# ============================================

@app.route('/api/spotify/queue')
@login_required
def api_get_queue():
    try:
        spotify_data = get_cached_spotify_data(force_refresh=False)
        return jsonify(spotify_data)
    except Exception as e:
        logger.error(f"Error en /api/spotify/queue: {e}")
        log_service.add_log('error', f'Error obteniendo cola de Spotify: {e}', 'spotify')
        return jsonify({
            'current': None,
            'queue': [],
            'is_playing': False,
            'progress_ms': 0,
            'duration_ms': 0
        })


@app.route('/api/spotify/track-art/<track_id>')
@login_required
def api_spotify_track_art(track_id):
    try:
        if not spotify_service or not spotify_service.sp:
            return jsonify({'error': 'Spotify no disponible'}), 500
        track = spotify_service.sp.track(track_id)
        if track and track.get('album', {}).get('images'):
            images = track['album']['images']
            album_art = images[0]['url'] if images else ''
            return jsonify({'album_art': album_art})
        return jsonify({'album_art': ''})
    except Exception as e:
        logger.error(f"Error obteniendo portada del álbum: {e}")
        log_service.add_log('error', f'Error obteniendo portada del álbum: {e}', 'spotify')
        return jsonify({'album_art': ''})


@app.route('/api/spotify/control', methods=['POST'])
@login_required
def api_spotify_control():
    try:
        data = request.json
        action = data.get('action', '')
        if not spotify_service:
            return jsonify({'error': 'Spotify no disponible'}), 500
        success = False
        if action == 'play':
            success = spotify_service.resume_playback()
        elif action == 'pause':
            success = spotify_service.pause_playback()
        elif action == 'skip':
            success = spotify_service.skip_track()
        elif action == 'previous':
            success = spotify_service.previous_track() if hasattr(spotify_service, 'previous_track') else False
        elif action == 'volume':
            volume = int(data.get('volume', 50))
            success = spotify_service.set_volume(volume)
            if success:
                config_service.set_spotify_volume(volume)
        elif action == 'seek':
            position_ms = int(data.get('position_ms', 0))
            success = spotify_service.seek(position_ms)
        else:
            return jsonify({'error': 'Acción no válida'}), 400
        if success:
            global _spotify_cache
            _spotify_cache['timestamp'] = 0
        if not success:
            log_service.add_log('warning', f'Acción de Spotify falló: {action}', 'spotify')
        return jsonify({'message': 'Comando ejecutado', 'success': success})
    except Exception as e:
        logger.error(f"Error en /api/spotify/control: {e}")
        log_service.add_log('error', f'Error controlando Spotify: {e}', 'spotify')
        return jsonify({'error': str(e)}), 500


@app.route('/api/spotify/search')
@login_required
def api_spotify_search():
    try:
        query = request.args.get('q', '')
        if not query or len(query) < 2 or not spotify_service:
            return jsonify([])
        results = spotify_service.sp.search(q=query, type='track', limit=10)
        tracks = results.get('tracks', {}).get('items', [])
        results_list = []
        for track in tracks:
            album_art = ''
            if track.get('album', {}).get('images'):
                album_art = track['album']['images'][0]['url'] if track['album']['images'] else ''
            results_list.append({
                'id': track['id'],
                'name': track['name'],
                'artist': track['artists'][0]['name'] if track['artists'] else 'Desconocido',
                'duration_ms': track['duration_ms'],
                'album_art': album_art
            })
        return jsonify(results_list)
    except Exception as e:
        log_service.add_log('error', f'Error buscando en Spotify: {e}', 'spotify')
        return jsonify([])


@app.route('/api/spotify/add', methods=['POST'])
@login_required
def api_spotify_add():
    try:
        data = request.json
        track_id = data.get('track_id', '')
        if not track_id or not spotify_service:
            return jsonify({'error': 'ID de canción requerido'}), 400
        track_info = {'name': 'Canción', 'artist': 'Artista', 'album_art': ''}
        try:
            track = spotify_service.sp.track(track_id)
            if track:
                album_art = ''
                if track.get('album', {}).get('images'):
                    album_art = track['album']['images'][0]['url'] if track['album']['images'] else ''
                track_info = {
                    'name': track.get('name', 'Canción'),
                    'artist': track['artists'][0]['name'] if track.get('artists') else 'Artista',
                    'album_art': album_art
                }
        except:
            pass
        success = spotify_service.add_to_queue(track_id, track_info)
        if success:
            global _spotify_cache
            _spotify_cache['timestamp'] = 0
        if not success:
            log_service.add_log('warning', f'No se pudo añadir canción a la cola: {track_id}', 'spotify')
        return jsonify({'message': 'Canción añadida a la cola', 'success': success})
    except Exception as e:
        log_service.add_log('error', f'Error añadiendo canción a cola: {e}', 'spotify')
        return jsonify({'error': str(e)}), 500


@app.route('/api/spotify/remove', methods=['POST'])
@login_required
def api_spotify_remove():
    try:
        data = request.json
        position = data.get('position', 0)
        if position < 1:
            return jsonify({'success': False, 'error': 'Posición inválida'}), 400
        removed = spotify_service.remove_from_queue_by_position(position)
        if removed:
            global _spotify_cache
            _spotify_cache['timestamp'] = 0
            return jsonify({
                'success': True,
                'message': f'Canción eliminada: {removed}',
                'was_playing': position == 1 and spotify_service.is_playing()
            })
        else:
            return jsonify({'success': False, 'error': 'No se encontró la canción'}), 404
    except Exception as e:
        logger.error(f"Error eliminando de cola: {e}")
        log_service.add_log('error', f'Error eliminando de cola: {e}', 'spotify')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/spotify/clearqueue', methods=['POST'])
@login_required
def api_spotify_clear_queue():
    try:
        count = spotify_service.clear_queue()
        if count > 0:
            global _spotify_cache
            _spotify_cache['timestamp'] = 0
        return jsonify({'success': True, 'message': f'Se eliminaron {count} canciones de la cola'})
    except Exception as e:
        logger.error(f"Error limpiando cola: {e}")
        log_service.add_log('error', f'Error limpiando cola: {e}', 'spotify')
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# ENDPOINTS DE LOGS
# ============================================

@app.route('/api/logs')
@login_required
def api_get_logs():
    try:
        limit = int(request.args.get('limit', 100))
        level = request.args.get('level', None)
        source = request.args.get('source', None)
        logs = log_service.get_logs(limit=limit, level_filter=level, source_filter=source)
        all_logs = list(log_service.logs)
        sources = sorted(set([l.get('source', 'unknown') for l in all_logs]))
        levels = ['INFO', 'WARNING', 'ERROR', 'CRITICAL']
        return jsonify({
            'logs': logs,
            'sources': sources,
            'levels': levels
        })
    except Exception as e:
        logger.error(f"Error obteniendo logs: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/logs/clear', methods=['POST'])
@login_required
def api_clear_logs():
    try:
        log_service.clear_logs()
        return jsonify({'success': True, 'message': 'Logs limpiados'})
    except Exception as e:
        logger.error(f"Error limpiando logs: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# ENDPOINTS DE ESTADO Y COMANDOS (legacy)
# ============================================

@app.route('/api/status')
@login_required
def api_status():
    try:
        data = api_dashboard_data().json
        return jsonify({
            'connected': data.get('status', {}).get('connected', True),
            'live': data.get('status', {}).get('live', False),
            'viewers': data.get('status', {}).get('viewers', 0),
            'game': data.get('status', {}).get('game', 'No especificado'),
            'title': data.get('status', {}).get('title', 'Sin título'),
            'uptime': data.get('status', {}).get('uptime', 'Offline'),
            'followers': data.get('stats', {}).get('followers', 0),
            'subscribers': data.get('stats', {}).get('subscribers', 0),
            'commands': data.get('stats', {}).get('commands', 0),
            'banned_words': data.get('stats', {}).get('banned_words', 0),
            'spotify_tracks': data.get('stats', {}).get('spotify_tracks', 0),
            'cheers': data.get('stats', {}).get('cheers', 0)
        })
    except Exception as e:
        logger.error(f"Error en /api/status: {e}")
        log_service.add_log('error', f'Error en /api/status: {e}', 'dashboard')
        return jsonify({
            'connected': False,
            'live': False,
            'viewers': 0,
            'game': 'Error',
            'title': 'Error',
            'uptime': 'Error',
            'followers': 0,
            'subscribers': 0,
            'commands': 0,
            'banned_words': 0,
            'spotify_tracks': 0,
            'cheers': 0
        })


@app.route('/api/commands')
@login_required
def api_get_commands():
    try:
        commands = config_service.get_custom_commands()
        command_list = []
        for name, data in commands.items():
            command_list.append({
                'name': name,
                'response': data.get('response', ''),
                'cooldown': data.get('cooldown', 0),
                'created_at': data.get('created_at', '')
            })
        return jsonify(command_list)
    except Exception as e:
        logger.error(f"Error en /api/commands: {e}")
        log_service.add_log('error', f'Error obteniendo comandos: {e}', 'config_service')
        return jsonify([])


@app.route('/api/commands', methods=['POST'])
@login_required
def api_add_command():
    try:
        data = request.json
        name = data.get('name', '').strip().lower()
        response = data.get('response', '').strip()
        cooldown = int(data.get('cooldown', 0))
        if not name or not response:
            return jsonify({'error': 'Nombre y respuesta son requeridos'}), 400
        base_commands = ['hola', 'ping', 'comandos', 'title', 'game', 'slow', 'followers',
                         'emote', 'subscribers', 'vip', 'timeout', 'ban', '8ball', 'dado',
                         'moneda', 'elige', 'lurk', 'uptime', 'viewers', 'shoutout',
                         'announce', 'warn', 'sr', 'current', 'skip', 'pause', 'resume',
                         'queue', 'remove', 'clearqueue', 'volumen', 'clip']
        if name in base_commands:
            return jsonify({'error': f'"{name}" es un comando base'}), 400
        success = config_service.add_custom_command(name, response, cooldown)
        if success:
            log_service.add_log('info', f'Comando !{name} creado por {current_user.username}', 'dashboard')
            return jsonify({'message': f'Comando !{name} creado', 'success': True})
        else:
            return jsonify({'error': 'Error al crear el comando'}), 500
    except Exception as e:
        logger.error(f"Error en /api/commands POST: {e}")
        log_service.add_log('error', f'Error creando comando: {e}', 'dashboard')
        return jsonify({'error': str(e)}), 500


@app.route('/api/commands/<name>', methods=['DELETE'])
@login_required
def api_delete_command(name):
    try:
        success = config_service.remove_custom_command(name)
        if success:
            log_service.add_log('info', f'Comando !{name} eliminado por {current_user.username}', 'dashboard')
            return jsonify({'message': f'Comando !{name} eliminado'})
        else:
            return jsonify({'error': 'Comando no encontrado'}), 404
    except Exception as e:
        logger.error(f"Error en /api/commands DELETE: {e}")
        log_service.add_log('error', f'Error eliminando comando: {e}', 'dashboard')
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/social')
@login_required
def api_get_social_links():
    try:
        return jsonify({
            'discord': config_service.get_social_link('discord'),
            'twitter': config_service.get_social_link('twitter'),
            'instagram': config_service.get_social_link('instagram'),
            'youtube': config_service.get_social_link('youtube'),
            'tiktok': config_service.get_social_link('tiktok')
        })
    except Exception as e:
        log_service.add_log('error', f'Error obteniendo enlaces sociales: {e}', 'config_service')
        return jsonify({})


@app.route('/api/settings/social', methods=['POST'])
@login_required
def api_set_social_links():
    try:
        data = request.json
        platform = data.get('platform', '')
        url = data.get('url', '')
        if not platform:
            return jsonify({'error': 'Plataforma requerida'}), 400
        success = config_service.set_social_link(platform, url)
        if success:
            log_service.add_log('info', f'Enlace social {platform} actualizado por {current_user.username}', 'dashboard')
        return jsonify({'message': f'Enlace de {platform} actualizado', 'success': success})
    except Exception as e:
        log_service.add_log('error', f'Error actualizando enlace social: {e}', 'dashboard')
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/bot-icon', methods=['GET'])
@login_required
def api_get_bot_icon():
    try:
        icon = config_service.get('bot_icon', '🕯️')
        return jsonify({'icon': icon})
    except Exception as e:
        return jsonify({'icon': '🕯️'})


@app.route('/api/settings/bot-icon', methods=['POST'])
@login_required
def api_set_bot_icon():
    try:
        data = request.json
        icon = data.get('icon', '').strip()
        if not icon:
            return jsonify({'success': False, 'error': 'El icono no puede estar vacío'}), 400
        if len(icon) > 10:
            return jsonify({'success': False, 'error': 'El icono es demasiado largo'}), 400
        success = config_service.set('bot_icon', icon)
        if success:
            log_service.add_log('info', f'Icono del bot actualizado a "{icon}"', 'dashboard')
            return jsonify({'success': True, 'message': 'Icono actualizado correctamente'})
        else:
            return jsonify({'success': False, 'error': 'Error al guardar el icono'}), 500
    except Exception as e:
        logger.error(f"Error guardando icono: {e}")
        log_service.add_log('error', f'Error guardando icono: {e}', 'dashboard')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/moderation/banned_words')
@login_required
def api_get_banned_words():
    try:
        return jsonify(config_service.get_banned_words())
    except Exception as e:
        return jsonify([])


@app.route('/api/moderation/banned_words', methods=['POST'])
@login_required
def api_add_banned_word():
    try:
        data = request.json
        word = data.get('word', '').strip().lower()
        if not word:
            return jsonify({'error': 'Palabra requerida'}), 400
        success = config_service.add_banned_word(word)
        if success:
            log_service.add_log('info', f'Palabra prohibida "{word}" añadida', 'dashboard')
            return jsonify({'message': f'Palabra "{word}" añadida', 'success': success})
        else:
            return jsonify({'error': 'Palabra ya existe'}), 400
    except Exception as e:
        log_service.add_log('error', f'Error añadiendo palabra prohibida: {e}', 'dashboard')
        return jsonify({'error': str(e)}), 500


@app.route('/api/moderation/banned_words/<word>', methods=['DELETE'])
@login_required
def api_delete_banned_word(word):
    try:
        success = config_service.remove_banned_word(word)
        if success:
            log_service.add_log('info', f'Palabra prohibida "{word}" eliminada', 'dashboard')
            return jsonify({'message': f'Palabra "{word}" eliminada'})
        else:
            return jsonify({'error': 'Palabra no encontrada'}), 404
    except Exception as e:
        log_service.add_log('error', f'Error eliminando palabra prohibida: {e}', 'dashboard')
        return jsonify({'error': str(e)}), 500


@app.route('/api/moderation/banned_words/reload', methods=['POST'])
@login_required
def api_reload_banned_words():
    try:
        from security.anti_spam import anti_spam
        anti_spam.reload_banned_words()
        log_service.add_log('info', 'Palabras prohibidas recargadas en el bot', 'dashboard')
        return jsonify({
            'success': True,
            'message': f'Palabras prohibidas recargadas: {len(anti_spam.banned_words)}'
        })
    except Exception as e:
        log_service.add_log('error', f'Error recargando palabras prohibidas: {e}', 'dashboard')
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/password', methods=['POST'])
@login_required
def api_change_password():
    try:
        data = request.json
        current = data.get('current', '')
        new = data.get('new', '')
        if not current or not new:
            return jsonify({'error': 'Contraseña actual y nueva requeridas'}), 400
        stored_password = config_service.get_dashboard_password()
        if current != stored_password:
            return jsonify({'error': 'Contraseña actual incorrecta'}), 401
        if len(new) < 6:
            return jsonify({'error': 'La nueva contraseña debe tener al menos 6 caracteres'}), 400
        success = config_service.set_dashboard_password(new)
        if success:
            log_service.add_log('info', 'Contraseña del dashboard actualizada', 'dashboard')
        return jsonify({'message': 'Contraseña actualizada', 'success': success})
    except Exception as e:
        log_service.add_log('error', f'Error cambiando contraseña: {e}', 'dashboard')
        return jsonify({'error': str(e)}), 500


# ============================================
# ENDPOINTS DE CONTROL DE STREAM (título, juego)
# ============================================

@app.route('/api/stream/title', methods=['POST'])
@login_required
def api_update_stream_title():
    try:
        data = request.json
        title = data.get('title', '').strip()
        if not title:
            return jsonify({'success': False, 'error': 'El título no puede estar vacío'}), 400
        if len(title) > 140:
            return jsonify({'success': False, 'error': 'El título no puede exceder 140 caracteres'}), 400
        from services.stream_manager import StreamManager
        stream_manager = StreamManager()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(stream_manager.update_title(title))
        loop.close()
        if result:
            log_service.add_log('info', f'Título del stream actualizado: {title}', 'dashboard')
            return jsonify({'success': True, 'message': 'Título actualizado correctamente'})
        else:
            return jsonify({'success': False, 'error': 'No se pudo actualizar el título'}), 500
    except Exception as e:
        logger.error(f"Error actualizando título: {e}")
        log_service.add_log('error', f'Error actualizando título: {e}', 'dashboard')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stream/game', methods=['POST'])
@login_required
def api_update_stream_game():
    try:
        data = request.json
        game_name = data.get('game', '').strip()
        if not game_name:
            return jsonify({'success': False, 'error': 'El nombre del juego no puede estar vacío'}), 400
        from services.stream_manager import StreamManager
        from exceptions import ResourceNotFoundError
        stream_manager = StreamManager()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            game_id, actual_name = loop.run_until_complete(stream_manager.update_game(game_name))
            loop.close()
            log_service.add_log('info', f'Juego del stream actualizado a "{actual_name}"', 'dashboard')
            return jsonify({
                'success': True,
                'message': 'Juego actualizado correctamente',
                'game_name': actual_name,
                'game_id': game_id
            })
        except ResourceNotFoundError:
            loop.close()
            return jsonify({'success': False, 'error': f'No se encontró el juego: {game_name}'}), 404
        except Exception as e:
            loop.close()
            raise e
    except Exception as e:
        logger.error(f"Error actualizando juego: {e}")
        log_service.add_log('error', f'Error actualizando juego: {e}', 'dashboard')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stream/status')
@login_required
def api_stream_status():
    try:
        from services.stats_service import stats_service
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        stream_info = loop.run_until_complete(stats_service.get_stream_info())
        loop.close()
        if stream_info:
            return jsonify({
                'live': True,
                'title': stream_info.get('title', 'Sin título'),
                'game': stream_info.get('game_name', 'No especificado'),
                'viewers': stream_info.get('viewer_count', 0),
                'started_at': stream_info.get('started_at')
            })
        else:
            api = TwitchAPI(use_broadcaster_token=True)
            channel_result = api.get(
                "channels",
                params={"broadcaster_id": stats_service.broadcaster_id}
            )
            if channel_result and "data" in channel_result and channel_result["data"]:
                channel = channel_result["data"][0]
                return jsonify({
                    'live': False,
                    'title': channel.get('title', 'Sin título'),
                    'game': channel.get('game_name', 'No especificado'),
                    'viewers': 0,
                    'started_at': None
                })
            else:
                return jsonify({
                    'live': False,
                    'title': 'Sin título',
                    'game': 'No especificado',
                    'viewers': 0,
                    'started_at': None
                })
    except Exception as e:
        logger.error(f"Error obteniendo estado del stream: {e}")
        log_service.add_log('error', f'Error obteniendo estado del stream: {e}', 'dashboard')
        return jsonify({'error': str(e)}), 500


# ============================================
# ENDPOINTS DE MODERACIÓN (settings)
# ============================================

@app.route('/api/moderation/settings')
@login_required
def api_get_moderation_settings():
    try:
        return jsonify({
            'slow_mode': config_service.get_slow_mode(),
            'follower_mode': config_service.get_follower_mode(),
            'emote_mode': config_service.get_emote_mode(),
            'subscriber_mode': config_service.get_subscriber_mode(),
            'max_warnings': config_service.get_max_warnings(),
            'banned_words': config_service.get_banned_words()
        })
    except Exception as e:
        log_service.add_log('error', f'Error obteniendo configuración de moderación: {e}', 'dashboard')
        return jsonify({'error': str(e)}), 500


@app.route('/api/moderation/slow', methods=['POST'])
@login_required
def api_set_slow_mode():
    try:
        data = request.json
        enabled = data.get('enabled', False)
        seconds = data.get('seconds', 10)
        if enabled and (seconds < 1 or seconds > 120):
            return jsonify({'error': 'Los segundos deben estar entre 1 y 120'}), 400
        success = config_service.set_slow_mode(enabled, seconds)
        if success and _bot_instance:
            try:
                asyncio.run_coroutine_threadsafe(
                    _bot_instance.apply_chat_settings(),
                    _bot_instance.loop
                )
            except Exception as e:
                logger.error(f"Error aplicando slow mode: {e}")
                log_service.add_log('warning', f'Error aplicando modo lento en el bot: {e}', 'bot')
        if success:
            log_service.add_log('info', f'Modo lento {"activado" if enabled else "desactivado"} ({seconds}s)', 'dashboard')
        return jsonify({'success': success})
    except Exception as e:
        log_service.add_log('error', f'Error configurando modo lento: {e}', 'dashboard')
        return jsonify({'error': str(e)}), 500


@app.route('/api/moderation/followers', methods=['POST'])
@login_required
def api_set_follower_mode():
    try:
        data = request.json
        enabled = data.get('enabled', False)
        minutes = data.get('minutes', 10)
        if enabled and (minutes < 1 or minutes > 129600):
            return jsonify({'error': 'Los minutos deben estar entre 1 y 129600'}), 400
        success = config_service.set_follower_mode(enabled, minutes)
        if success and _bot_instance:
            try:
                asyncio.run_coroutine_threadsafe(
                    _bot_instance.apply_chat_settings(),
                    _bot_instance.loop
                )
            except Exception as e:
                logger.error(f"Error aplicando follower mode: {e}")
                log_service.add_log('warning', f'Error aplicando modo seguidores en el bot: {e}', 'bot')
        if success:
            log_service.add_log('info', f'Modo seguidores {"activado" if enabled else "desactivado"} ({minutes}m)', 'dashboard')
        return jsonify({'success': success})
    except Exception as e:
        log_service.add_log('error', f'Error configurando modo seguidores: {e}', 'dashboard')
        return jsonify({'error': str(e)}), 500


@app.route('/api/moderation/emote', methods=['POST'])
@login_required
def api_set_emote_mode():
    try:
        data = request.json
        enabled = data.get('enabled', False)
        success = config_service.set_emote_mode(enabled)
        if success and _bot_instance:
            try:
                asyncio.run_coroutine_threadsafe(
                    _bot_instance.apply_chat_settings(),
                    _bot_instance.loop
                )
            except Exception as e:
                logger.error(f"Error aplicando emote mode: {e}")
                log_service.add_log('warning', f'Error aplicando modo emotes en el bot: {e}', 'bot')
        if success:
            log_service.add_log('info', f'Modo emotes {"activado" if enabled else "desactivado"}', 'dashboard')
        return jsonify({'success': success})
    except Exception as e:
        log_service.add_log('error', f'Error configurando modo emotes: {e}', 'dashboard')
        return jsonify({'error': str(e)}), 500


@app.route('/api/moderation/subscriber', methods=['POST'])
@login_required
def api_set_subscriber_mode():
    try:
        data = request.json
        enabled = data.get('enabled', False)
        success = config_service.set_subscriber_mode(enabled)
        if success and _bot_instance:
            try:
                asyncio.run_coroutine_threadsafe(
                    _bot_instance.apply_chat_settings(),
                    _bot_instance.loop
                )
            except Exception as e:
                logger.error(f"Error aplicando subscriber mode: {e}")
                log_service.add_log('warning', f'Error aplicando modo suscriptores en el bot: {e}', 'bot')
        if success:
            log_service.add_log('info', f'Modo suscriptores {"activado" if enabled else "desactivado"}', 'dashboard')
        return jsonify({'success': success})
    except Exception as e:
        log_service.add_log('error', f'Error configurando modo suscriptores: {e}', 'dashboard')
        return jsonify({'error': str(e)}), 500


@app.route('/api/moderation/max_warnings', methods=['POST'])
@login_required
def api_set_max_warnings():
    try:
        data = request.json
        value = data.get('value', 3)
        if value < 1 or value > 10:
            return jsonify({'error': 'El valor debe estar entre 1 y 10'}), 400
        success = config_service.set_max_warnings(value)
        if success:
            log_service.add_log('info', f'Máximo de advertencias actualizado a {value}', 'dashboard')
        return jsonify({'success': success})
    except Exception as e:
        log_service.add_log('error', f'Error actualizando máximo de advertencias: {e}', 'dashboard')
        return jsonify({'error': str(e)}), 500


# ============================================
# ENDPOINTS DE ENLACES PERMITIDOS
# ============================================

@app.route('/api/links/allowed')
@login_required
def api_get_allowed_links():
    try:
        links = config_service.get_allowed_links()
        return jsonify(list(links.keys()))
    except Exception as e:
        log_service.add_log('error', f'Error obteniendo enlaces permitidos: {e}', 'dashboard')
        return jsonify({'error': str(e)}), 500


@app.route('/api/links/allowed', methods=['POST'])
@login_required
def api_add_allowed_link():
    try:
        data = request.json
        domain = data.get('domain', '').strip().lower()
        if not domain:
            return jsonify({'error': 'Dominio requerido'}), 400
        domain = domain.replace('https://', '').replace('http://', '').replace('www.', '')
        success = config_service.add_allowed_link(domain)
        if success:
            log_service.add_log('info', f'Dominio permitido añadido: {domain}', 'dashboard')
            return jsonify({'message': f'Dominio {domain} añadido', 'success': True})
        else:
            return jsonify({'error': 'Error al añadir dominio'}), 500
    except Exception as e:
        log_service.add_log('error', f'Error añadiendo dominio permitido: {e}', 'dashboard')
        return jsonify({'error': str(e)}), 500


@app.route('/api/links/allowed/<domain>', methods=['DELETE'])
@login_required
def api_remove_allowed_link(domain):
    try:
        success = config_service.remove_allowed_link(domain)
        if success:
            log_service.add_log('info', f'Dominio permitido eliminado: {domain}', 'dashboard')
            return jsonify({'message': f'Dominio {domain} eliminado', 'success': True})
        else:
            return jsonify({'error': 'Dominio no encontrado'}), 404
    except Exception as e:
        log_service.add_log('error', f'Error eliminando dominio permitido: {e}', 'dashboard')
        return jsonify({'error': str(e)}), 500


# ============================================
# ENDPOINTS DE TWITCH MODERATION (ban, timeout)
# ============================================

@app.route('/api/twitch/ban/<user_id>', methods=['DELETE'])
@login_required
def api_twitch_remove_ban(user_id):
    try:
        success = link_manager.remove_twitch_ban(user_id)
        if success:
            log_service.add_log('info', f'Ban removido para usuario {user_id}', 'dashboard')
            return jsonify({'message': f'Usuario {user_id} desbaneado', 'success': True})
        else:
            return jsonify({'error': 'No se pudo desbanear al usuario'}), 400
    except Exception as e:
        log_service.add_log('error', f'Error removiendo ban: {e}', 'dashboard')
        return jsonify({'error': str(e)}), 500


@app.route('/api/twitch/timeout/<user_id>', methods=['DELETE'])
@login_required
def api_twitch_remove_timeout(user_id):
    try:
        success = link_manager.remove_twitch_timeout(user_id)
        if success:
            log_service.add_log('info', f'Timeout removido para usuario {user_id}', 'dashboard')
            return jsonify({'message': f'Timeout removido para usuario {user_id}', 'success': True})
        else:
            return jsonify({'error': 'No se pudo quitar el timeout'}), 400
    except Exception as e:
        log_service.add_log('error', f'Error removiendo timeout: {e}', 'dashboard')
        return jsonify({'error': str(e)}), 500


@app.route('/api/twitch/check/<user_id>')
@login_required
def api_twitch_check_user(user_id):
    try:
        status = link_manager.check_user_status(user_id)
        return jsonify(status)
    except Exception as e:
        log_service.add_log('error', f'Error verificando usuario {user_id}: {e}', 'dashboard')
        return jsonify({'error': str(e), 'banned': False}), 500


# ============================================
# WEBHOOK DE TWITCH (integrado)
# ============================================

@app.route('/webhook/twitch', methods=['POST'])
def twitch_webhook():
    """Endpoint para webhooks de Twitch (EventSub)"""
    try:
        signature = request.headers.get('Twitch-Eventsub-Message-Signature', '')
        message_id = request.headers.get('Twitch-Eventsub-Message-Id', '')
        timestamp = request.headers.get('Twitch-Eventsub-Message-Timestamp', '')
        message_type = request.headers.get('Twitch-Eventsub-Message-Type', '')
        body = request.get_data(as_text=True)
        message = message_id + timestamp + body

        secret = os.getenv("TWITCH_WEBHOOK_SECRET", "")
        if secret:
            expected = hmac.new(
                secret.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            if signature.startswith('sha256='):
                signature = signature[7:]
            if not hmac.compare_digest(expected, signature):
                log_service.add_log('warning', 'Firma inválida en webhook', 'webhook')
                return jsonify({"error": "Invalid signature"}), 401

        data = request.json

        if message_type == 'webhook_callback_verification':
            challenge = data.get('challenge')
            return jsonify({"challenge": challenge}), 200

        if message_type == 'notification':
            event_type = data.get('subscription', {}).get('type', 'unknown')
            event_data = data.get('event', {})
            log_service.add_log('info', f'Evento recibido: {event_type}', 'webhook')

            from services.eventsub_service import eventsub_service
            if _bot_instance:
                eventsub_service.set_bot(_bot_instance)
                eventsub_service._process_event(event_type, event_data)

        return jsonify({"status": "ok"}), 200
    except Exception as e:
        log_service.add_log('error', f'Error en webhook: {e}', 'webhook')
        return jsonify({"error": str(e)}), 500


@app.route('/webhook/twitch', methods=['GET'])
def twitch_webhook_get():
    return jsonify({"status": "ready"}), 200


# ============================================
# HEALTH CHECK
# ============================================

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }), 200


# ============================================
# RUN DASHBOARD
# ============================================

def run_dashboard(port=None):
    if port is None:
        port = int(os.getenv("PORT", 5002))   # Usa PORT de Render o 5002 por defecto
    wait_for_tokens(timeout=60)
    logger.info(f"🚀 Iniciando servidor dashboard en el puerto {port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)