from __future__ import annotations

import shutil

import numpy as np
import pytest

pytest.importorskip("pytesseract")

from app.services.ocr.engine import TesseractOcrEngine
from app.services.ocr.loader import PageImage

_HAS_BINARY = shutil.which("tesseract") is not None

pytestmark = pytest.mark.skipif(not _HAS_BINARY, reason="tesseract binary not installed")


def _text_page() -> PageImage:
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (400, 80), "white")
    ImageDraw.Draw(img).text((10, 25), "HELLO WORLD 123", fill="black")
    return PageImage(index=1, width=400, height=80, array=np.asarray(img))


def test_tesseract_recognises_text():
    engine = TesseractOcrEngine()
    pages = engine.recognize_pages([_text_page()], "en")
    assert pages[0].page == 1
    joined = pages[0].text.upper()
    assert "HELLO" in joined and "WORLD" in joined
    assert all(0.0 <= ln.confidence <= 1.0 for ln in pages[0].lines)
