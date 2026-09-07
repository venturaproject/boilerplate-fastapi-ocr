from __future__ import annotations

ROLES = "/api/v1/roles"
PERMISSIONS = "/api/v1/permissions"


async def test_roles_list_is_paginated(admin_client):
    r = await admin_client.get(ROLES)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) >= {"data", "current_page", "last_page", "per_page", "total"}
    assert body["total"] >= 3  # admin / editor / viewer from the seed
    admin_row = next(row for row in body["data"] if row["name"] == "admin")
    assert admin_row["permissions_count"] > 0
    assert admin_row["users_count"] >= 1  # the seeded admin user


async def test_permissions_list_is_paginated_and_filtered(admin_client):
    r = await admin_client.get(PERMISSIONS, params={"per_page": 5})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["per_page"] == 5
    assert len(body["data"]) == 5
    assert body["total"] > 5
    assert body["last_page"] == -(-body["total"] // 5)
    assert "users" in body["groups"]

    r = await admin_client.get(PERMISSIONS, params={"group": "documents"})
    assert r.status_code == 200
    assert {p["name"] for p in r.json()["data"]} == {"documents.view", "documents.delete"}

    r = await admin_client.get(PERMISSIONS, params={"search": "ocr."})
    assert all(p["name"].startswith("ocr.") for p in r.json()["data"])


async def test_roles_search(admin_client):
    r = await admin_client.get(ROLES, params={"search": "edit"})
    assert [row["name"] for row in r.json()["data"]] == ["editor"]
