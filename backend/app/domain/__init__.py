"""Registro de la capa de dominio: importar este paquete engancha todos los
command/query handlers, subscribers y traductores del inbox en los buses.

Lo importan `app.main` (API) y `app.events.worker` (worker) al arrancar.
"""

from app.domain import dispositivo, telefono, trabajador

__all__ = ["dispositivo", "telefono", "trabajador"]
