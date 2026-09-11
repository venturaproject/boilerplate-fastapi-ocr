"""End-to-end: an ApiClient.ocr_extractor_override pins the effective extractor mode for
that client's requests regardless of the global OCR_EXTRACTOR — and the two clients below
upload byte-identical files, which also exercises the extractor_mode-aware cache key
(app/services/ocr/cache.py) — without it these two calls would collide.
"""

from __future__ import annotations

import hashlib
import io
import secrets
from datetime import UTC, datetime, timedelta

from PIL import Image

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.api_client import ApiClient, ApiClientToken
from app.schemas.ocr import OcrLine, OcrPage
from app.services.ocr import llm

CLASSIFY = "/api/ext/ocr/classify"

DELIVERY_NOTE = (
    "NOTA DE ENTREGA\nNumero de pedido: 88214\n"
    "Se hace entrega en el domicilio de Talleres Rodriguez S.A. del siguiente material: "
    "Filtro de aceite modelo XY-330, referencia FR-330-A, en una cantidad total de 120 unidades."
)


async def _issue_client(name: str, *, ocr_extractor_override: str | None) -> str:
    raw = "tok_" + secrets.token_hex(8)
    async with AsyncSessionLocal() as s, s.begin():
        client_row = ApiClient(
            name=name,
            client_id="cli_" + secrets.token_hex(6),
            secret_hash="x",
            scopes=["ocr:write", "ocr:read"],
            ocr_extractor_override=ocr_extractor_override,
        )
        s.add(client_row)
        await s.flush()
        s.add(
            ApiClientToken(
                client_id=client_row.id,
                scopes=client_row.scopes,
                access_token_hash=hashlib.sha256(raw.encode()).hexdigest(),
                refresh_token_hash=secrets.token_hex(16),
                access_expires_at=datetime.now(tz=UTC) + timedelta(hours=1),
                refresh_expires_at=datetime.now(tz=UTC) + timedelta(days=1),
            )
        )
    return raw


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


def _fake_llm_client(calls: list):
    class _Client:
        def __init__(self, *a, **k) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a) -> bool:
            return False

        def post(self, *a, **k):
            calls.append(1)

            class _Resp:
                status_code = 200

                def json(self):
                    return {"choices": [{"message": {"content": '{"client": "Talleres Rodriguez S.A."}'}}]}

            return _Resp()

    return _Client


async def test_client_override_pins_rules_despite_global_llm(client, monkeypatch):
    monkeypatch.setattr(settings, "ocr_extractor", "llm")  # global default
    monkeypatch.setattr(settings, "ocr_llm_api_key", "test-key")
    calls: list = []
    monkeypatch.setattr(llm.httpx, "Client", _fake_llm_client(calls))
    _force_text(monkeypatch, DELIVERY_NOTE)

    pinned_token = await _issue_client("pinned-to-rules", ocr_extractor_override="rules")

    r = await client.post(CLASSIFY, files={"file": ("f.png", _png(), "image/png")}, headers=_auth(pinned_token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["doc_type"] == "delivery_note"
    # rules-mode delivery_note only extracts order_number — never the llm-only fields.
    extraction = body["extraction"]
    if extraction:
        assert "client" not in extraction["fields"]
    assert not calls, "the pinned client's request must never reach the LLM provider"


async def test_client_without_override_inherits_global_llm(client, monkeypatch):
    monkeypatch.setattr(settings, "ocr_extractor", "llm")
    monkeypatch.setattr(settings, "ocr_llm_api_key", "test-key")
    calls: list = []
    monkeypatch.setattr(llm.httpx, "Client", _fake_llm_client(calls))
    _force_text(monkeypatch, DELIVERY_NOTE)

    default_token = await _issue_client("no-override", ocr_extractor_override=None)

    r = await client.post(CLASSIFY, files={"file": ("f.png", _png(), "image/png")}, headers=_auth(default_token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["extraction"]["fields"]["client"]["value"] == "Talleres Rodriguez S.A."
    assert calls, "expected the llm extractor to actually be invoked"
