"""LLM-based structured field extraction (`OCR_EXTRACTOR=llm`).

Calls an OpenAI-compatible chat-completions endpoint (NVIDIA NIM by default —
point `OCR_LLM_BASE_URL` elsewhere for OpenAI itself, a local vLLM/Ollama
server, etc) with the OCR text and a fixed field schema for the detected
`doc_type`, and asks for a strict JSON object back.

Runs synchronously: the caller (`extractor.extract`) already executes inside
the OCR worker thread (see `service._process_sync`), off the event loop, so a
blocking `httpx.Client` call here is fine and simpler than juggling an event
loop from a thread. It does mean this request counts against
`OCR_MAX_CONCURRENCY` like OCR inference itself — keep `OCR_LLM_TIMEOUT_SECONDS`
tight so one slow provider call can't starve the pipeline.

Deliberately best-effort: any failure (missing key, network, timeout, bad
JSON, a field the model didn't return) drops the extraction rather than
raising — same "misses beat wrong values" policy as the rules extractor.

Data minimization: with `OCR_LLM_REDACT_PII` (default on), the text is passed
through `redact.redact_pii` before it leaves to the provider — masks emails,
IBANs, card numbers, DNI/NIE, phone numbers. It does NOT anonymize the fields
we're asking the model to extract (client/product/reference/quantity aren't
PII patterns) — that data necessarily reaches whichever provider is configured
in `OCR_LLM_BASE_URL`. For documents where that's not acceptable, either point
`OCR_LLM_BASE_URL` at a self-hosted model (no data leaves your infra) or set
`OCR_EXTRACTOR=rules`/`none`.
"""

from __future__ import annotations

import json
import logging

import httpx

from app.config import settings
from app.schemas.ocr import DocExtraction, DocExtractionField
from app.services.ocr.redact import redact_pii

logger = logging.getLogger("app.services.ocr")

_CONFIDENCE = 0.5  # fixed — the provider doesn't give us a calibrated score

# doc_type -> {field_name: prompt description}. Add a doc_type here to enable
# LLM extraction for it; unlisted types fall through to `extract() -> None`.
FIELDS: dict[str, dict[str, str]] = {
    "delivery_note": {
        "client": "Nombre del cliente o destinatario de la mercancía",
        "product": "Descripción del producto o artículo principal de la línea",
        "reference": "Referencia o código de producto/pedido",
        "quantity": "Número de unidades o cantidad entregada, solo el número",
    },
}

_SYSTEM_PROMPT = (
    "Extraes datos de documentos escaneados a partir de su texto OCR (puede tener "
    "errores de reconocimiento). Devuelve EXCLUSIVAMENTE un objeto JSON plano, sin "
    "explicación ni bloque markdown. Usa como claves los campos pedidos que "
    "encuentres con certeza en el texto; omite cualquier campo que no aparezca "
    "claramente. No inventes ni deduzcas valores que no estén en el texto."
)


def _build_prompt(text: str, fields: dict[str, str]) -> str:
    field_lines = "\n".join(f"- {name}: {desc}" for name, desc in fields.items())
    if settings.ocr_llm_redact_pii:
        text = redact_pii(text)  # strip incidental PII before it leaves to the provider
    excerpt = text[:6000]  # bound request size / cost
    return (
        f"Campos a extraer:\n{field_lines}\n\n"
        'Responde con JSON: {"campo": "valor", ...}\n\n'
        f"Texto OCR del documento:\n{excerpt}"
    )


def _call(prompt: str) -> str | None:
    if not settings.ocr_llm_api_key:
        logger.warning("OCR_EXTRACTOR=llm pero OCR_LLM_API_KEY no está configurada")
        return None
    payload = {
        "model": settings.ocr_llm_model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": settings.ocr_llm_max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {settings.ocr_llm_api_key}",
        "Content-Type": "application/json",
    }
    url = f"{settings.ocr_llm_base_url.rstrip('/')}/chat/completions"
    try:
        with httpx.Client(timeout=settings.ocr_llm_timeout_seconds) as client:
            resp = client.post(url, json=payload, headers=headers)
        if resp.status_code != 200:
            logger.warning("LLM extractor: HTTP %s de %s", resp.status_code, url)
            return None
        return resp.json()["choices"][0]["message"]["content"]
    except (httpx.HTTPError, KeyError, IndexError, ValueError, TypeError):
        logger.exception("LLM extractor: fallo llamando al proveedor")
        return None


def _parse_json_object(content: str) -> dict:
    content = content.strip()
    if content.startswith("```"):  # tolerate a ```json ... ``` fenced block
        content = content.strip("`")
        if "\n" in content:
            first_line, rest = content.split("\n", 1)
            content = rest if first_line.strip().lower() in ("", "json") else content
    start, end = content.find("{"), content.rfind("}")
    if start == -1 or end == -1 or end < start:
        return {}
    try:
        obj = json.loads(content[start : end + 1])
    except ValueError:
        return {}
    return obj if isinstance(obj, dict) else {}


def extract_fields_llm(text: str, doc_type: str | None) -> DocExtraction | None:
    if not doc_type or doc_type not in FIELDS:
        return None
    fields_spec = FIELDS[doc_type]
    content = _call(_build_prompt(text, fields_spec))
    if not content:
        return None
    parsed = _parse_json_object(content)
    fields: dict[str, DocExtractionField] = {}
    for name in fields_spec:
        value = parsed.get(name)
        if isinstance(value, str) and value.strip():
            fields[name] = DocExtractionField(value=value.strip(), raw=value.strip(), confidence=_CONFIDENCE)
        elif isinstance(value, int | float) and not isinstance(value, bool):
            fields[name] = DocExtractionField(value=str(value), raw=str(value), confidence=_CONFIDENCE)
    if not fields:
        return None
    return DocExtraction(doc_type=doc_type, fields=fields)
