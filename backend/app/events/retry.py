from __future__ import annotations

from datetime import timedelta

BACKOFF_BASE_SECONDS = 10
BACKOFF_CAP_SECONDS = 3600


def next_backoff(attempts: int) -> timedelta:
    """Espera antes del siguiente intento tras ``attempts`` fallos."""
    seconds = min(BACKOFF_BASE_SECONDS * (2 ** max(attempts - 1, 0)), BACKOFF_CAP_SECONDS)
    return timedelta(seconds=seconds)
