from services.spotify_service import spotify_service
from services.stats_service import stats_service
from services.stream_manager import StreamManager
from services.moderation_actions import ModerationActions
from services.config_service import config_service
from services.token_manager import token_manager
from services.log_service import log_service  # <-- NUEVO


class ServiceManager:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not ServiceManager._initialized:
            self._initialize()
            ServiceManager._initialized = True

    def _initialize(self):
        try:
            self.spotify = spotify_service
            self.stats = stats_service
            self.stream_manager = StreamManager()
            self.moderation = ModerationActions()
            self.config = config_service
            self.token_manager = token_manager
            print("✅ ServiceManager inicializado")
            log_service.add_log('info', 'ServiceManager inicializado', 'service_manager')
        except Exception as e:
            log_service.add_log('critical', f'Error inicializando ServiceManager: {e}', 'service_manager')
            raise


service_manager = ServiceManager()