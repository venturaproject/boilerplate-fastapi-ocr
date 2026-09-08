"""Field extraction over the OCR text, keyed by the detected document type.

Pluggable like the classifier: `OCR_EXTRACTOR=none|rules|llm`. Runs after
`classify()`; returns a small set of structured fields per type (each with the
raw matched substring). Deliberately conservative — misses beat wrong values.
"""

from __future__ import annotations

import re

from app.config import settings
from app.schemas.ocr import DocExtraction, DocExtractionField, OcrResult

# amounts like 1.234,56 / 1,234.56 / 1234.56
_AMOUNT = r"\d{1,3}(?:[.\s]\d{3})*(?:[.,]\d{2})|\d+[.,]\d{2}"
_DATE = (
    r"\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}"
    r"|\d{1,2}\s+de\s+[a-záéíóú]+\s+de\s+\d{4}"
    r"|\d{4}-\d{2}-\d{2}"
)
_IBAN = r"\b[A-Z]{2}\d{2}[\sA-Z0-9]{11,30}\b"
_TAX_ID = r"\b[A-Z]?\d{7,8}[A-Z]?\b"
_DNI = r"\b\d{8}[-\s]?[A-Z]\b"
_NIE = r"\b[XYZ][-\s]?\d{7}[-\s]?[A-Z]\b"
_EMAIL = r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"

# doc_type -> ordered list of (field, regex, context_window). If `context` is set,
# the match must appear within ~60 chars after a line containing that keyword.
_RULES: dict[str, list[tuple[str, str, str | None]]] = {
    "invoice": [
        ("total", _AMOUNT, r"total|importe|a pagar|amount due"),
        ("date", _DATE, r"fecha|date"),
        ("tax_id", _TAX_ID, r"c\.?i\.?f|n\.?i\.?f|vat|tax id"),
        ("invoice_number", r"[A-Z0-9][A-Z0-9/\-]{2,}", r"factura n|n\.? factura|invoice n|invoice no"),
    ],
    "receipt": [
        ("total", _AMOUNT, r"total"),
        ("date", _DATE, None),
    ],
    "payslip": [
        ("net_pay", _AMOUNT, r"l[ií]quido a percibir|total a percibir|net pay"),
        ("gross_pay", _AMOUNT, r"total devengado|devengos|gross"),
        ("period", r"\d{1,2}/\d{4}|[a-záéíóú]+\s+\d{4}", r"per[ií]odo|mes|period"),
    ],
    "id_document": [
        ("document_number", rf"{_DNI}|{_NIE}", None),
        ("birth_date", _DATE, r"nacimiento|birth"),
    ],
    "bank_statement": [
        ("iban", _IBAN, None),
        ("closing_balance", _AMOUNT, r"saldo final|closing balance|saldo disponible"),
    ],
    "delivery_note": [
        ("order_number", r"[A-Z0-9][A-Z0-9/\-]{2,}", r"pedido|order"),
    ],
    "cv": [
        ("email", _EMAIL, None),
        ("phone", r"\+?\d[\d\s().-]{7,}\d", r"tel[ée]fono|phone|m[óo]vil"),
    ],
}

_COMPILED: dict[str, list[tuple[str, re.Pattern[str], re.Pattern[str] | None]]] = {
    dt: [
        (name, re.compile(rx, re.IGNORECASE), re.compile(ctx, re.IGNORECASE) if ctx else None)
        for name, rx, ctx in rules
    ]
    for dt, rules in _RULES.items()
}


def _find(text: str, rx: re.Pattern[str], ctx: re.Pattern[str] | None) -> str | None:
    if ctx is None:
        m = rx.search(text)
        return m.group(0).strip() if m else None
    for cm in ctx.finditer(text):
        window = text[cm.end() : cm.end() + 80]
        m = rx.search(window)
        if m:
            return m.group(0).strip()
    return None


def extract_fields(text: str, doc_type: str | None) -> DocExtraction | None:
    if not doc_type or doc_type not in _COMPILED:
        return None
    fields: dict[str, DocExtractionField] = {}
    for name, rx, ctx in _COMPILED[doc_type]:
        value = _find(text, rx, ctx)
        if value:
            fields[name] = DocExtractionField(value=value, raw=value, confidence=0.6)
    if not fields:
        return None
    return DocExtraction(doc_type=doc_type, fields=fields)


def _llm_extract(text: str, doc_type: str | None) -> DocExtraction | None:
    raise NotImplementedError("OCR_EXTRACTOR=llm requiere un proveedor. Implementa app/services/ocr/llm.py.")


def extract(result: OcrResult) -> DocExtraction | None:
    mode = settings.ocr_extractor
    if mode == "none":
        return None
    doc_type = result.classification.doc_type if result.classification else None
    if mode == "llm":
        return _llm_extract(result.text, doc_type)
    return extract_fields(result.text, doc_type)
