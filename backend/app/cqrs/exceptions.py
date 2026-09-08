from __future__ import annotations


class CqrsError(Exception):
    """Base de los errores del bus."""


class HandlerNotFound(CqrsError):
    def __init__(self, message_type: type) -> None:
        super().__init__(f"No hay handler registrado para {message_type.__name__}")
        self.message_type = message_type


class DuplicateHandler(CqrsError):
    def __init__(self, message_type: type) -> None:
        super().__init__(f"Ya hay un handler registrado para {message_type.__name__}")
        self.message_type = message_type
