from concurrent.futures import ThreadPoolExecutor

import pytest

from cashflow.domain.model import Conflict, Entry
from cashflow.infrastructure.storage import LedgerStore, SummaryStore


def entry(kind="credit", cents=10000, day="2026-10-13"):
    return Entry.create(kind, cents, day, "Example")


def test_daily_and_running_balance(tmp_path):
    store = SummaryStore(str(tmp_path / "summary.db"))
    for e in [entry(cents=10000, day="2026-10-12"), entry(cents=5000), entry("debit", 2500)]:
        store.consume(e.event())
    report = store.report("2026-10-13")
    assert report["opening_cents"] == 10000
    assert report["credits_cents"] == 5000
    assert report["debits_cents"] == 2500
    assert report["net_cents"] == 2500
    assert report["closing_cents"] == 12500


def test_outbox_atomic_and_idempotency(tmp_path):
    store = LedgerStore(str(tmp_path / "ledger.db"))
    saved, replay = store.record(entry(), "request-1")
    duplicate, replay = store.record(entry(), "request-1")
    assert replay and saved == duplicate
    assert len(store.due()) == 1
    with pytest.raises(Conflict):
        store.record(entry(cents=99), "request-1")


def test_duplicate_and_corrupted_event(tmp_path):
    store = SummaryStore(str(tmp_path / "summary.db"))
    event = entry().event()
    assert store.consume(event)
    assert not store.consume(event)
    event["entry"]["amount_cents"] = 3
    with pytest.raises(Conflict):
        store.consume(event)
    assert store.report("2026-10-13")["closing_cents"] == 10000


def test_concurrent_duplicate(tmp_path):
    store = SummaryStore(str(tmp_path / "summary.db"))
    event = entry().event()
    with ThreadPoolExecutor(max_workers=8) as pool:
        applied = list(pool.map(lambda _: store.consume(event), range(20)))
    assert sum(applied) == 1
    assert store.report("2026-10-13")["credits_cents"] == 10000


@pytest.mark.parametrize("amount", [0, -1, 1.2, True, 10**12 + 1])
def test_invalid_money(amount):
    with pytest.raises(ValueError):
        entry(cents=amount)


def test_late_event_recalculates_opening(tmp_path):
    store = SummaryStore(str(tmp_path / "summary.db"))
    store.consume(entry("debit", 200).event())
    store.consume(entry(cents=1000, day="2026-10-12").event())
    assert store.report("2026-10-13")["closing_cents"] == 800
    assert store.report("2026-10-14")["opening_cents"] == 800
