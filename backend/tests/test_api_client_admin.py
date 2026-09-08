from __future__ import annotations

BASE = "/api/v1/api-clients"


async def _create(admin_client, name: str = "acme") -> dict:
    r = await admin_client.post(BASE, json={"name": name, "scopes": ["ocr:read", "ocr:write"]})
    assert r.status_code == 201, r.text
    return r.json()


async def test_patch_sets_rate_limit_and_quota(admin_client):
    created = await _create(admin_client)
    cid = created["client"]["id"]

    r = await admin_client.patch(f"{BASE}/{cid}", json={"rate_limit": "5/60", "monthly_page_quota": 1000})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["rate_limit"] == "5/60"
    assert body["monthly_page_quota"] == 1000


async def test_patch_rejects_bad_rate_limit(admin_client):
    created = await _create(admin_client)
    cid = created["client"]["id"]

    r = await admin_client.patch(f"{BASE}/{cid}", json={"rate_limit": "nonsense"})
    assert r.status_code == 422


async def test_rotate_secret_returns_new_secret_and_revokes_tokens(admin_client, client):
    created = await _create(admin_client)
    cid = created["client"]["id"]
    client_id = created["client"]["client_id"]
    old_secret = created["secret"]

    # get a bearer with the old secret
    tok = await client.post(
        "/api/ext/auth/token",
        json={"client_id": client_id, "client_secret": old_secret},
    )
    assert tok.status_code == 200, tok.text
    old_bearer = tok.json()["access_token"]

    r = await admin_client.post(f"{BASE}/{cid}/rotate")
    assert r.status_code == 200, r.text
    new_secret = r.json()["secret"]
    assert new_secret != old_secret

    # old bearer no longer works
    me = await client.get("/api/ext/ocr/usage", headers={"Authorization": f"Bearer {old_bearer}"})
    assert me.status_code == 401

    # old secret can no longer mint a token
    bad = await client.post(
        "/api/ext/auth/token",
        json={"client_id": client_id, "client_secret": old_secret},
    )
    assert bad.status_code == 401

    # new secret works
    good = await client.post(
        "/api/ext/auth/token",
        json={"client_id": client_id, "client_secret": new_secret},
    )
    assert good.status_code == 200, good.text


async def test_admin_usage_endpoint(admin_client):
    created = await _create(admin_client)
    cid = created["client"]["id"]
    await admin_client.patch(f"{BASE}/{cid}", json={"monthly_page_quota": 500})

    r = await admin_client.get(f"{BASE}/{cid}/usage")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["pages"] == 0
    assert body["monthly_page_quota"] == 500
    assert body["quota_remaining"] == 500
    assert "/" in body["rate_limit"]


async def test_patch_requires_permission(client):
    r = await client.patch(f"{BASE}/00000000-0000-0000-0000-000000000000", json={"rate_limit": "5/60"})
    assert r.status_code in (401, 403)
