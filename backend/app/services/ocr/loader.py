"""Turn an uploaded image or PDF into a list of RGB page images for the OCR engine."""

from __future__ import annotations

import io
import logging
import math
import os
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageSequence

from app.config import settings
from app.exceptions import PayloadTooLargeException, UnsupportedMediaException

logger = logging.getLogger("app.services.ocr")

# Cap Pillow's own decompression-bomb guard to our configured budget.
Image.MAX_IMAGE_PIXELS = int(settings.ocr_max_image_megapixels * 1_000_000)


def _max_pixels() -> int:
    return int(settings.ocr_max_image_megapixels * 1_000_000)


# content-type -> canonical extension
IMAGE_CONTENT_TYPES: dict[str, str] = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/webp": "webp",
    "image/bmp": "bmp",
    "image/tiff": "tiff",
    "image/x-tiff": "tiff",
}
PDF_CONTENT_TYPES: set[str] = {"application/pdf", "application/x-pdf"}
SUPPORTED_CONTENT_TYPES: set[str] = set(IMAGE_CONTENT_TYPES) | PDF_CONTENT_TYPES

_EXT_TO_CONTENT_TYPE: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".pdf": "application/pdf",
}


@dataclass(frozen=True)
class PageImage:
    index: int  # 1-based page number
    width: int
    height: int
    array: np.ndarray  # H x W x 3, uint8, RGB


def normalize_content_type(content_type: str | None, filename: str | None) -> str:
    """Best-effort content type: trust the header, fall back to the file extension."""
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct in SUPPORTED_CONTENT_TYPES:
        return ct
    if filename:
        ext = os.path.splitext(filename)[1].lower()
        if ext in _EXT_TO_CONTENT_TYPE:
            return _EXT_TO_CONTENT_TYPE[ext]
    return ct


def _pil_to_page(index: int, img: Image.Image) -> PageImage:
    rgb = img.convert("RGB")
    return PageImage(index=index, width=rgb.width, height=rgb.height, array=np.asarray(rgb))


def load_pages(
    data: bytes,
    content_type: str | None,
    *,
    filename: str | None = None,
    max_pages: int | None = None,
) -> list[PageImage]:
    ct = normalize_content_type(content_type, filename)

    if ct in PDF_CONTENT_TYPES:
        return _load_pdf(data, max_pages=max_pages)
    if ct in IMAGE_CONTENT_TYPES:
        return _load_image(data, max_pages=max_pages)

    raise UnsupportedMediaException(
        f"Tipo de archivo no soportado: {ct or 'desconocido'}. Admitidos: PNG, JPEG, WEBP, BMP, TIFF y PDF."
    )


def _load_image(data: bytes, *, max_pages: int | None) -> list[PageImage]:
    try:
        img = Image.open(io.BytesIO(data))
    except Exception as exc:
        raise UnsupportedMediaException("No se pudo decodificar la imagen") from exc

    # Header carries the size without decoding pixels — reject bombs before load().
    if img.width * img.height > _max_pixels():
        raise PayloadTooLargeException(
            f"La imagen es de {img.width}x{img.height}px; el máximo es {settings.ocr_max_image_megapixels:g} MP."
        )

    n_frames = getattr(img, "n_frames", 1)
    if max_pages is not None and n_frames > max_pages:
        raise PayloadTooLargeException(f"La imagen tiene {n_frames} fotogramas; el máximo permitido es {max_pages}.")

    try:
        return [_pil_to_page(i, frame) for i, frame in enumerate(ImageSequence.Iterator(img), start=1)]
    except Image.DecompressionBombError as exc:
        raise PayloadTooLargeException("La imagen supera el límite de píxeles permitido.") from exc
    except Exception as exc:
        raise UnsupportedMediaException("No se pudo decodificar la imagen") from exc


def _load_pdf(data: bytes, *, max_pages: int | None) -> list[PageImage]:
    try:
        import pymupdf as fitz
    except ImportError as exc:  # pragma: no cover
        raise UnsupportedMediaException("Soporte de PDF no disponible (falta PyMuPDF)") from exc

    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise UnsupportedMediaException("No se pudo leer el PDF") from exc

    zoom = settings.ocr_pdf_dpi / 72.0
    budget = _max_pixels()
    pages: list[PageImage] = []
    with doc:
        page_count = doc.page_count
        if max_pages is not None and page_count > max_pages:
            raise PayloadTooLargeException(f"El PDF tiene {page_count} páginas; el máximo permitido es {max_pages}.")
        for i in range(page_count):
            page = doc.load_page(i)
            rect = page.rect
            # Clamp this page's zoom so the rendered bitmap never exceeds the pixel budget.
            page_zoom = zoom
            target_px = (rect.width * zoom) * (rect.height * zoom)
            if target_px > budget and rect.width > 0 and rect.height > 0:
                page_zoom = math.sqrt(budget / (rect.width * rect.height))
                logger.warning(
                    "PDF página %s (%.0fx%.0f pt) reescalada: zoom %.2f -> %.2f",
                    i + 1,
                    rect.width,
                    rect.height,
                    zoom,
                    page_zoom,
                )
            pix = page.get_pixmap(matrix=fitz.Matrix(page_zoom, page_zoom), alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            pages.append(_pil_to_page(i + 1, img))
    return pages
