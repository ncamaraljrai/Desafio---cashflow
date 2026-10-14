import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    api_token: str
    event_token: str
    ledger_db: str = "data/ledger.db"
    summary_db: str = "data/summary.db"
    summary_url: str = "http://127.0.0.1:8001"

    def __post_init__(self):
        if min(len(self.api_token), len(self.event_token)) < 32:
            raise ValueError("API_TOKEN and EVENT_TOKEN must each be at least 32 characters")
        if self.api_token == self.event_token:
            raise ValueError("Use separate API_TOKEN and EVENT_TOKEN")

    @classmethod
    def from_env(cls):
        return cls(
            os.environ["API_TOKEN"],
            os.environ["EVENT_TOKEN"],
            os.getenv("LEDGER_DB", "data/ledger.db"),
            os.getenv("SUMMARY_DB", "data/summary.db"),
            os.getenv("SUMMARY_URL", "http://127.0.0.1:8001"),
        )
