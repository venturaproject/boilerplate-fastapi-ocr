from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    """Marcador para intenciones de escritura.

    Los comandos pasan por el ``command_bus``. La transacción la aporta el
    contexto (``get_db`` en request, ``session.begin()`` en el worker); los
    eventos de dominio emitidos durante el handler se vuelcan al outbox por el
    hook ``before_flush`` de SQLAlchemy.
    """


@dataclass(frozen=True)
class Query:
    """Marcador para lecturas. Pasa por el ``query_bus``: ejecución directa."""
