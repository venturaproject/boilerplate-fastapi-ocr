from __future__ import annotations

import argparse
import asyncio
import logging

from app.config import settings
from app.ocr.processor import drain_once

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("app.ocr.worker")


async def run_loop(interval: float, batch_size: int) -> None:
    logger.info("ocr-worker: bucle cada %ss (Ctrl-C para salir)", interval)
    while True:
        try:
            n = await drain_once(batch_size)
            if n:
                logger.info("ocr-worker: %s job(s) procesado(s)", n)
        except Exception:
            logger.exception("ocr-worker: error en el lote")
        await asyncio.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Procesa la cola de jobs OCR.")
    parser.add_argument("--once", action="store_true", help="Procesa un lote y sale.")
    parser.add_argument("--interval", type=float, default=settings.ocr_worker_interval_seconds)
    parser.add_argument("--batch-size", type=int, default=5)
    args = parser.parse_args()

    if args.once:
        n = asyncio.run(drain_once(args.batch_size))
        logger.info("ocr-worker: %s job(s) procesado(s).", n)
    else:
        try:
            asyncio.run(run_loop(args.interval, args.batch_size))
        except KeyboardInterrupt:
            logger.info("ocr-worker: detenido.")


if __name__ == "__main__":
    main()
