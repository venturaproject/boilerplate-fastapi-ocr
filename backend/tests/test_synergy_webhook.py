from __future__ import annotations

import logging

from sqlalchemy import func, select

from app.database import AsyncSessionLocal
from app.events.inbox import process_inbox_batch
from app.events.models import InboxMessage, OutboxMessage
from app.events.outbox import process_outbox_batch
from app.models.trabajador import Trabajador

WEBHOOK = "/api/ext/webhooks/synergy"
SID = 900123


def _body(**over):
    base = {"event": "employee.upserted", "synergy_res_id": SID,
            "nombre_completo": "Test User", "email": "t@e.com"}
    base.update(over)
    return base


async def test_webhook_stores_and_dedupes(client, bearer_token):
    h = {"Authorization": f"Bearer {bearer_token}", "X-Message-Id": "m1"}
    r1 = await client.post(WEBHOOK, json=_body(), headers=h)
    r2 = await client.post(WEBHOOK, json=_body(), headers=h)

    assert r1.status_code == 202
    assert r2.status_code == 200
    assert r2.json()["status"] == "duplicate"
    async with AsyncSessionLocal() as s:
        count = (
            await s.execute(select(func.count()).select_from(InboxMessage).where(InboxMessage.message_id == "m1"))
        ).scalar_one()
    assert count == 1


async def test_missing_message_id_is_400(client, bearer_token):
    r = await client.post(WEBHOOK, json=_body(), headers={"Authorization": f"Bearer {bearer_token}"})
    assert r.status_code == 400


async def test_full_flow(client, bearer_token, caplog):
    h = {"Authorization": f"Bearer {bearer_token}", "X-Message-Id": "m1"}
    await client.post(WEBHOOK, json=_body(), headers=h)

    assert await process_inbox_batch() == 1

    async with AsyncSessionLocal() as s:
        t = (await s.execute(select(Trabajador).where(Trabajador.synergy_res_id == SID))).scalar_one()
        inbox = (await s.execute(select(InboxMessage).where(InboxMessage.message_id == "m1"))).scalar_one()
        outbox = (await s.execute(select(OutboxMessage))).scalars().one()
    assert (t.nombre, t.apellido) == ("Test", "User")
    assert inbox.status == "processed"
    assert outbox.event_name == "trabajador.synchronized_from_erp"
    assert outbox.status == "pending"
    assert outbox.payload["created"] is True

    with caplog.at_level(logging.INFO, logger="app.domain.trabajador"):
        assert await process_outbox_batch() == 1
    assert any("desde Synergy" in r.message for r in caplog.records)

    async with AsyncSessionLocal() as s:
        outbox = (await s.execute(select(OutboxMessage))).scalars().one()
    assert outbox.status == "done"


async def test_replayed_message_id_idempotent_sync(client, bearer_token):
    await client.post(WEBHOOK, json=_body(), headers={"Authorization": f"Bearer {bearer_token}", "X-Message-Id": "m1"})
    await client.post(
        WEBHOOK, json=_body(email="new@e.com"),
        headers={"Authorization": f"Bearer {bearer_token}", "X-Message-Id": "m2"},
    )
    await process_inbox_batch()
    await process_inbox_batch()

    async with AsyncSessionLocal() as s:
        rows = (await s.execute(select(Trabajador).where(Trabajador.synergy_res_id == SID))).scalars().all()
    assert len(rows) == 1
    assert rows[0].email == "new@e.com"
