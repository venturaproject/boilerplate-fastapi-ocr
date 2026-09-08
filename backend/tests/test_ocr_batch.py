from __future__ import annotations

import io
import zipfile

from PIL import Image

from app.ocr.processor import drain_once

BATCH = "/api/ext/ocr/jobs:batch"


def _png(n: int = 1) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (30 + n, 20), "white").save(buf, format="PNG")
    return buf.getvalue()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_batch_of_files(client, ocr_token):
    files = [("files", (f"d{i}.png", _png(i), "image/png")) for i in range(3)]
    r = await client.post(BATCH, files=files, headers=_auth(ocr_token))
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["count"] == 3
    assert len(body["jobs"]) == 3
    assert all(j["status"] == "pending" for j in body["jobs"])

    batch_id = body["batch_id"]
    assert await drain_once() == 3

    r = await client.get(f"/api/ext/ocr/batches/{batch_id}", headers=_auth(ocr_token))
    assert r.status_code == 200
    assert r.json()["total"] == 3
    assert r.json()["counts"].get("done") == 3


async def test_batch_from_zip(client, ocr_token):
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w") as zf:
        zf.writestr("a.png", _png(1))
        zf.writestr("b.png", _png(2))
        zf.writestr("notes.txt", b"ignored - unsupported type")
    r = await client.post(
        BATCH,
        files=[("files", ("bundle.zip", zbuf.getvalue(), "application/zip"))],
        headers=_auth(ocr_token),
    )
    assert r.status_code == 202, r.text
    assert r.json()["count"] == 2  # the .txt entry is skipped


async def test_batch_status_not_found(client, ocr_token):
    r = await client.get("/api/ext/ocr/batches/00000000-0000-0000-0000-000000000000", headers=_auth(ocr_token))
    assert r.status_code == 404


async def test_jobs_filter_by_batch(client, ocr_token):
    files = [("files", (f"d{i}.png", _png(i), "image/png")) for i in range(2)]
    batch_id = (await client.post(BATCH, files=files, headers=_auth(ocr_token))).json()["batch_id"]

    r = await client.get(f"/api/ext/ocr/jobs?batch_id={batch_id}", headers=_auth(ocr_token))
    assert r.json()["total"] == 2
