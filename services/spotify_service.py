"""
Servicio para integración con Spotify
"""

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from typing import Optional, Dict, List
from collections import deque
import threading
import time
import requests.exceptions
import os
from datetime import datetime, timedelta

from config import settings
from utils.logger import get_logger
from services.log_service import log_service

logger = get_logger(__name__)


class SpotifyService:
    """Servicio para gestionar Spotify (song requests)"""
    
    def __init__(self):
        self.client_id = settings.SPOTIFY_CLIENT_ID
        self.client_secret = settings.SPOTIFY_CLIENT_SECRET
        self.redirect_uri = "http://127.0.0.1:8888/callback"
        self.scope = "user-modify-playback-state user-read-playback-state user-read-currently-playing user-read-playback-state"
        
        self.sp = None
        self.queue_tracks: List[str] = []
        self.queue_info: Dict[str, dict] = {}
        self.queue_history: deque = deque(maxlen=10)
        self.current_track_id = None
        self._monitoring = False
        self._last_error_time = 0
        self._error_cooldown = 30
        
        # Estado del token para integración con token_manager
        self.token_valid = False
        self.token_expires_at = None
        
        if self.client_id and self.client_secret:
            self._authenticate()
            self._start_monitoring()
        else:
            logger.warning("⚠️ Spotify no configurado. Los comandos !sr no funcionarán.")
            log_service.add_log('warning', 'Spotify no configurado (faltan credenciales)', 'spotify_service')
    
    def _authenticate(self):
        """Autenticar con Spotify usando refresh token desde settings"""
        try:
            refresh_token = settings.SPOTIFY_REFRESH_TOKEN
            
            if not refresh_token:
                logger.warning("⚠️ No hay SPOTIFY_REFRESH_TOKEN configurado en variables de entorno")
                logger.warning("💡 Agrega SPOTIFY_REFRESH_TOKEN a las variables de entorno de Render")
                log_service.add_log('warning', 'No hay SPOTIFY_REFRESH_TOKEN configurado', 'spotify_service')
                self.sp = None
                self.token_valid = False
                return
            
            # Crear auth manager sin caché
            auth_manager = SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri,
                scope=self.scope,
                cache_path=None,
                open_browser=False,
                show_dialog=False
            )
            
            logger.info("🔄 Generando nuevo access token de Spotify desde refresh token...")
            
            try:
                token_info = auth_manager.refresh_access_token(refresh_token)
                
                if token_info and token_info.get('access_token'):
                    self.sp = spotipy.Spotify(auth_manager=auth_manager)
                    auth_manager.token_info = token_info
                    
                    # Guardar información del token
                    self.token_valid = True
                    expires_in = token_info.get('expires_in', 3600)
                    self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                    
                    logger.info("✅ Token de Spotify generado correctamente")
                    logger.info(f"⏰ Expira en: {expires_in // 60} minutos")
                    log_service.add_log('info', f'Token de Spotify generado desde refresh token (expira en {expires_in//60}m)', 'spotify_service')
                    
                    # Verificar que funciona
                    try:
                        user = self.sp.current_user()
                        logger.info(f"👤 Conectado como: {user.get('display_name', 'Usuario Spotify')}")
                    except Exception as e:
                        logger.warning(f"⚠️ Verificación falló: {e}")
                else:
                    logger.error("❌ No se pudo generar token de Spotify con el refresh token")
                    log_service.add_log('error', 'No se pudo generar token de Spotify con refresh token', 'spotify_service')
                    self.sp = None
                    self.token_valid = False
                    
            except Exception as e:
                error_msg = str(e)
                if "invalid refresh token" in error_msg.lower():
                    logger.error("❌ Refresh token inválido o expirado. Genera uno nuevo localmente.")
                    logger.error("💡 Ejecuta en local el script para generar SPOTIFY_REFRESH_TOKEN")
                    log_service.add_log('error', 'Refresh token de Spotify inválido', 'spotify_service')
                else:
                    logger.error(f"❌ Error generando token de Spotify: {e}")
                    log_service.add_log('error', f'Error generando token de Spotify: {e}', 'spotify_service')
                self.sp = None
                self.token_valid = False
                
        except Exception as e:
            logger.error(f"❌ Error autenticando con Spotify: {e}")
            log_service.add_log('error', f'Error autenticando con Spotify: {e}', 'spotify_service')
            self.sp = None
            self.token_valid = False
    
    def get_token_status(self) -> Dict:
        """Obtener estado del token de Spotify para integración con token_manager"""
        if not self.sp:
            return {'valid': False, 'expires_at': None, 'expires_in': None}
        
        if self.token_expires_at:
            now = datetime.now()
            if self.token_expires_at > now:
                expires_in = (self.token_expires_at - now).total_seconds()
                return {
                    'valid': True,
                    'expires_at': self.token_expires_at,
                    'expires_in': expires_in
                }
            else:
                # Token expirado, intentar refrescar
                logger.info("🔄 Token de Spotify expirado, refrescando...")
                self._authenticate()
                if self.token_expires_at:
                    expires_in = (self.token_expires_at - datetime.now()).total_seconds()
                    return {
                        'valid': self.token_valid,
                        'expires_at': self.token_expires_at,
                        'expires_in': expires_in if expires_in > 0 else 0
                    }
        
        return {'valid': self.token_valid, 'expires_at': None, 'expires_in': None}
    
    def refresh_token(self) -> bool:
        """Refrescar token de Spotify manualmente (usado por token_manager)"""
        logger.info("🔄 Refrescando token de Spotify...")
        self._authenticate()
        return self.token_valid
    
    def _start_monitoring(self):
        """Iniciar monitoreo de reproducción en segundo plano"""
        if self._monitoring:
            return
        
        self._monitoring = True
        
        def monitor():
            consecutive_errors = 0
            while self._monitoring:
                try:
                    self._check_current_track()
                    consecutive_errors = 0
                    time.sleep(2)
                except (requests.exceptions.ConnectionError, 
                        requests.exceptions.Timeout,
                        ConnectionError) as e:
                    consecutive_errors += 1
                    now = time.time()
                    if now - self._last_error_time > self._error_cooldown:
                        logger.warning(f"⚠️ Spotify no responde (posiblemente cerrado): {e}")
                        log_service.add_log('warning', f'Spotify no responde: {e}', 'spotify_service')
                        self._last_error_time = now
                    if consecutive_errors > 5:
                        time.sleep(10)
                    else:
                        time.sleep(5)
                except Exception as e:
                    error_msg = str(e)
                    now = time.time()
                    if "EOF" in error_msg or "Server listening" in error_msg:
                        if now - self._last_error_time > 300:
                            logger.debug(f"Spotify en modo espera: {error_msg[:50]}")
                            self._last_error_time = now
                        time.sleep(10)
                    else:
                        logger.error(f"Error en monitoreo de Spotify: {e}")
                        log_service.add_log('error', f'Error en monitoreo de Spotify: {e}', 'spotify_service')
                        time.sleep(5)
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        logger.info("🔍 Monitoreo de Spotify iniciado")
        log_service.add_log('info', 'Monitoreo de Spotify iniciado', 'spotify_service')
    
    def _check_current_track(self):
        """Verificar si la canción actual cambió"""
        if not self.sp:
            return
        
        try:
            current = self.sp.current_user_playing_track()
            
            if not current or not current.get('is_playing'):
                return
            
            item = current.get('item', {})
            track_id = item.get('id')
            
            if track_id and track_id != self.current_track_id:
                if self.current_track_id and self.current_track_id in self.queue_tracks:
                    self.queue_tracks.remove(self.current_track_id)
                    if self.current_track_id in self.queue_info:
                        del self.queue_info[self.current_track_id]
                    self.queue_history.append(self.current_track_id)
                    logger.info(f"Canción reproducida: {self.current_track_id}")
                
                self.current_track_id = track_id
                
                if track_id in self.queue_tracks:
                    self.queue_tracks.remove(track_id)
                    if track_id in self.queue_info:
                        del self.queue_info[track_id]
                    
        except (requests.exceptions.ConnectionError, 
                requests.exceptions.Timeout,
                ConnectionError) as e:
            raise
        except Exception as e:
            logger.error(f"Error en monitoreo: {e}")
            log_service.add_log('error', f'Error en monitoreo de Spotify: {e}', 'spotify_service')
    
    def _safe_api_call(self, func, *args, **kwargs):
        """Ejecuta una llamada a la API de Spotify con manejo de errores de conexión"""
        if not self.sp:
            return None
        
        try:
            return func(*args, **kwargs)
        except (requests.exceptions.ConnectionError, 
                requests.exceptions.Timeout,
                ConnectionError) as e:
            now = time.time()
            if now - self._last_error_time > self._error_cooldown:
                logger.warning(f"⚠️ Spotify no disponible: {e}")
                log_service.add_log('warning', f'Spotify no disponible: {e}', 'spotify_service')
                self._last_error_time = now
            return None
        except Exception as e:
            logger.error(f"Error en API de Spotify: {e}")
            log_service.add_log('error', f'Error en API de Spotify: {e}', 'spotify_service')
            return None
    
    def search_track(self, query: str) -> Optional[Dict]:
        """Buscar una canción en Spotify con portada"""
        if not self.sp:
            return None
        
        try:
            results = self.sp.search(q=query, type='track', limit=1)
            tracks = results.get('tracks', {}).get('items', [])
            
            if not tracks:
                return None
            
            track = tracks[0]
            album_art = ''
            if track.get('album', {}).get('images'):
                album_art = track['album']['images'][0]['url'] if track['album']['images'] else ''
            
            return {
                'id': track['id'],
                'name': track['name'],
                'artist': track['artists'][0]['name'],
                'url': track['external_urls']['spotify'],
                'duration_ms': track['duration_ms'],
                'album_art': album_art
            }
        except (requests.exceptions.ConnectionError, 
                requests.exceptions.Timeout,
                ConnectionError) as e:
            logger.warning(f"⚠️ Spotify no disponible para búsqueda: {e}")
            log_service.add_log('warning', f'Spotify no disponible para búsqueda', 'spotify_service')
            return None
        except Exception as e:
            logger.error(f"Error buscando canción: {e}")
            log_service.add_log('error', f'Error buscando canción "{query}": {e}', 'spotify_service')
            return None
    
    def is_track_in_queue(self, track_id: str) -> bool:
        """Verificar si una canción ya está en la cola"""
        return track_id in self.queue_tracks
    
    def get_queue_list(self) -> List[Dict]:
        """Obtener lista de canciones en cola con su info y portada"""
        queue_list = []
        for i, track_id in enumerate(self.queue_tracks, 1):
            info = self.queue_info.get(track_id, {})
            queue_list.append({
                'position': i,
                'name': info.get('name', 'Desconocida'),
                'artist': info.get('artist', 'Desconocido'),
                'id': track_id,
                'album_art': info.get('album_art', '')
            })
        return queue_list
    
    def get_queue_count(self) -> int:
        """Obtener número de canciones en cola"""
        return len(self.queue_tracks)
    
    def set_volume(self, volume: int) -> bool:
        """Ajustar volumen (0-100)"""
        if not self.sp:
            return False
        
        try:
            volume = max(0, min(100, volume))
            self.sp.volume(volume)
            logger.info(f"Volumen ajustado a {volume}%")
            log_service.add_log('info', f'Volumen ajustado a {volume}%', 'spotify_service')
            return True
        except (requests.exceptions.ConnectionError, 
                requests.exceptions.Timeout,
                ConnectionError) as e:
            logger.warning(f"⚠️ Spotify no disponible para ajustar volumen: {e}")
            log_service.add_log('warning', f'Spotify no disponible para ajustar volumen', 'spotify_service')
            return False
        except Exception as e:
            logger.error(f"Error ajustando volumen: {e}")
            log_service.add_log('error', f'Error ajustando volumen: {e}', 'spotify_service')
            return False
    
    def get_volume(self) -> Optional[int]:
        """Obtener volumen actual"""
        if not self.sp:
            return None
        
        try:
            playback = self.sp.current_playback()
            if playback and playback.get('device'):
                return playback['device'].get('volume_percent', 50)
            return None
        except (requests.exceptions.ConnectionError, 
                requests.exceptions.Timeout,
                ConnectionError) as e:
            logger.warning(f"⚠️ Spotify no disponible para obtener volumen: {e}")
            log_service.add_log('warning', f'Spotify no disponible para obtener volumen', 'spotify_service')
            return None
        except Exception as e:
            logger.error(f"Error obteniendo volumen: {e}")
            log_service.add_log('error', f'Error obteniendo volumen: {e}', 'spotify_service')
            return None
    
    def get_track_position_in_history(self, track_id: str) -> int:
        """Obtener posición de una canción en el historial"""
        try:
            history_list = list(self.queue_history)
            if track_id in history_list:
                position = len(history_list) - history_list.index(track_id)
                return position
            return -1
        except Exception:
            return -1
    
    def is_track_in_history(self, track_id: str) -> tuple:
        """Verificar si una canción está en el historial"""
        position = self.get_track_position_in_history(track_id)
        return (position != -1, position)
    
    def add_to_queue(self, track_id: str, track_info: dict) -> bool:
        """Añadir canción a la cola de Spotify con portada"""
        if not self.sp:
            return False
        
        try:
            self.sp.add_to_queue(track_id)
            
            album_art = track_info.get('album_art', '')
            if not album_art:
                try:
                    track = self.sp.track(track_id)
                    if track and track.get('album', {}).get('images'):
                        album_art = track['album']['images'][0]['url'] if track['album']['images'] else ''
                except:
                    pass
            
            self.queue_tracks.append(track_id)
            self.queue_info[track_id] = {
                'name': track_info.get('name', 'Canción'),
                'artist': track_info.get('artist', 'Artista'),
                'album_art': album_art
            }
            logger.info(f"Canción añadida a la cola: {track_info.get('name')}")
            log_service.add_log('info', f'Canción añadida a la cola: {track_info.get("name")}', 'spotify_service')
            return True
        except (requests.exceptions.ConnectionError, 
                requests.exceptions.Timeout,
                ConnectionError) as e:
            logger.warning(f"⚠️ Spotify no disponible para añadir a cola: {e}")
            log_service.add_log('warning', f'Spotify no disponible para añadir a cola', 'spotify_service')
            return False
        except Exception as e:
            logger.error(f"Error añadiendo a la cola: {e}")
            log_service.add_log('error', f'Error añadiendo a la cola: {e}', 'spotify_service')
            return False
    
    def get_current_track(self) -> Optional[Dict]:
        """Obtener canción actual (incluso si está pausada)"""
        if not self.sp:
            return None
        
        try:
            current = self.sp.current_user_playing_track()
            if not current or not current.get('item'):
                return None
            item = current.get('item', {})
            return {
                'name': item.get('name'),
                'artist': item.get('artists', [{}])[0].get('name'),
                'url': item.get('external_urls', {}).get('spotify'),
                'id': item.get('id'),
                'duration_ms': item.get('duration_ms'),
                'is_playing': current.get('is_playing', False)
            }
        except (requests.exceptions.ConnectionError, 
                requests.exceptions.Timeout,
                ConnectionError) as e:
            now = time.time()
            if now - self._last_error_time > self._error_cooldown:
                logger.warning(f"⚠️ Spotify no disponible para obtener canción actual: {e}")
                log_service.add_log('warning', f'Spotify no disponible (posiblemente cerrado)', 'spotify_service')
                self._last_error_time = now
            return None
        except Exception as e:
            logger.error(f"Error obteniendo canción actual: {e}")
            log_service.add_log('error', f'Error obteniendo canción actual: {e}', 'spotify_service')
            return None
    
    def skip_track(self) -> bool:
        """Saltar a la siguiente canción"""
        if not self.sp:
            return False
        
        try:
            if self.current_track_id and self.current_track_id in self.queue_tracks:
                self.queue_tracks.remove(self.current_track_id)
                if self.current_track_id in self.queue_info:
                    del self.queue_info[self.current_track_id]
                self.queue_history.append(self.current_track_id)
            
            self.sp.next_track()
            self.current_track_id = None
            logger.info("⏭️ Saltando a siguiente canción")
            log_service.add_log('info', 'Saltando a siguiente canción', 'spotify_service')
            return True
        except (requests.exceptions.ConnectionError, 
                requests.exceptions.Timeout,
                ConnectionError) as e:
            logger.warning(f"⚠️ Spotify no disponible para saltar: {e}")
            log_service.add_log('warning', f'Spotify no disponible para saltar', 'spotify_service')
            return False
        except Exception as e:
            logger.error(f"Error saltando: {e}")
            log_service.add_log('error', f'Error saltando canción: {e}', 'spotify_service')
            return False
    
    def previous_track(self) -> bool:
        """Ir a la canción anterior"""
        if not self.sp:
            return False
        
        try:
            self.sp.previous_track()
            self.current_track_id = None
            logger.info("⏮️ Volviendo a canción anterior")
            log_service.add_log('info', 'Volviendo a canción anterior', 'spotify_service')
            return True
        except (requests.exceptions.ConnectionError, 
                requests.exceptions.Timeout,
                ConnectionError) as e:
            logger.warning(f"⚠️ Spotify no disponible para ir a anterior: {e}")
            log_service.add_log('warning', f'Spotify no disponible para ir a anterior', 'spotify_service')
            return False
        except Exception as e:
            logger.error(f"Error yendo a canción anterior: {e}")
            log_service.add_log('error', f'Error yendo a canción anterior: {e}', 'spotify_service')
            return False
    
    def pause_playback(self) -> bool:
        """Pausar reproducción"""
        if not self.sp:
            return False
        
        try:
            self.sp.pause_playback()
            logger.info("⏸️ Reproducción pausada")
            log_service.add_log('info', 'Reproducción pausada', 'spotify_service')
            return True
        except (requests.exceptions.ConnectionError, 
                requests.exceptions.Timeout,
                ConnectionError) as e:
            logger.warning(f"⚠️ Spotify no disponible para pausar: {e}")
            log_service.add_log('warning', f'Spotify no disponible para pausar', 'spotify_service')
            return False
        except Exception as e:
            logger.error(f"Error pausando: {e}")
            log_service.add_log('error', f'Error pausando reproducción: {e}', 'spotify_service')
            return False
    
    def resume_playback(self) -> bool:
        """Reanudar reproducción"""
        if not self.sp:
            return False
        
        try:
            self.sp.start_playback()
            logger.info("▶️ Reproducción reanudada")
            log_service.add_log('info', 'Reproducción reanudada', 'spotify_service')
            return True
        except (requests.exceptions.ConnectionError, 
                requests.exceptions.Timeout,
                ConnectionError) as e:
            logger.warning(f"⚠️ Spotify no disponible para reanudar: {e}")
            log_service.add_log('warning', f'Spotify no disponible para reanudar', 'spotify_service')
            return False
        except Exception as e:
            logger.error(f"Error reanudando: {e}")
            log_service.add_log('error', f'Error reanudando reproducción: {e}', 'spotify_service')
            return False
    
    def is_playing(self) -> bool:
        """Verificar si hay música sonando (activo)"""
        if not self.sp:
            return False
        
        try:
            current = self.sp.current_user_playing_track()
            return current is not None and current.get('is_playing', False)
        except (requests.exceptions.ConnectionError, 
                requests.exceptions.Timeout,
                ConnectionError) as e:
            return False
        except Exception:
            return False
    
    def stop_monitoring(self):
        """Detener monitoreo"""
        self._monitoring = False
        logger.info("🛑 Monitoreo de Spotify detenido")
        log_service.add_log('info', 'Monitoreo de Spotify detenido', 'spotify_service')
    
    def get_playback_state(self) -> Dict:
        """Obtener estado completo de reproducción con progreso y duración"""
        if not self.sp:
            return {'is_playing': False, 'device': None, 'track': None, 'volume': None}
        
        try:
            playback = self.sp.current_playback()
            if not playback:
                return {'is_playing': False, 'device': None, 'track': None, 'volume': None}
            
            track = None
            if playback.get('item'):
                item = playback['item']
                track = {
                    'name': item.get('name'),
                    'artist': item.get('artists', [{}])[0].get('name'),
                    'id': item.get('id'),
                    'url': item.get('external_urls', {}).get('spotify'),
                    'duration_ms': item.get('duration_ms'),
                    'progress_ms': playback.get('progress_ms', 0)
                }
            
            return {
                'is_playing': playback.get('is_playing', False),
                'device': playback.get('device', {}),
                'track': track,
                'volume': playback.get('device', {}).get('volume_percent', 50) if playback.get('device') else None
            }
        except (requests.exceptions.ConnectionError, 
                requests.exceptions.Timeout,
                ConnectionError) as e:
            return {'is_playing': False, 'device': None, 'track': None, 'volume': None}
        except Exception as e:
            logger.error(f"Error obteniendo estado de reproducción: {e}")
            log_service.add_log('error', f'Error obteniendo estado de reproducción: {e}', 'spotify_service')
            return {'is_playing': False, 'device': None, 'track': None, 'volume': None}
    
    def seek(self, position_ms: int) -> bool:
        """Mover a una posición específica de la canción"""
        if not self.sp:
            return False
        try:
            self.sp.seek_track(position_ms)
            logger.info(f"⏩ Seek a {position_ms}ms")
            log_service.add_log('info', f'Seek a {position_ms}ms', 'spotify_service')
            return True
        except (requests.exceptions.ConnectionError, 
                requests.exceptions.Timeout,
                ConnectionError) as e:
            logger.warning(f"⚠️ Spotify no disponible para seek: {e}")
            log_service.add_log('warning', f'Spotify no disponible para seek', 'spotify_service')
            return False
        except Exception as e:
            logger.error(f"Error en seek: {e}")
            log_service.add_log('error', f'Error en seek: {e}', 'spotify_service')
            return False


# Instancia global
spotify_service = SpotifyService()