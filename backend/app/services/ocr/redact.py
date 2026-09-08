"""Best-effort PII masking for text that gets stored (`documents.text_excerpt`).

Regex-only, tuned for ES documents (payslips, bank statements, ID docs). Enabled
with `DOCUMENT_REDACT_PII=true`. It masks; it does not guarantee removal.
"""

from __future__ import annotations

import re

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[EMAIL]"),
    (re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){2,7}\b"), "[IBAN]"),
    (re.compile(r"\b(?:\d[ -]?){13,16}\d\b"), "[CARD]"),
    (re.compile(r"\b[XYZ][- ]?\d{7}[- ]?[A-Za-z]\b"), "[NIE]"),
    (re.compile(r"\b\d{8}[- ]?[A-Za-z]\b"), "[DNI]"),
    (re.compile(r"(?<!\d)(?:\+?34[ -]?)?[6-9]\d{2}[ -]?\d{2}[ -]?\d{2}[ -]?\d{2}(?!\d)"), "[PHONE]"),
]


def redact_pii(text: str) -> str:
    for rx, repl in _PATTERNS:
        text = rx.sub(repl, text)
    return text
