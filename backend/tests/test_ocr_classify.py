from __future__ import annotations

import io

from PIL import Image

from app.ocr.processor import drain_once
from app.schemas.ocr import OcrLine, OcrPage
from app.services.ocr.classifier import classify_text

EXT = "/api/ext/ocr"
JOBS = "/api/ext/ocr/jobs"

INVOICE = (
    "FACTURA Nº 2026-014\n"
    "Base imponible: 100,00 EUR\n"
    "IVA 21%: 21,00 EUR\n"
    "Total a pagar: 121,00 EUR\n"
    "CIF: B12345678  ·  Vencimiento: 30 días"
)
CV = (
    "Antonio Ventura — Perfil profesional\n"
    "Experiencia profesional\n- Senior Developer 2020-2026\n"
    "Formación académica\nIdiomas: Español (nativo), Inglés\n"
    "Aptitudes: Python, Rust"
)
PAYSLIP = (
    "Recibo individual justificativo del pago de salarios\n"
    "Devengos ... Deducciones\n"
    "Base de cotización: 2.000,00\nIRPF: 15%\n"
    "Líquido a percibir: 1.650,00"
)


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (48, 24), "white").save(buf, format="PNG")
    return buf.getvalue()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _force_text(monkeypatch, text: str) -> None:
    from app.services.ocr.engine import FakeOcrEngine

    def _recognize(self, pages, lang):
        return [
            OcrPage(
                page=p.index,
                width=p.width,
                height=p.height,
                lines=[OcrLine(text=text, confidence=0.95, box=[[0, 0], [1, 0], [1, 1], [0, 1]])],
                text=text,
            )
            for p in pages
        ]

    monkeypatch.setattr(FakeOcrEngine, "recognize_pages", _recognize)


# ── unit ─────────────────────────────────────────────────────────────────────


def test_classify_invoice():
    c = classify_text(INVOICE)
    assert c.doc_type == "invoice"
    assert c.confidence > 0.6


def test_classify_cv():
    assert classify_text(CV).doc_type == "cv"


def test_classify_payslip():
    assert classify_text(PAYSLIP).doc_type == "payslip"


def test_classify_unknown_for_random_text():
    c = classify_text("the quick brown fox jumps over the lazy dog " * 5)
    assert c.doc_type is None
    assert c.scores == {}


def test_classify_below_threshold_is_unknown():
    # a single weak signal ("idiomas") is not enough
    c = classify_text("Notas varias\nidiomas de programación disponibles")
    assert c.doc_type is None


# ── endpoint + job ───────────────────────────────────────────────────────────


async def test_classify_endpoint(client, ocr_token, monkeypatch):
    _force_text(monkeypatch, INVOICE)
    r = await client.post(
        f"{EXT}/classify",
        files={"file": ("f.png", _png(), "image/png")},
        headers=_auth(ocr_token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["doc_type"] == "invoice"
    assert body["scores"]["invoice"] > 0
    assert body["text_excerpt"].startswith("FACTURA")


async def test_sync_result_carries_classification(client, ocr_token, monkeypatch):
    _force_text(monkeypatch, CV)
    r = await client.post(EXT, files={"file": ("f.png", _png(), "image/png")}, headers=_auth(ocr_token))
    assert r.json()["classification"]["doc_type"] == "cv"


async def test_job_stores_doc_type_and_filters(client, ocr_token, monkeypatch):
    _force_text(monkeypatch, INVOICE)
    r = await client.post(JOBS, files={"file": ("f.png", _png(), "image/png")}, headers=_auth(ocr_token))
    job_id = r.json()["id"]
    await drain_once()

    detail = await client.get(f"{JOBS}/{job_id}", headers=_auth(ocr_token))
    assert detail.json()["doc_type"] == "invoice"

    hit = await client.get(f"{JOBS}?doc_type=invoice", headers=_auth(ocr_token))
    assert hit.json()["total"] == 1
    miss = await client.get(f"{JOBS}?doc_type=cv", headers=_auth(ocr_token))
    assert miss.json()["total"] == 0

    stats = await client.get(f"{EXT}/stats", headers=_auth(ocr_token))
    assert stats.json()["by_doc_type"] == {"invoice": 1}


async def test_classifier_can_be_disabled(client, ocr_token, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "ocr_classifier", "none")
    _force_text(monkeypatch, INVOICE)
    r = await client.post(EXT, files={"file": ("f.png", _png(), "image/png")}, headers=_auth(ocr_token))
    assert r.json()["classification"] is None
