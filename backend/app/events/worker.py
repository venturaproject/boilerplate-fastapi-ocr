from __future__ import annotations

import argparse
import asyncio
import logging

import app.domain  # noqa: F401  -- registra handlers / subscribers / translators
from app.config import settings
from app.events.inbox import process_inbox_batch
from app.events.outbox import process_outbox_batch

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("app.events.worker")


async def drain_once(batch_size: int) -> int:
    processed = 0
    processed += await process_inbox_batch(batch_size=batch_size)
    processed += await process_outbox_batch(batch_size=batch_size)
    return processed


async def run_loop(interval: float, batch_size: int) -> None:
    logger.info("worker: bucle cada %ss (Ctrl-C para salir)", interval)
    while True:
        try:
            await drain_once(batch_size)
        except Exception:
            logger.exception("worker: error en el lote")
        await asyncio.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Drena outbox + inbox.")
    parser.add_argument("--once", action="store_true", help="Procesa un lote y sale.")
    parser.add_argument("--interval", type=float, default=settings.events_worker_interval_seconds)
    parser.add_argument("--batch-size", type=int, default=50)
    args = parser.parse_args()

    if args.once:
        n = asyncio.run(drain_once(args.batch_size))
        logger.info("worker: %s mensaje(s) procesado(s).", n)
    else:
        try:
            asyncio.run(run_loop(args.interval, args.batch_size))
        except KeyboardInterrupt:
            logger.info("worker: detenido.")


if __name__ == "__main__":
    main()
