"""Rule-based document-type classifier over the OCR text.

Pluggable like the engine (`OCR_CLASSIFIER=none|rules`). Keyword/regex signals per
type, accent-insensitive, scored on the first pages' text. Returns the dominant
type plus a normalised score vector; below the configured thresholds -> `None`
(unknown).
"""

from __future__ import annotations

import re
import unicodedata

from app.config import settings
from app.schemas.ocr import DocClassification, OcrResult

# Only the first N characters are considered — doc type is almost always
# determinable from the first page.
_HEAD_CHARS = 8000

# (regex, weight) per type. Patterns are written already normalised: lowercase, no accents.
_RAW_RULES: dict[str, list[tuple[str, float]]] = {
    "invoice": [
        (r"\bfactura\b", 2.0),
        (r"\b(n\.?\s?factura|numero de factura|factura n)\b", 1.5),
        (r"\bbase imponible\b", 2.0),
        (r"\b(i\.?\s?v\.?\s?a\.?|impuesto sobre el valor anadido)\b", 1.5),
        (r"\b(total a pagar|importe total|total factura)\b", 1.5),
        (r"\b(c\.?\s?i\.?\s?f\.?|n\.?\s?i\.?\s?f\.?)\b", 1.0),
        (r"\b(vencimiento|forma de pago|fecha de emision)\b", 1.0),
        (r"\binvoice\b", 2.0),
        (r"\b(vat|tax id)\b", 1.0),
        (r"\b(amount due|total due|bill to)\b", 1.5),
    ],
    "cv": [
        (r"\b(curriculum vitae|curriculum|resume|hoja de vida)\b", 2.5),
        (r"\bexperiencia( laboral| profesional)?\b", 1.0),
        (r"\b(formacion( academica)?|educacion|estudios|titulacion)\b", 1.0),
        (r"\bidiomas\b", 1.0),
        (r"\b(aptitudes|habilidades|competencias|conocimientos)\b", 1.0),
        (r"\b(perfil profesional|perfil personal|sobre mi|objetivo profesional)\b", 1.0),
        (r"\b(datos personales|informacion de contacto|referencias)\b", 1.0),
        (r"\b(work experience|professional experience|employment history)\b", 2.0),
        (r"\beducation\b", 1.0),
        (r"\bskills\b", 1.0),
        (r"\breferences\b", 0.5),
    ],
    "payslip": [
        (r"\b(nomina|recibo de salarios|recibo individual justificativo)\b", 2.5),
        (r"\bdevengos\b", 2.0),
        (r"\bdeducciones\b", 2.0),
        (r"\b(base de cotizacion|cotizacion a la seguridad social)\b", 2.0),
        (r"\b(liquido a percibir|total a percibir|salario neto)\b", 1.5),
        (r"\birpf\b", 1.0),
        (r"\b(numero de afiliacion|n\.?\s?afiliacion)\b", 1.0),
        (r"\b(payslip|salary slip|net pay|gross pay)\b", 2.0),
    ],
    "contract": [
        (r"\bcontrato\b", 2.0),
        (r"\breunidos\b", 1.5),
        (r"\bclausul[ao]s?\b", 1.5),
        (r"\b(de una parte|de otra parte|ambas partes|las partes)\b", 1.0),
        (r"\b(estipulaciones|acuerdan lo siguiente|convienen)\b", 1.5),
        (r"\b(en prueba de conformidad|firma de las partes)\b", 1.0),
        (r"\b(agreement|this contract|hereby agree|the parties agree)\b", 1.5),
    ],
    "id_document": [
        (r"\b(documento nacional de identidad|d\.?\s?n\.?\s?i\.?)\b", 2.5),
        (r"\b(pasaporte|passport)\b", 2.5),
        (r"\bapellidos\b", 0.8),
        (r"\b(fecha de nacimiento|nacionalidad|lugar de nacimiento)\b", 1.0),
        (r"\b(numero de soporte|validez|caducidad|fecha de expedicion)\b", 1.0),
        (r"\b(nie|numero de identidad de extranjero)\b", 2.0),
    ],
    "bank_statement": [
        (r"\b(extracto|movimientos de la cuenta|estado de cuenta)\b", 2.0),
        (r"\bsaldo (anterior|inicial|final|disponible)\b", 2.0),
        (r"\b(iban|swift|bic)\b", 1.5),
        (r"\bfecha valor\b", 1.5),
        (r"\b(cargo|abono|debe|haber)\b", 0.5),
        (r"\b(bank statement|account statement|opening balance|closing balance)\b", 2.0),
    ],
    "delivery_note": [
        (r"\balbaran\b", 2.5),
        (r"\b(nota de entrega|nota de envio)\b", 2.0),
        (r"\b(bultos|peso bruto|numero de pedido|referencia de pedido)\b", 1.0),
        (r"\b(delivery note|packing slip|shipped to|dispatch note)\b", 2.0),
    ],
    "receipt": [
        (r"\b(recibo|ticket|tique)\b", 1.5),
        (r"\b(gracias por su compra|conserve su ticket)\b", 2.0),
        (r"\b(t\.?\s?p\.?\s?v\.?|terminal punto de venta)\b", 1.0),
        (r"\b(thank you for your purchase|change due|cash tendered)\b", 1.5),
    ],
}

