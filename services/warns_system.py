from services.moderation_actions import ModerationActions
from services.config_service import config_service
from services.log_service import log_service
from utils.logger import get_logger

logger = get_logger(__name__)


class WarnsSystem:
    MAX_WARNS = 3

    def __init__(self):
        self.mod_actions = ModerationActions()

    async def add_warning(self, user_id: str, user_name: str, reason: str, warned_by: str):
        try:
            config_service.add_warning(user_id, user_name, reason, warned_by)
            warnings = config_service.get_warnings(user_id)
            warning_count = len(warnings)
            
            # Log de advertencia (moderación)
            log_service.add_log('warning', f'Advertencia aplicada a {user_name} (total: {warning_count}) por {warned_by}. Razón: "{reason}"', 'moderation')

            action_taken = False

            if warning_count >= self.MAX_WARNS:
                await self.mod_actions.timeout(user_name, 600, "Máximo de advertencias alcanzado")
                action_taken = True
                config_service.clear_warnings(user_id)
                # Log de timeout automático (moderación)
                log_service.add_log('warning', f'Timeout automático a {user_name} por máximo de advertencias ({warning_count}/{self.MAX_WARNS})', 'moderation')

            return warning_count, action_taken
        except Exception as e:
            logger.error(f"Error en add_warning: {e}")
            log_service.add_log('error', f'Error al añadir advertencia para {user_name}: {e}', 'bot')
            raise


warns_system = WarnsSystem()