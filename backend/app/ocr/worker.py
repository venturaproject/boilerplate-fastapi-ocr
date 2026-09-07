from __future__ import annotations

import argparse
import asyncio
import logging
import time

import anyio.to_thread

from app.config import settings
from app.ocr.processor import drain_once, purge_once
from app.services.ocr.engine import warmup


def _configure_logging() -> None:
    # force=True: PaddleOCR reconfigures the root logger during model load.
    logging.basicConfig(
        level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s", force=True
    )


_configure_logging()
logger = logging.getLogger("app.ocr.worker")


async def run_loop(interval: float, batch_size: int) -> None:
    if settings.ocr_warmup_on_startup:
        logger.info("ocr-worker: precargando modelo(s) %s…", settings.ocr_warmup_langs_list)
        await anyio.to_thread.run_sync(warmup, settings.ocr_warmup_langs_list)
        _configure_logging()

    logger.info("ocr-worker: bucle cada %ss (Ctrl-C para salir)", interval)
    last_purge = 0.0
    while True:
        try:
            n = await drain_once(batch_size)
            if n:
                logger.info("ocr-worker: %s job(s) procesado(s)", n)
        except Exception:
            logger.exception("ocr-worker: error en el lote")

        if time.monotonic() - last_purge >= settings.ocr_purge_interval_seconds:
            last_purge = time.monotonic()
            try:
                await purge_once()
            except Exception:
                logger.exception("ocr-worker: error en la purga")

        await asyncio.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Procesa la cola de jobs OCR.")
    parser.add_argument("--once", action="store_true", help="Procesa un lote y sale.")
    parser.add_argument("--purge", action="store_true", help="Purga jobs vencidos y sale.")
    parser.add_argument("--interval", type=float, default=settings.ocr_worker_interval_seconds)
    parser.add_argument("--batch-size", type=int, default=5)
    args = parser.parse_args()

    if args.purge:
        n = asyncio.run(purge_once())
        logger.info("ocr-worker: %s job(s) purgado(s).", n)
    elif args.once:
        n = asyncio.run(drain_once(args.batch_size))
        logger.info("ocr-worker: %s job(s) procesado(s).", n)
    else:
        try:
            asyncio.run(run_loop(args.interval, args.batch_size))
        except KeyboardInterrupt:
            logger.info("ocr-worker: detenido.")


if __name__ == "__main__":
    main()
