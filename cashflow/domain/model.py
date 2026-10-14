"""Business rules. No framework, transport or persistence dependencies."""

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from uuid import UUID, uuid4


class Conflict(Exception):
    """A stable identity was reused with different content."""


def validate_day(value: str) -> str:
    if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
        raise ValueError("business_date must be YYYY-MM-DD")
    return value


@dataclass(frozen=True)
class Entry:
    id: str
    kind: str
    amount_cents: int
    business_date: str
    description: str
    created_at: str

    def __post_init__(self):
        UUID(self.id)
        if self.kind not in ("credit", "debit"):
            raise ValueError("kind must be credit or debit")
        if type(self.amount_cents) is not int or not 0 < self.amount_cents <= 10**12:
            raise ValueError("amount_cents must be an integer in 1..1000000000000")
        validate_day(self.business_date)
        if not isinstance(self.description, str) or len(self.description) > 200:
            raise ValueError("description must contain at most 200 characters")
        timestamp = datetime.fromisoformat(self.created_at)
        if timestamp.tzinfo is None:
            raise ValueError("created_at requires timezone")

    @classmethod
    def create(cls, kind, amount_cents, business_date, description=""):
        return cls(
            str(uuid4()),
            kind,
            amount_cents,
            business_date,
            description,
            datetime.now(timezone.utc).isoformat(),
        )

    def event(self):
        return {"event_id": self.id, "type": "EntryRecorded", "version": 1, "entry": asdict(self)}


def validate_event(event: dict) -> Entry:
    if set(event) != {"event_id", "type", "version", "entry"}:
        raise ValueError("invalid event envelope")
    if (
        type(event["version"]) is not int
        or event["version"] != 1
        or event["type"] != "EntryRecorded"
    ):
        raise ValueError("unsupported event contract")
    entry = Entry(**event["entry"])
    if event["event_id"] != entry.id:
        raise ValueError("event_id must equal entry.id for EntryRecorded v1")
    return entry
