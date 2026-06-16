"""
Excepciones personalizadas para el bot
"""


class TwitchBotError(Exception):
    """Excepción base del bot"""
    pass


class TwitchAPIError(TwitchBotError):
    """Error al comunicarse con la API de Twitch"""
    def __init__(self, message: str, status_code: int = None, response_text: str = None):
        self.status_code = status_code
        self.response_text = response_text
        self._message = message
        super().__init__(message)
    
    @property
    def message(self):
        """Propiedad message para compatibilidad"""
        return self._message
    
    def __str__(self):
        if self.status_code:
            return f"Error {self.status_code}: {self._message}"
        return self._message


class AuthenticationError(TwitchAPIError):
    """Error de autenticación (token inválido)"""
    pass


class RateLimitError(TwitchAPIError):
    """Rate limit excedido"""
    pass


class ResourceNotFoundError(TwitchAPIError):
    """Recurso no encontrado"""
    pass


class ValidationError(TwitchBotError):
    """Error de validación de entrada"""
    pass


class StreamOfflineError(TwitchBotError):
    """El stream no está en vivo"""
    pass


class PermissionDeniedError(TwitchBotError):
    """El usuario no tiene permisos suficientes"""
    pass