"""
Servicio para integración con Spotify
"""

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from typing import Optional, Dict, Set, List
from collections import deque
import threading
import time

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class SpotifyService:
    """Servicio para gestionar Spotify (song requests)"""
    
    def __init__(self):
        self.client_id = settings.SPOTIFY_CLIENT_ID
        self.client_secret = settings.SPOTIFY_CLIENT_SECRET
        self.redirect_uri = "http://127.0.0.1:8888/callback"
        self.scope = "user-modify-playback-state user-read-playback-state user-read-currently-playing user-read-playback-state"
        
        self.sp = None
        self.queue_tracks: List[str] = []  # Lista ordenada de IDs de canciones en cola
        self.queue_info: Dict[str, dict] = {}  # Info de cada canción en cola
        self.queue_history: deque = deque(maxlen=10)
        self.current_track_id = None
        self._monitoring = False
        
        if self.client_id and self.client_secret:
            self._authenticate()
            self._start_monitoring()
        else:
            logger.warning("⚠️ Spotify no configurado. Los comandos !sr no funcionarán.")
    
    def _authenticate(self):
        """Autenticar con Spotify"""
        try:
            self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri,
                scope=self.scope,
                cache_path=".spotify_cache"
            ))
            logger.info("✅ Autenticado con Spotify")
        except Exception as e:
            logger.error(f"❌ Error autenticando con Spotify: {e}")
            self.sp = None
    
    def _start_monitoring(self):
        """Iniciar monitoreo de reproducción en segundo plano"""
        if self._monitoring:
            return
        
        self._monitoring = True
        
        def monitor():
            while self._monitoring:
                try:
                    self._check_current_track()
                    time.sleep(2)
                except Exception as e:
                    logger.error(f"Error en monitoreo: {e}")
                    time.sleep(5)
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        logger.info("🔍 Monitoreo de Spotify iniciado")
    
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
                    
        except Exception as e:
            logger.error(f"Error en monitoreo: {e}")
    
    def search_track(self, query: str) -> Optional[Dict]:
        """Buscar una canción en Spotify"""
        if not self.sp:
            return None
        
        try:
            results = self.sp.search(q=query, type='track', limit=1)
            tracks = results.get('tracks', {}).get('items', [])
            
            if not tracks:
                return None
            
            track = tracks[0]
            return {
                'id': track['id'],
                'name': track['name'],
                'artist': track['artists'][0]['name'],
                'url': track['external_urls']['spotify'],
                'duration_ms': track['duration_ms']
            }
        except Exception as e:
            logger.error(f"Error buscando canción: {e}")
            return None
    
    def is_track_in_queue(self, track_id: str) -> bool:
        """Verificar si una canción ya está en la cola"""
        return track_id in self.queue_tracks
    
    def get_queue_list(self) -> List[Dict]:
        """Obtener lista de canciones en cola con su info"""
        queue_list = []
        for i, track_id in enumerate(self.queue_tracks, 1):
            info = self.queue_info.get(track_id, {})
            queue_list.append({
                'position': i,
                'name': info.get('name', 'Desconocida'),
                'artist': info.get('artist', 'Desconocido'),
                'id': track_id
            })
        return queue_list
    
    def get_queue_count(self) -> int:
        """Obtener número de canciones en cola"""
        return len(self.queue_tracks)
    
    def remove_from_queue_by_position(self, position: int) -> Optional[str]:
        """Eliminar canción de la cola por posición"""
        if 1 <= position <= len(self.queue_tracks):
            track_id = self.queue_tracks[position - 1]
            self.queue_tracks.pop(position - 1)
            if track_id in self.queue_info:
                info = self.queue_info.pop(track_id)
                return f"{info.get('name', 'Canción')} - {info.get('artist', 'Desconocido')}"
        return None
    
    def clear_queue(self) -> int:
        """Limpiar toda la cola"""
        count = len(self.queue_tracks)
        self.queue_tracks.clear()
        self.queue_info.clear()
        return count
    
    def set_volume(self, volume: int) -> bool:
        """Ajustar volumen (0-100)"""
        if not self.sp:
            return False
        
        try:
            volume = max(0, min(100, volume))  # Limitar entre 0 y 100
            self.sp.volume(volume)
            logger.info(f"Volumen ajustado a {volume}%")
            return True
        except Exception as e:
            logger.error(f"Error ajustando volumen: {e}")
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
        except Exception as e:
            logger.error(f"Error obteniendo volumen: {e}")
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
        """
        Añadir canción a la cola de Spotify
        """
        if not self.sp:
            return False
        
        try:
            self.sp.add_to_queue(track_id)
            self.queue_tracks.append(track_id)
            self.queue_info[track_id] = {
                'name': track_info['name'],
                'artist': track_info['artist']
            }
            logger.info(f"Canción añadida a la cola: {track_info['name']}")
            return True
        except Exception as e:
            logger.error(f"Error añadiendo a la cola: {e}")
            return False
    
    def get_current_track(self) -> Optional[Dict]:
        """Obtener canción actual"""
        if not self.sp:
            return None
        
        try:
            current = self.sp.current_user_playing_track()
            
            if not current or not current.get('is_playing'):
                return None
            
            item = current.get('item', {})
            return {
                'name': item.get('name'),
                'artist': item.get('artists', [{}])[0].get('name'),
                'url': item.get('external_urls', {}).get('spotify'),
                'id': item.get('id')
            }
        except Exception as e:
            logger.error(f"Error obteniendo canción actual: {e}")
            return None
    
    def skip_track(self) -> bool:
        """Saltar canción"""
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
            return True
        except Exception as e:
            logger.error(f"Error saltando: {e}")
            return False
    
    def pause_playback(self) -> bool:
        """Pausar"""
        if not self.sp:
            return False
        
        try:
            self.sp.pause_playback()
            return True
        except Exception as e:
            logger.error(f"Error pausando: {e}")
            return False
    
    def resume_playback(self) -> bool:
        """Reanudar"""
        if not self.sp:
            return False
        
        try:
            self.sp.start_playback()
            return True
        except Exception as e:
            logger.error(f"Error reanudando: {e}")
            return False
    
    def is_playing(self) -> bool:
        """Verificar si hay música sonando"""
        if not self.sp:
            return False
        
        try:
            current = self.sp.current_user_playing_track()
            return current is not None and current.get('is_playing', False)
        except Exception as e:
            return False
    
    def stop_monitoring(self):
        """Detener monitoreo"""
        self._monitoring = False


# Instancia global
spotify_service = SpotifyService()