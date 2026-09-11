from __future__ import annotations

import json

from app.config import settings
from app.services.ocr import llm


class _Resp:
    def __init__(self, status_code: int, body: dict) -> None:
        self.status_code = status_code
        self._body = body

    def json(self) -> dict:
        return self._body


def _fake_client(content: str | None, *, status_code: int = 200):
    class _Client:
        def __init__(self, *a, **k) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a) -> bool:
            return False

        def post(self, *a, **k):
            body = {"choices": [{"message": {"content": content}}]} if content is not None else {}
            return _Resp(status_code, body)

    return _Client


def test_unknown_doc_type_returns_none_without_calling_llm(monkeypatch):
    # No API key configured either — if this called out, _call would warn+return None
    # anyway, but we assert the short-circuit happens before that.
    called = False

    def _boom(*a, **k):
        nonlocal called
        called = True
        raise AssertionError("should not call the LLM for an unknown doc_type")

    monkeypatch.setattr(llm.httpx, "Client", _boom)
    assert llm.extract_fields_llm("algún texto", "not_a_type") is None
    assert called is False


def test_no_api_key_is_a_noop(monkeypatch):
    monkeypatch.setattr(settings, "ocr_llm_api_key", "")
    assert llm.extract_fields_llm("texto del albarán", "delivery_note") is None


def test_extract_delivery_note_fields(monkeypatch):
    monkeypatch.setattr(settings, "ocr_llm_api_key", "test-key")
    content = json.dumps(
        {
            "client": "Ferretería García S.L.",
            "product": "Tornillo M6x20 inox",
            "reference": "REF-4471",
            "quantity": 500,
        }
    )
    monkeypatch.setattr(llm.httpx, "Client", _fake_client(content))

    out = llm.extract_fields_llm("albarán de entrega...", "delivery_note")

    assert out is not None
    assert out.doc_type == "delivery_note"
    assert out.fields["client"].value == "Ferretería García S.L."
    assert out.fields["reference"].value == "REF-4471"
    assert out.fields["quantity"].value == "500"  # numeric values are stringified
    assert out.fields["client"].confidence == llm._CONFIDENCE


def test_tolerates_markdown_fenced_json(monkeypatch):
    monkeypatch.setattr(settings, "ocr_llm_api_key", "test-key")
    content = '```json\n{"client": "Acme"}\n```'
    monkeypatch.setattr(llm.httpx, "Client", _fake_client(content))

    out = llm.extract_fields_llm("texto", "delivery_note")

    assert out is not None
    assert out.fields["client"].value == "Acme"


def test_omits_fields_the_model_didnt_return(monkeypatch):
    monkeypatch.setattr(settings, "ocr_llm_api_key", "test-key")
    monkeypatch.setattr(llm.httpx, "Client", _fake_client('{"client": "Acme"}'))

    out = llm.extract_fields_llm("texto", "delivery_note")

    assert out is not None
    assert set(out.fields) == {"client"}


def test_garbage_response_returns_none(monkeypatch):
    monkeypatch.setattr(settings, "ocr_llm_api_key", "test-key")
    monkeypatch.setattr(llm.httpx, "Client", _fake_client("not json at all"))

    assert llm.extract_fields_llm("texto", "delivery_note") is None


def test_non_200_response_returns_none(monkeypatch):
    monkeypatch.setattr(settings, "ocr_llm_api_key", "test-key")
    monkeypatch.setattr(llm.httpx, "Client", _fake_client('{"client": "Acme"}', status_code=500))

    assert llm.extract_fields_llm("texto", "delivery_note") is None


def test_network_error_returns_none(monkeypatch):
    class _Client:
        def __init__(self, *a, **k) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a) -> bool:
            return False

        def post(self, *a, **k):
            raise llm.httpx.ConnectError("connection refused")

    monkeypatch.setattr(settings, "ocr_llm_api_key", "test-key")
    monkeypatch.setattr(llm.httpx, "Client", _Client)

    assert llm.extract_fields_llm("texto", "delivery_note") is None


def test_malformed_response_body_returns_none(monkeypatch):
    # 200 OK but the body doesn't have the expected `choices[0].message.content` shape.
    monkeypatch.setattr(settings, "ocr_llm_api_key", "test-key")

    class _Client:
        def __init__(self, *a, **k) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a) -> bool:
            return False

        def post(self, *a, **k):
            return _Resp(200, {"unexpected": "shape"})

    monkeypatch.setattr(llm.httpx, "Client", _Client)

    assert llm.extract_fields_llm("texto", "delivery_note") is None


def test_boolean_value_is_dropped(monkeypatch):
    # A bool would pass `isinstance(value, int)` in Python — the extractor must
    # not coerce it into a field value.
    monkeypatch.setattr(settings, "ocr_llm_api_key", "test-key")
    monkeypatch.setattr(llm.httpx, "Client", _fake_client('{"client": "Acme", "quantity": true}'))

    out = llm.extract_fields_llm("texto", "delivery_note")

    assert out is not None
    assert "quantity" not in out.fields
    assert out.fields["client"].value == "Acme"


def _capturing_client(content: str, captured: list):
    class _Client:
        def __init__(self, *a, **k) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a) -> bool:
            return False

        def post(self, *a, **kwargs):
            captured.append(kwargs["json"])
            return _Resp(200, {"choices": [{"message": {"content": content}}]})

    return _Client


def test_pii_is_redacted_before_it_leaves_by_default(monkeypatch):
    monkeypatch.setattr(settings, "ocr_llm_api_key", "test-key")
    assert settings.ocr_llm_redact_pii is True  # the default we ship

    captured: list = []
    monkeypatch.setattr(llm.httpx, "Client", _capturing_client('{"client": "Acme"}', captured))

    text = "Cliente: Acme. Contacto: juan@acme.com, tel 612345678, DNI 12345678Z."
    llm.extract_fields_llm(text, "delivery_note")

    sent_prompt = captured[0]["messages"][1]["content"]
    assert "juan@acme.com" not in sent_prompt
    assert "612345678" not in sent_prompt
    assert "12345678Z" not in sent_prompt
    assert "[EMAIL]" in sent_prompt and "[PHONE]" in sent_prompt and "[DNI]" in sent_prompt
    assert "Acme" in sent_prompt  # the target field itself is not touched


def test_pii_redaction_can_be_disabled(monkeypatch):
    monkeypatch.setattr(settings, "ocr_llm_api_key", "test-key")
    monkeypatch.setattr(settings, "ocr_llm_redact_pii", False)

    captured: list = []
    monkeypatch.setattr(llm.httpx, "Client", _capturing_client('{"client": "Acme"}', captured))

    text = "Cliente: Acme. Contacto: juan@acme.com"
    llm.extract_fields_llm(text, "delivery_note")

    assert "juan@acme.com" in captured[0]["messages"][1]["content"]


def test_extract_dispatches_to_llm_mode(monkeypatch):
    from app.schemas.ocr import DocClassification, OcrResult
    from app.services.ocr.extractor import extract

    monkeypatch.setattr(settings, "ocr_extractor", "llm")
    monkeypatch.setattr(settings, "ocr_llm_api_key", "test-key")
    monkeypatch.setattr(llm.httpx, "Client", _fake_client('{"client": "Acme"}'))

    result = OcrResult(
        engine="fake",
        lang="es",
        page_count=1,
        pages=[],
        text="albarán...",
        processing_ms=1,
        classification=DocClassification(doc_type="delivery_note", confidence=0.9, scores={}),
    )
    out = extract(result)
    assert out is not None
    assert out.fields["client"].value == "Acme"
