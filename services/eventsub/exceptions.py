# services/eventsub/exceptions.py
"""
Excepciones específicas del sistema EventSub.
"""


class EventSubError(Exception):
    """Excepción base para el sistema EventSub."""
    pass


class InvalidScopeError(EventSubError):
    """Error cuando un scope requerido no está presente."""
    pass


class InvalidConditionError(EventSubError):
    """Error cuando la condición de un evento es inválida."""
    pass


class WebhookUnavailableError(EventSubError):
    """Error cuando el webhook no responde o no está disponible."""
    pass


class SubscriptionError(EventSubError):
    """Error al crear o eliminar una suscripción."""
    pass


class TokenMismatchError(EventSubError):
    """Error cuando el token no coincide con el usuario esperado."""
    pass


class DuplicateEventError(EventSubError):
    """Error cuando se detecta un evento duplicado."""
    pass


class HandlerNotFoundError(EventSubError):
    """Error cuando no se encuentra un handler para un tipo de evento."""
    pass


class TransportNotSupportedError(EventSubError):
    """Error cuando el transporte solicitado no es soportado por el evento."""
    pass


class CleanupError(EventSubError):
    """Error durante la limpieza de suscripciones."""
    pass