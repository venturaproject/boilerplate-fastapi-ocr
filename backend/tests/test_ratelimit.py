from __future__ import annotations

LOGIN = "/api/v1/auth/login"


async def test_login_returns_429_after_limit(client):
    # THROTTLE_LOGIN por defecto = 5/60
    statuses = []
    for _ in range(8):
        r = await client.post(LOGIN, json={"login": "x@y.com", "password": "bad"})
        statuses.append(r.status_code)

    assert 429 not in statuses[:5]
    assert statuses[5] == 429
