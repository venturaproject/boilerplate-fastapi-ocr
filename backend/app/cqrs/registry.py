from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from app.cqrs.exceptions import DuplicateHandler, HandlerNotFound
from app.cqrs.messages import Command, Query

TMessage = TypeVar("TMessage", bound=Command | Query)
Handler = Callable[..., Awaitable[Any]]

_command_handlers: dict[type, Handler] = {}
_query_handlers: dict[type, Handler] = {}


def command_handler(command_type: type[Command]) -> Callable[[Handler], Handler]:
    """Registra la corutina decorada como handler (1:1) del comando indicado."""

    def decorator(fn: Handler) -> Handler:
        if command_type in _command_handlers:
            raise DuplicateHandler(command_type)
        _command_handlers[command_type] = fn
        return fn

    return decorator


def query_handler(query_type: type[Query]) -> Callable[[Handler], Handler]:
    """Registra la corutina decorada como handler (1:1) de la query indicada."""

    def decorator(fn: Handler) -> Handler:
        if query_type in _query_handlers:
            raise DuplicateHandler(query_type)
        _query_handlers[query_type] = fn
        return fn

    return decorator


def get_command_handler(command_type: type) -> Handler:
    try:
        return _command_handlers[command_type]
    except KeyError:
        raise HandlerNotFound(command_type) from None


def get_query_handler(query_type: type) -> Handler:
    try:
        return _query_handlers[query_type]
    except KeyError:
        raise HandlerNotFound(query_type) from None


def reset_registry() -> None:
    """Sólo para tests."""
    _command_handlers.clear()
    _query_handlers.clear()
