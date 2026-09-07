"""OCR engine abstraction.

`PaddleOcrEngine` wraps PaddleOCR and is the ONLY place that knows its API.
`FakeOcrEngine` is a deterministic stub for tests / CI (no heavy deps).
Select with `OCR_ENGINE` (settings.ocr_engine).
"""

from __future__ import annotations

import functools
import logging
import threading
from typing import Any, Protocol

import numpy as np

from app.config import settings
from app.schemas.ocr import OcrLine, OcrPage
from app.services.ocr.loader import PageImage

logger = logging.getLogger("app.services.ocr")


class OcrEngine(Protocol):
    name: str

    def recognize_pages(self, pages: list[PageImage], lang: str) -> list[OcrPage]: ...


def _page_text(lines: list[OcrLine]) -> str:
    return "\n".join(line.text for line in lines)


# ── PaddleOCR ────────────────────────────────────────────────────────────────


class PaddleOcrEngine:
    name = "paddleocr"

    def __init__(self) -> None:
        self._models: dict[str, object] = {}
        self._lock = threading.Lock()

    def _get_model(self, lang: str) -> object:
        with self._lock:
            model = self._models.get(lang)
            if model is None:
                from paddleocr import PaddleOCR

                logger.info("Cargando modelo PaddleOCR (lang=%s)…", lang)
                model = PaddleOCR(
                    use_angle_cls=True,
                    lang=lang,
                    use_gpu=settings.ocr_use_gpu,
                    show_log=False,
                )
                self._models[lang] = model
            return model

    def recognize_pages(self, pages: list[PageImage], lang: str) -> list[OcrPage]:
        model = self._get_model(lang)
        results: list[OcrPage] = []
        for page in pages:
            # PaddleOCR models are not thread-safe: serialise inference.
            with self._lock:
                raw = model.ocr(page.array, cls=True)  # type: ignore[attr-defined]
            lines = _parse_paddle_page(raw)
            results.append(
                OcrPage(
                    page=page.index,
                    width=page.width,
                    height=page.height,
                    lines=lines,
                    text=_page_text(lines),
                )
            )
        return results


def _parse_paddle_page(raw: Any) -> list[OcrLine]:
    """Normalise PaddleOCR 2.x output: [[ [box, (text, score)], ... ]] (or [None])."""
    if not raw:
        return []
    page = raw[0] if isinstance(raw, list) else raw
    if not page:
        return []
    lines: list[OcrLine] = []
    for entry in page:
        try:
            box, rec = entry[0], entry[1]
            text = str(rec[0])
            score = float(rec[1])
        except (TypeError, IndexError, ValueError):  # pragma: no cover - defensive
            continue
        lines.append(
            OcrLine(
                text=text,
                confidence=max(0.0, min(1.0, score)),
                box=[[float(x), float(y)] for x, y in box],
            )
        )
    return lines


# ── Fake (tests / CI) ────────────────────────────────────────────────────────


class FakeOcrEngine:
    name = "fake"

    def recognize_pages(self, pages: list[PageImage], lang: str) -> list[OcrPage]:
        results: list[OcrPage] = []
        for page in pages:
            lines = [
                OcrLine(
                    text=f"[fake-ocr {lang}] page {page.index} line {n}",
                    confidence=0.99,
                    box=[
                        [0.0, 20.0 * (n - 1)],
                        [float(page.width), 20.0 * (n - 1)],
                        [float(page.width), 20.0 * n],
                        [0.0, 20.0 * n],
                    ],
                )
                for n in (1, 2)
            ]
            results.append(
                OcrPage(
                    page=page.index,
                    width=page.width,
                    height=page.height,
                    lines=lines,
                    text=_page_text(lines),
                )
            )
        return results


@functools.lru_cache(maxsize=1)
def get_engine() -> OcrEngine:
    if settings.ocr_engine == "fake":
        return FakeOcrEngine()
    return PaddleOcrEngine()


def warmup(langs: list[str]) -> None:
    """Load models ahead of the first request (blocking; run in a thread from async code)."""
    engine = get_engine()
    if engine.name == "fake":
        return
    blank = PageImage(index=1, width=32, height=32, array=np.full((32, 32, 3), 255, dtype=np.uint8))
    for lang in dict.fromkeys(langs):
        try:
            engine.recognize_pages([blank], lang)
            logger.info("PaddleOCR warmup listo (lang=%s)", lang)
        except Exception:
            logger.exception("PaddleOCR warmup falló (lang=%s)", lang)
