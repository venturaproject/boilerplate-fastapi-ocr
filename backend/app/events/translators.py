from __future__ import annotations

from collections.abc import Callable

from app.cqrs.messages import Command

Translator = Callable[[dict], Command]

_translators: dict[tuple[str, str], Translator] = {}


class TranslatorNotFound(Exception):
    def __init__(self, source: str, event_name: str) -> None:
        super().__init__(f"No hay traductor para ({source!r}, {event_name!r})")


def inbox_translator(source: str, event_name: str) -> Callable[[Translator], Translator]:
    """Registra una función ``payload -> Command`` para un mensaje entrante.

    @inbox_translator("erp", "invoice.received")
    def _(payload: dict) -> Command:
        return IngestInvoice(**payload)
    """

    def decorator(fn: Translator) -> Translator:
        _translators[(source, event_name)] = fn
        return fn

    return decorator


def translate(source: str, event_name: str, payload: dict) -> Command:
    try:
        fn = _translators[(source, event_name)]
    except KeyError:
        raise TranslatorNotFound(source, event_name) from None
    return fn(payload)


def reset_translators() -> None:
    """Sólo para tests."""
    _translators.clear()
