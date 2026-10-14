from typing import Protocol

from cashflow.domain.model import Entry


class Ledger(Protocol):
    def record(self, entry: Entry, key: str) -> tuple[dict, bool]: ...
    def get(self, entry_id: str) -> dict | None: ...


class Projection(Protocol):
    def consume(self, event: dict) -> bool: ...
    def report(self, day: str) -> dict: ...


class Outbox(Protocol):
    def due(self, limit: int = 100) -> list[dict]: ...
    def delivered(self, event_id: str) -> None: ...
    def failed(self, event_id: str, attempts: int, permanent: bool = False) -> None: ...


class EventTransport(Protocol):
    def send(self, event: dict) -> None: ...


class PermanentDeliveryError(Exception):
    """Payload rejected: quarantine instead of blocking valid messages."""
