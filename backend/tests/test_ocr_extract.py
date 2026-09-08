from __future__ import annotations

from app.schemas.ocr import DocClassification, OcrResult
from app.services.ocr.extractor import extract, extract_fields


def test_extract_invoice_fields():
    text = "FACTURA Nº A-2043\nFecha: 12/03/2026\nCIF: B12345678\nBase imponible 100,00\nTotal a pagar 121,00 EUR\n"
    out = extract_fields(text, "invoice")
    assert out is not None
    assert out.fields["total"].value == "121,00"
    assert out.fields["tax_id"].value == "B12345678"
    assert out.fields["date"].value == "12/03/2026"


def test_extract_bank_statement_iban():
    out = extract_fields("Titular\nIBAN ES91 2100 0418 4502 0005 1332\nSaldo final 1.234,56", "bank_statement")
    assert out is not None
    assert out.fields["iban"].value.replace(" ", "").startswith("ES91")
    assert out.fields["closing_balance"].value == "1.234,56"


def test_extract_unknown_type_returns_none():
    assert extract_fields("anything", None) is None
    assert extract_fields("anything", "not_a_type") is None


def test_extract_respects_config(monkeypatch):
    from app.config import settings

    result = OcrResult(
        engine="fake",
        lang="es",
        page_count=1,
        pages=[],
        text="Total a pagar 50,00",
        processing_ms=1,
        classification=DocClassification(doc_type="invoice", confidence=0.9, scores={}),
    )
    monkeypatch.setattr(settings, "ocr_extractor", "none")
    assert extract(result) is None
    monkeypatch.setattr(settings, "ocr_extractor", "rules")
    assert extract(result) is not None
