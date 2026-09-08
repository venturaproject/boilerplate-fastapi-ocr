"""Prometheus metrics. Exposed at GET /metrics — see app/routers/metrics.py."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# ── OCR ──────────────────────────────────────────────────────────────────────
ocr_requests_total = Counter(
    "ocr_requests_total",
    "OCR requests handled",
    ["mode", "engine", "status"],  # mode: sync|classify|async ; status: ok|error
)
ocr_processing_ms = Histogram(
    "ocr_processing_ms",
    "OCR processing time in milliseconds",
    ["mode", "engine"],
    buckets=(50, 100, 250, 500, 1000, 2500, 5000, 10_000, 30_000, 60_000),
)
ocr_cache_events_total = Counter(
    "ocr_cache_events_total",
    "Sync-endpoint result cache events",
    ["event"],  # hit|miss
)
ocr_engine_errors_total = Counter("ocr_engine_errors_total", "OCR engine failures", ["engine"])
ocr_callback_total = Counter("ocr_callback_total", "Webhook callback delivery outcomes", ["status"])
ocr_queue_depth = Gauge("ocr_queue_depth", "OCR jobs by status (sampled at scrape time)", ["status"])

# ── HTTP (low cardinality: method + status class only) ───────────────────────
http_requests_total = Counter("http_requests_total", "HTTP requests", ["method", "status"])
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30),
)


def record_ocr(*, mode: str, engine: str, status: str, ms: float | None = None) -> None:
    ocr_requests_total.labels(mode=mode, engine=engine, status=status).inc()
    if ms is not None:
        ocr_processing_ms.labels(mode=mode, engine=engine).observe(ms)


def record_cache(event: str) -> None:
    ocr_cache_events_total.labels(event=event).inc()


def record_engine_error(engine: str) -> None:
    ocr_engine_errors_total.labels(engine=engine).inc()


def record_callback(status: str) -> None:
    # collapse "http_500", "error:ConnectError", "blocked:..." into a short class
    short = status.split(":", 1)[0] if ":" in status else status
    ocr_callback_total.labels(status=short).inc()
