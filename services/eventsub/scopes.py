# services/eventsub/scopes.py
"""
Validación de scopes para EventSub.
"""

from typing import List
from services.eventsub.definitions import ScopeOwner, TokenInfo
from services.eventsub.tokens import TokenValidator
from services.eventsub.exceptions import InvalidScopeError
from utils.logger import get_logger

logger = get_logger(__name__)


class ScopeValidator:
    """Valida que los scopes requeridos estén presentes en el token del usuario correspondiente."""

    def validate(
        self,
        required_scopes: List[str],
        scope_owner: ScopeOwner,
        event_type: str
    ) -> bool:
        if not required_scopes:
            return True

        if scope_owner == ScopeOwner.APP:
            # No se pueden validar scopes en App Token
            logger.warning(f"Evento {event_type} tiene scopes pero scope_owner=APP. No se validarán scopes.")
            return True

        token_type = self._map_scope_owner_to_token_type(scope_owner)
        token_info = TokenValidator.get_token_info(token_type)

        if not token_info:
            raise InvalidScopeError(f"No hay token {token_type} disponible para {event_type}")

        if not token_info.scopes:
            raise InvalidScopeError(f"Token {token_type} no tiene scopes para {event_type}")

        missing = [s for s in required_scopes if s not in token_info.scopes]
        if missing:
            raise InvalidScopeError(
                f"Scopes faltantes en {token_type} para {event_type}: {', '.join(missing)}"
            )

        logger.debug(f"Scopes OK para {event_type} en {token_type}")
        return True

    def _map_scope_owner_to_token_type(self, scope_owner: ScopeOwner) -> str:
        mapping = {
            ScopeOwner.BROADCASTER: "broadcaster",
            ScopeOwner.MODERATOR: "moderator",
            ScopeOwner.USER: "user",
            ScopeOwner.APP: "app",
        }
        return mapping.get(scope_owner, "broadcaster")


scope_validator = ScopeValidator()