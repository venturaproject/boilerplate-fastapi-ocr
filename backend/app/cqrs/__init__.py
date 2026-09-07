"""CQRS: command bus + query bus (async).

    # app/domain/<x>/commands.py
    @dataclass(frozen=True)
    class CrearCosa(Command):
        nombre: str

    # app/domain/<x>/handlers.py
    @command_handler(CrearCosa)
    async def handle_crear_cosa(session, cmd: CrearCosa) -> uuid.UUID:
        ...

    # app/routers/<x>.py
    cosa_id = await command_bus.dispatch(db, CrearCosa(nombre="x"))
"""

from app.cqrs.bus import command_bus, query_bus
from app.cqrs.exceptions import DuplicateHandler, HandlerNotFound
from app.cqrs.messages import Command, Query
from app.cqrs.registry import command_handler, query_handler

__all__ = [
    "Command",
    "DuplicateHandler",
    "HandlerNotFound",
    "Query",
    "command_bus",
    "command_handler",
    "query_bus",
    "query_handler",
]
