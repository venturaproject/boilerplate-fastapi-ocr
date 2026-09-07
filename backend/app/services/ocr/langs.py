"""Accepted PaddleOCR language codes (mirrors `paddleocr.paddleocr.parse_lang` for 2.x).

Validating `lang` at the request boundary gives a clean 422 instead of a model-load
crash, and stops a client from loading an unbounded number of models into memory.
"""

from __future__ import annotations

from app.config import settings
from app.exceptions import ValidationException

_LATIN = {
    "af", "az", "bs", "cs", "cy", "da", "de", "es", "et", "fr", "ga", "hr", "hu", "id",
    "is", "it", "ku", "la", "lt", "lv", "mi", "ms", "mt", "nl", "no", "oc", "pi", "pl",
    "pt", "ro", "rs_latin", "sk", "sl", "sq", "sv", "sw", "tl", "tr", "uz", "vi",
    "french", "german", "latin",
}
_ARABIC = {"ar", "fa", "ug", "ur", "arabic"}
_CYRILLIC = {
    "ru", "rs_cyrillic", "be", "bg", "uk", "mn", "abq", "ady", "kbd", "ava", "dar",
    "inh", "che", "lbe", "lez", "tab", "cyrillic",
}
_DEVANAGARI = {
    "hi", "mr", "ne", "bh", "mai", "ang", "bho", "mah", "sck", "new", "gom", "sa",
    "bgc", "devanagari",
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
