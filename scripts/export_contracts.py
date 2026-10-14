"""Export OpenAPI without credentials or runtime data in artifacts."""

import json
import os
import secrets
import tempfile
from pathlib import Path

from cashflow.ai_main import create_app
from cashflow.infrastructure.storage import LedgerStore, SummaryStore
from cashflow.presentation.api import ledger_app, summary_app

with tempfile.TemporaryDirectory() as folder:
    token, event_token = secrets.token_hex(32), secrets.token_hex(32)
    os.environ.update(
        API_TOKEN=token,
        EVENT_TOKEN=event_token,
        KNOWLEDGE_DB=folder + "/knowledge.db",
        AI_PROVIDER="offline",
    )
    apps = {
        "ledger": ledger_app(LedgerStore(folder + "/ledger.db"), token),
        "summary": summary_app(SummaryStore(folder + "/summary.db"), token, event_token),
        "assistant": create_app(),
    }
    output = Path("docs/contracts")
    output.mkdir(parents=True, exist_ok=True)
    for name, app in apps.items():
        (output / (name + ".openapi.json")).write_text(json.dumps(app.openapi(), indent=2) + "\n")
