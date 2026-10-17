"""Wyjątki warstwy serwisowej, mapowane na HTTP w app.main i na błędy narzędzi w MCP."""


class ServiceError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class InvalidInput(ServiceError):
    """Niepoprawne dane wejściowe (HTTP 422)."""


class NotFound(ServiceError):
    """Brak obiektu albo obiekt usunięty (HTTP 404)."""


class Conflict(ServiceError):
    """Konflikt z istniejącym stanem (HTTP 409)."""
