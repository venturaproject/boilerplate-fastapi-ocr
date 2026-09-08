"""Accepted PaddleOCR language codes (mirrors `paddleocr.paddleocr.parse_lang` for 2.x).

Validating `lang` at the request boundary gives a clean 422 instead of a model-load
crash, and stops a client from loading an unbounded number of models into memory.
"""

from __future__ import annotations

import re

from app.config import settings
from app.exceptions import ValidationException

_LATIN = {
    "af",
    "az",
    "bs",
    "cs",
    "cy",
    "da",
    "de",
    "es",
    "et",
    "fr",
    "ga",
    "hr",
    "hu",
    "id",
    "is",
    "it",
    "ku",
    "la",
    "lt",
    "lv",
    "mi",
    "ms",
    "mt",
    "nl",
    "no",
    "oc",
    "pi",
    "pl",
    "pt",
    "ro",
    "rs_latin",
    "sk",
    "sl",
    "sq",
    "sv",
    "sw",
    "tl",
    "tr",
    "uz",
    "vi",
    "french",
    "german",
    "latin",
}
_ARABIC = {"ar", "fa", "ug", "ur", "arabic"}
_CYRILLIC = {
    "ru",
    "rs_cyrillic",
    "be",
    "bg",
    "uk",
    "mn",
    "abq",
    "ady",
    "kbd",
    "ava",
    "dar",
    "inh",
    "che",
    "lbe",
    "lez",
    "tab",
    "cyrillic",
}
_DEVANAGARI = {
    "hi",
    "mr",
    "ne",
    "bh",
    "mai",
    "ang",
    "bho",
    "mah",
    "sck",
    "new",
    "gom",
    "sa",
    "bgc",
    "devanagari",
}
_OTHER = {"ch", "en", "korean", "japan", "chinese_cht", "ta", "te", "ka"}

PADDLE_LANGS: frozenset[str] = frozenset(_LATIN | _ARABIC | _CYRILLIC | _DEVANAGARI | _OTHER)


def allowed_langs() -> frozenset[str]:
    configured = settings.ocr_allowed_langs_list
    return frozenset(configured) if configured else PADDLE_LANGS


def resolve_lang(lang: str | None) -> str:
    value = (lang or settings.ocr_lang).strip() or "es"
    if value not in allowed_langs():
        raise ValidationException(
            f"Idioma '{value}' no soportado. Ejemplos: es, en, fr, german, pt, ch, japan, korean."
        )
    return value


# ── Tesseract ────────────────────────────────────────────────────────────────
# Tesseract uses ISO 639-2/T codes; map from the PaddleOCR codes we accept.
_TESSERACT_LANG: dict[str, str] = {
    "es": "spa",
    "en": "eng",
    "fr": "fra",
    "french": "fra",
    "de": "deu",
    "german": "deu",
    "pt": "por",
    "it": "ita",
    "nl": "nld",
    "ca": "cat",
    "gl": "spa",
}


def tesseract_lang(lang: str) -> str:
    return _TESSERACT_LANG.get(lang, "eng")


# ── Language auto-detection ──────────────────────────────────────────────────
# Frequency of very common words per language over the OCR text. Deliberately
# dependency-free and limited to the Latin languages the panel exposes.
_STOPWORDS: dict[str, set[str]] = {
    "es": {"de", "la", "el", "en", "y", "los", "las", "del", "con", "por", "para", "una", "que", "se"},
    "en": {"the", "of", "and", "to", "in", "for", "is", "on", "with", "as", "at", "by", "an", "be"},
    "fr": {"le", "la", "les", "de", "des", "et", "un", "une", "du", "pour", "dans", "que", "est", "au"},
    "german": {"der", "die", "das", "und", "den", "von", "mit", "für", "ist", "im", "auf", "ein", "eine", "nicht"},
    "pt": {"de", "da", "do", "que", "para", "com", "uma", "não", "os", "as", "dos", "das", "por", "em"},
}


def detect_lang(text: str) -> str | None:
    """Best-effort language guess from common-word frequency. `None` if unclear."""
    tokens = [t for t in re.findall(r"[a-zà-ÿ]{2,}", text.lower()) if t]
    if len(tokens) < 12:
        return None
    counts = {lang: sum(t in words for t in tokens) for lang, words in _STOPWORDS.items()}
    best = max(counts, key=lambda k: counts[k])
    total = sum(counts.values())
    if total < 4 or counts[best] < 3 or counts[best] / total < 0.45:
        return None
    return best if best in allowed_langs() else None
