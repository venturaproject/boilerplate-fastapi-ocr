from __future__ import annotations

from dataclasses import dataclass

from app.events import DomainEvent


@dataclass(frozen=True)
class TrabajadorSynchronizedFromERP(DomainEvent):
    synergy_res_id: int | None = None
    created: bool = False

    @classmethod
    def name(cls) -> str:
        return "trabajador.synchronized_from_erp"
