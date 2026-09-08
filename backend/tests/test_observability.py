from __future__ import annotations

import json
import logging

from app.config import settings
from app.observability.logging import JsonFormatter


async def test_metrics_endpoint(client):
    r = await client.get("/metrics")
    assert r.status_code == 200
    assert "text/plain" in r.headers["content-type"]
    body = r.text
    for name in (
        "ocr_requests_total",
        "ocr_processing_ms",
        "ocr_cache_events_total",
        "ocr_engine_errors_total",
        "ocr_callback_total",
        "ocr_queue_depth",
        "http_requests_total",
    ):
        assert name in body


async def test_metrics_token_gate(client, monkeypatch):
    monkeypatch.setattr(settings, "metrics_token", "s3cr3t")
    assert (await client.get("/metrics")).status_code == 401
    assert (await client.get("/metrics", headers={"Authorization": "Bearer s3cr3t"})).status_code == 200


async def test_request_id_generated_and_echoed(client):
    r = await client.get("/api/health")
    rid = r.headers.get("X-Request-ID")
    assert rid and len(rid) >= 16


async def test_request_id_is_propagated(client):
    r = await client.get("/api/health", headers={"X-Request-ID": "abc-123-trace"})
    assert r.headers["X-Request-ID"] == "abc-123-trace"


def test_json_formatter_emits_parseable_lines():
    rec = logging.LogRecord("app.x", logging.INFO, __file__, 1, "hola %s", ("mundo",), None)
    rec.custom = "field"
    out = json.loads(JsonFormatter().format(rec))
    assert out["level"] == "INFO"
    assert out["logger"] == "app.x"
    assert out["msg"] == "hola mundo"
    assert out["custom"] == "field"
