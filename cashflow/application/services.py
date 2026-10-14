from cashflow.application.ports import Ledger, Projection
from cashflow.domain.model import Entry, validate_day, validate_event


class RecordEntry:
    def __init__(self, ledger: Ledger):
        self.ledger = ledger

    def execute(
        self, key: str, kind: str, amount_cents: int, business_date: str, description: str = ""
    ):
        if not key or len(key) > 128:
            raise ValueError("Idempotency-Key must contain 1..128 characters")
        return self.ledger.record(Entry.create(kind, amount_cents, business_date, description), key)


class Consolidate:
    def __init__(self, projection: Projection):
        self.projection = projection

    def receive(self, event: dict):
        validate_event(event)
        return self.projection.consume(event)

    def report(self, day: str):
        return self.projection.report(validate_day(day))
