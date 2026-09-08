"""Structured logging. `LOG_FORMAT=json` swaps the formatter for one that emits
one JSON object per line (with the request_id when there is one). No dependency."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from app.observability.context import get_request_id

_STD_ATTRS = set(logging.LogRecord("", 0, "", 0, "", None, None).__dict__) | {"message", "asctime", "taskName"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        rid = get_request_id()
        if rid:
            data["request_id"] = rid
        if record.exc_info:
            data["exc"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key not in _STD_ATTRS and not key.startswith("_"):
                data[key] = value
        return json.dumps(data, default=str, ensure_ascii=False)


class RequestIdFilter(logging.Filter):
    """Adds `request_id` to every record so text formatters can show it too."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        return True


_TEXT_FMT = "%(asctime)s %(levelname)-7s [%(request_id)s] %(name)s: %(message)s"


def configure_logging(log_format: str = "text", level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(level.upper())
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(JsonFormatter() if log_format == "json" else logging.Formatter(_TEXT_FMT))
    root.addHandler(handler)

    # uvicorn keeps its own handlers; route them through ours
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers = []
        lg.propagate = True
