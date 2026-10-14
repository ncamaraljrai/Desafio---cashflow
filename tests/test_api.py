import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from test_business import entry

from cashflow.application.ports import PermanentDeliveryError
from cashflow.application.relay import deliver_batch
from cashflow.infrastructure.storage import LedgerStore, SummaryStore
from cashflow.presentation.api import ledger_app, summary_app

TOKEN = "a" * 32
EVENT_TOKEN = "b" * 32
AUTH = {"Authorization": "Bearer " + TOKEN}


def test_api_contract_and_auth(tmp_path):
    store = LedgerStore(str(tmp_path / "ledger.db"))
    with TestClient(ledger_app(store, TOKEN)) as client:
        body = {"kind": "credit", "amount_cents": 1234, "business_date": "2026-10-13"}
        assert client.post("/entries", json=body).status_code == 401
        headers = {**AUTH, "Idempotency-Key": "one"}
        response = client.post("/entries", json=body, headers=headers)
        assert response.status_code == 201
        assert client.get(response.headers["Location"], headers=AUTH).json()["amount_cents"] == 1234
        assert client.post("/entries", json=body, headers=headers).status_code == 200
        assert (
            client.post("/entries", json={**body, "amount_cents": 2}, headers=headers).status_code
            == 409
        )
        assert (
            client.post("/entries", json={**body, "amount_cents": 1.5}, headers=headers).status_code
            == 422
        )
        assert (
            client.post(
                "/entries", json={**body, "business_date": "2026-02-30"}, headers=headers
            ).status_code
            == 422
        )
        assert client.get("/health/ready").status_code == 200


def test_summary_scope_and_malformed_event(tmp_path):
    store = SummaryStore(str(tmp_path / "summary.db"))
    with TestClient(summary_app(store, TOKEN, EVENT_TOKEN)) as client:
        assert (
            client.post("/internal/events", headers=AUTH, json=entry().event()).status_code == 401
        )
        headers = {"Authorization": "Bearer " + EVENT_TOKEN}
        assert client.post("/internal/events", headers=headers, json={}).status_code == 422
        assert (
            client.post("/internal/events", headers=headers, json=entry().event()).status_code
            == 200
        )
        assert client.get("/balances/2026-10-13", headers=AUTH).json()["closing_cents"] == 10000


def test_outage_recovery_and_lost_ack(tmp_path):
    ledger = LedgerStore(str(tmp_path / "ledger.db"))
    summary = SummaryStore(str(tmp_path / "summary.db"))

    class Down:
        def send(self, event):
            raise ConnectionError("down")

    for i in range(10):
        ledger.record(entry(cents=100), str(i))
    assert deliver_batch(ledger, Down()) == 0
    assert ledger.stats()["pending"] == 10
    ledger.record(entry(cents=50), "during-outage")

    class LostAck:
        def send(self, event):
            summary.consume(event)
            raise ConnectionError("response lost after commit")

    with ledger.connection() as db:
        db.execute("UPDATE outbox SET next_attempt=0")
    assert deliver_batch(ledger, LostAck()) == 0

    class Up:
        def send(self, event):
            summary.consume(event)

    with ledger.connection() as db:
        db.execute("UPDATE outbox SET next_attempt=0")
    assert deliver_batch(ledger, Up()) == 11
    assert summary.report("2026-10-13")["closing_cents"] == 1050
    assert ledger.stats()["pending"] == 0


def test_atomic_rollback_when_outbox_insert_fails(tmp_path):
    ledger = LedgerStore(str(tmp_path / "ledger.db"))
    with ledger.connection() as db:
        db.execute(
            "CREATE TRIGGER broken BEFORE INSERT ON outbox BEGIN SELECT RAISE(ABORT, 'fail'); END"
        )
    e = entry()
    with pytest.raises(sqlite3.IntegrityError):
        ledger.record(e, "atomic")
    assert ledger.get(e.id) is None


def test_quarantine_does_not_block_valid_event(tmp_path):
    ledger = LedgerStore(str(tmp_path / "ledger.db"))
    first, _ = ledger.record(entry(), "bad")
    ledger.record(entry(), "good")

    class Transport:
        def send(self, event):
            if event["event_id"] == first["id"]:
                raise PermanentDeliveryError()

    assert deliver_batch(ledger, Transport()) == 1
    assert ledger.stats()["quarantined"] == 1


def test_concurrent_ledger_idempotency_and_restart(tmp_path):
    path = str(tmp_path / "ledger.db")
    ledger = LedgerStore(path)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: ledger.record(entry(), "same"), range(20)))
    assert sum(not replay for _, replay in results) == 1
    reopened = LedgerStore(path)
    assert reopened.stats()["pending"] == 1
    assert json.loads(reopened.due()[0]["payload"])["entry"]["amount_cents"] == 10000
