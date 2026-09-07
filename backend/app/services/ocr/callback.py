"""OCR job webhook callbacks: SSRF-guarded delivery with an HMAC signature.

Receivers verify authenticity with:
    expected = "sha256=" + hmac_sha256(OCR_CALLBACK_SIGNING_SECRET, f"{X-OCR-Timestamp}." + raw_body)
    constant_time_compare(expected, X-OCR-Signature)

Note: `_resolve_and_check` closes the common SSRF vectors (private-range targets,
redirect following) but not DNS rebinding between the check and the socket connect.
For hostile multi-tenant use, pair this with network egress policy.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import logging
import socket
import time
from urllib.parse import urlparse

import anyio.to_thread
import httpx

from app.config import settings
from app.exceptions import ValidationException

logger = logging.getLogger("app.ocr.worker")

_BLOCKED_HOSTNAMES = {"localhost", "localhost.localdomain", "ip6-localhost", "ip6-loopback"}

_IPAddr = ipaddress.IPv4Address | ipaddress.IPv6Address


def _is_blocked_ip(ip: _IPAddr) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _host_allowed(host: str, allowed: list[str]) -> bool:
    return any(host == a or host.endswith("." + a) for a in allowed)


def validate_callback_url(url: str | None) -> str | None:
    """Cheap synchronous checks at job-creation time (scheme, allowlist, literal private IPs)."""
    if not url or not url.strip():
        return None
    url = url.strip()
    if len(url) > 1024:
        raise ValidationException("callback_url demasiado larga (máx. 1024).")

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValidationException("callback_url debe ser una URL http(s).")
    host = (parsed.hostname or "").lower()
    if not host:
        raise ValidationException("callback_url sin host.")

    allowed = settings.ocr_callback_allowed_hosts_list
    if allowed and not _host_allowed(host, allowed):
        raise ValidationException("El host de callback_url no está en la lista permitida.")

    if settings.ocr_callback_allow_private:
        return url

    if host in _BLOCKED_HOSTNAMES:
        raise ValidationException("callback_url apunta a una dirección no permitida.")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None and _is_blocked_ip(ip):
        raise ValidationException("callback_url apunta a una IP privada o reservada.")
    return url


class CallbackBlocked(Exception):
    pass


def _resolve_and_check(host: str) -> None:
    if settings.ocr_callback_allow_private:
        return
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise CallbackBlocked(f"host irresoluble: {host}") from exc
    for info in infos:
        addr = str(info[4][0])
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if _is_blocked_ip(ip):
            raise CallbackBlocked(f"{host} -> IP no permitida {addr}")


def sign_payload(body: bytes, timestamp: str) -> str:
    mac = hmac.new(
        settings.ocr_callback_secret.encode(),
        timestamp.encode() + b"." + body,
        hashlib.sha256,
    )
    return "sha256=" + mac.hexdigest()


async def deliver(url: str, payload: dict) -> str:
    """POST `payload` as signed JSON. Returns a short status string for `ocr_jobs.callback_status`."""
    host = (urlparse(url).hostname or "").lower()

    allowed = settings.ocr_callback_allowed_hosts_list
    if allowed and not _host_allowed(host, allowed):
        logger.warning("callback a %s bloqueado: host fuera de la lista permitida", host)
        return "blocked:host_not_allowed"
    try:
        await anyio.to_thread.run_sync(_resolve_and_check, host)  # DNS lookup off the loop
    except CallbackBlocked as exc:
        logger.warning("callback a %s bloqueado: %s", host, exc)
        return f"blocked:{exc}"[:64]

    body = json.dumps(payload, separators=(",", ":"), default=str).encode()
    ts = str(int(time.time()))
    headers = {
        "Content-Type": "application/json",
        "X-OCR-Timestamp": ts,
        "X-OCR-Signature": sign_payload(body, ts),
        "User-Agent": "fastapi-ocr-callback/1",
    }

    status = "unsent"
    async with httpx.AsyncClient(
        timeout=settings.ocr_callback_timeout_seconds, follow_redirects=False
    ) as client:
        for _attempt in range(2):
            try:
                resp = await client.post(url, content=body, headers=headers)
                status = f"http_{resp.status_code}"
                if resp.is_success:
                    return status
            except httpx.HTTPError as exc:
                status = f"error:{type(exc).__name__}"
    logger.warning("callback a %s no confirmado: %s", host or url, status)
    return status
