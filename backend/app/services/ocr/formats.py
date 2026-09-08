"""Render an `OcrResult` into text / hOCR / ALTO / searchable-PDF.

`json` (the `OcrResult` model) is the default and handled by the routers; this
module covers the `?format=` alternatives.
"""

from __future__ import annotations

import html
import io
from xml.sax.saxutils import escape, quoteattr

from app.schemas.ocr import OcrPage, OcrResult

FORMATS = ("json", "text", "hocr", "alto", "pdf")
MEDIA_TYPES = {
    "text": "text/plain; charset=utf-8",
    "hocr": "text/html; charset=utf-8",
    "alto": "application/xml; charset=utf-8",
    "pdf": "application/pdf",
}


def _bbox(box: list[list[float]]) -> tuple[int, int, int, int]:
    xs = [p[0] for p in box]
    ys = [p[1] for p in box]
    return int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))


def to_text(result: OcrResult) -> str:
    return result.text


def to_hocr(result: OcrResult) -> str:
    out = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"'
        ' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">',
        "<html xmlns='http://www.w3.org/1999/xhtml'><head>",
        "<meta http-equiv='Content-Type' content='text/html;charset=utf-8'/>",
        f"<meta name='ocr-system' content='fastapi-ocr ({escape(result.engine)})'/>",
        "<meta name='ocr-capabilities' content='ocr_page ocr_line'/>",
        "</head><body>",
    ]
    line_id = 0
    for p in result.pages:
        out.append(
            f"<div class='ocr_page' id='page_{p.page}' title='bbox 0 0 {p.width} {p.height}; ppageno {p.page - 1}'>"
        )
        for ln in p.lines:
            line_id += 1
            x0, y0, x1, y1 = _bbox(ln.box)
            out.append(
                f"<span class='ocr_line' id='line_{line_id}' "
                f"title='bbox {x0} {y0} {x1} {y1}; x_wconf {int(ln.confidence * 100)}'>"
                f"{html.escape(ln.text)}</span>"
            )
        out.append("</div>")
    out.append("</body></html>")
    return "\n".join(out)


def to_alto(result: OcrResult) -> str:
    out = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        "<alto xmlns='http://www.loc.gov/standards/alto/ns-v3#'>",
        "<Description><MeasurementUnit>pixel</MeasurementUnit>"
        f"<OCRProcessing ID='OCR_1'><ocrProcessingStep><processingSoftware>"
        f"<softwareName>fastapi-ocr</softwareName><softwareCreator>{escape(result.engine)}</softwareCreator>"
        "</processingSoftware></ocrProcessingStep></OCRProcessing></Description>",
        "<Layout>",
    ]
    sid = 0
    for p in result.pages:
        out.append(
            f"<Page ID='page_{p.page}' PHYSICAL_IMG_NR='{p.page}' "
            f"WIDTH='{p.width}' HEIGHT='{p.height}'>"
            f"<PrintSpace HPOS='0' VPOS='0' WIDTH='{p.width}' HEIGHT='{p.height}'><TextBlock ID='block_{p.page}'>"
        )
        for i, ln in enumerate(p.lines):
            x0, y0, x1, y1 = _bbox(ln.box)
            out.append(
                f"<TextLine ID='line_{p.page}_{i}' HPOS='{x0}' VPOS='{y0}' WIDTH='{x1 - x0}' HEIGHT='{y1 - y0}'>"
            )
            for word in ln.text.split():
                sid += 1
                out.append(
                    f"<String ID='s_{sid}' HPOS='{x0}' VPOS='{y0}' WIDTH='{x1 - x0}' "
                    f"HEIGHT='{y1 - y0}' WC='{round(ln.confidence, 2)}' CONTENT={quoteattr(word)}/>"
                )
            out.append("</TextLine>")
        out.append("</TextBlock></PrintSpace></Page>")
    out.append("</Layout></alto>")
    return "\n".join(out)


def to_pdf(result: OcrResult, page_images: list) -> bytes:
    """Searchable PDF: each source page image with an invisible text layer on top."""
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    by_index: dict[int, OcrPage] = {p.page: p for p in result.pages}

    for img in page_images:
        w, h = float(img.width), float(img.height)
        c.setPageSize((w, h))
        try:
            from PIL import Image

            pil = Image.fromarray(img.array)
            c.drawImage(ImageReader(pil), 0, 0, width=w, height=h)
        except Exception:  # pragma: no cover - image render best-effort
            pass

        page = by_index.get(img.index)
        if page:
            text_obj = c.beginText()
            text_obj.setTextRenderMode(3)  # invisible
            for ln in page.lines:
                x0, _y0, _x1, y1 = _bbox(ln.box)
                font_size = max(4.0, (y1 - _y0) * 0.9)
                text_obj.setFont("Helvetica", font_size)
                text_obj.setTextOrigin(x0, h - y1)  # PDF origin is bottom-left
                text_obj.textLine(ln.text)
            c.drawText(text_obj)
        c.showPage()

    c.save()
    return buf.getvalue()


def render(result: OcrResult, fmt: str, page_images: list | None = None) -> tuple[bytes, str]:
    """Return (body, media_type) for a non-json format."""
    if fmt == "text":
        return to_text(result).encode("utf-8"), MEDIA_TYPES["text"]
    if fmt == "hocr":
        return to_hocr(result).encode("utf-8"), MEDIA_TYPES["hocr"]
    if fmt == "alto":
        return to_alto(result).encode("utf-8"), MEDIA_TYPES["alto"]
    if fmt == "pdf":
        return to_pdf(result, page_images or []), MEDIA_TYPES["pdf"]
    raise ValueError(f"formato no soportado: {fmt}")
