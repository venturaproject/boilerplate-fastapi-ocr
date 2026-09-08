from __future__ import annotations

from app.services.ocr.redact import redact_pii


def test_redact_masks_common_pii():
    text = (
        "Contacto: juan.perez@example.com tel 612 34 56 78\n"
        "DNI 12345678Z  NIE X1234567L\n"
        "IBAN ES91 2100 0418 4502 0005 1332\n"
        "Tarjeta 4111 1111 1111 1111"
    )
    out = redact_pii(text)
    assert "@example.com" not in out and "[EMAIL]" in out
    assert "12345678Z" not in out and "[DNI]" in out
    assert "X1234567L" not in out and "[NIE]" in out
    assert "ES91" not in out and "[IBAN]" in out
    assert "4111" not in out and "[CARD]" in out
    assert "[PHONE]" in out


def test_redact_leaves_plain_text():
    assert redact_pii("FACTURA total 121,00 EUR") == "FACTURA total 121,00 EUR"
