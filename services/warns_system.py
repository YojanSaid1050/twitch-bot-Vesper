from services.moderation_actions import ModerationActions
from services.config_service import config_service
from utils.logger import get_logger
from services.log_service import log_service

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
            
            log_service.add_log('info', f'Advertencia a {user_name} por {reason} (total: {warning_count})', 'warns_system')

            action_taken = False

            if warning_count >= self.MAX_WARNS:
                await self.mod_actions.timeout(user_name, 600, "Máximo de advertencias alcanzado")
                action_taken = True
                config_service.clear_warnings(user_id)
                log_service.add_log('warning', f'Timeout a {user_name} por máximo de advertencias ({warning_count})', 'warns_system')

            return warning_count, action_taken
        except Exception as e:
            logger.error(f"Error en add_warning: {e}")
            log_service.add_log('error', f'Error en add_warning para {user_name}: {e}', 'warns_system')
            raise


warns_system = WarnsSystem()