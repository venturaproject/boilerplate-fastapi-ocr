from __future__ import annotations

from app.services.ocr.langs import detect_lang, tesseract_lang


def test_detect_lang_spanish():
    text = (
        "La factura corresponde a los servicios prestados en el mes de enero. "
        "El total incluye el impuesto sobre el valor añadido y se debe abonar "
        "antes del día 15 por transferencia a la cuenta indicada."
    )
    assert detect_lang(text) == "es"


def test_detect_lang_english():
    text = (
        "This invoice covers the services provided during the month of January. "
        "The total includes the value added tax and must be paid to the account "
        "shown below before the fifteenth of the month."
    )
    assert detect_lang(text) == "en"


def test_detect_lang_unclear_returns_none():
    assert detect_lang("FACTURA 123 456 789") is None
    assert detect_lang("") is None


def test_tesseract_lang_mapping():
    assert tesseract_lang("es") == "spa"
    assert tesseract_lang("german") == "deu"
    assert tesseract_lang("klingon") == "eng"