_RULES: dict[str, list[tuple[re.Pattern[str], float]]] = {
    doc_type: [(re.compile(p), w) for p, w in patterns] for doc_type, patterns in _RAW_RULES.items()
}

DOC_TYPES: tuple[str, ...] = tuple(_RULES)


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def classify_text(text: str) -> DocClassification:
    head = _normalize(text)[:_HEAD_CHARS]

    raw: dict[str, float] = {}
    for doc_type, patterns in _RULES.items():
        score = sum(weight for rx, weight in patterns if rx.search(head))
        if score:
            raw[doc_type] = round(score, 2)

    total = sum(raw.values())
    scores = {t: round(v / total, 4) for t, v in raw.items()} if total else {}

    if not raw:
        return DocClassification(doc_type=None, confidence=0.0, scores={})

    best = max(raw, key=lambda t: raw[t])
    confidence = raw[best] / total
    if raw[best] < settings.ocr_classifier_min_score or confidence < settings.ocr_classifier_min_confidence:
        return DocClassification(doc_type=None, confidence=round(confidence, 4), scores=scores)

    return DocClassification(doc_type=best, confidence=round(confidence, 4), scores=scores)


def _ml_classify(text: str) -> DocClassification:
    """TF-IDF + LogisticRegression. Needs a model trained with
    `scripts/train_classifier.py` (scikit-learn, optional-dep `ml`)."""
    import os

    import joblib

    path = os.path.join(os.path.dirname(__file__), "models", "classifier.joblib")
    if not os.path.exists(path):
        raise RuntimeError(
            "OCR_CLASSIFIER=ml pero no hay modelo. Entrena con "
            "`uv run python scripts/train_classifier.py <dir>` (extra `ml`)."
        )
    pipe = joblib.load(path)
    proba = pipe.predict_proba([text])[0]
    labels = list(pipe.classes_)
    scores = {labels[i]: round(float(proba[i]), 4) for i in range(len(labels))}
    best = max(scores, key=lambda k: scores[k])
    conf = scores[best]
    if conf < settings.ocr_classifier_min_confidence:
        return DocClassification(doc_type=None, confidence=conf, scores=scores)
    return DocClassification(doc_type=best, confidence=conf, scores=scores)


def _llm_classify(text: str) -> DocClassification:
    raise NotImplementedError("OCR_CLASSIFIER=llm requiere un proveedor. Implementa app/services/ocr/llm.py.")


def classify(result: OcrResult) -> DocClassification | None:
    mode = settings.ocr_classifier
    if mode == "none":
        return None
    if mode == "ml":
        return _ml_classify(result.text)
    if mode == "llm":
        return _llm_classify(result.text)
    return classify_text(result.text)
