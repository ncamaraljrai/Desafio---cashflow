"""Composition root: only this layer assembles concrete adapters."""

import argparse
import logging
import signal
import threading

import httpx
import uvicorn

from cashflow.application.relay import deliver_batch
from cashflow.config import Settings
from cashflow.infrastructure.storage import LedgerStore, SummaryStore
from cashflow.infrastructure.transport import HttpEventTransport
from cashflow.presentation.api import ledger_app, summary_app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("service", choices=["ledger", "summary", "relay"])
    parser.add_argument("--port", type=int)
    args = parser.parse_args()
    settings = Settings.from_env()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if args.service == "relay":
        stopped = threading.Event()
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda *_: stopped.set())
        store = LedgerStore(settings.ledger_db)
        with httpx.Client(timeout=3, trust_env=False) as client:
            transport = HttpEventTransport(client, settings.summary_url, settings.event_token)
            while not stopped.is_set():
                try:
                    count = deliver_batch(store, transport)
                except Exception:
                    logging.exception("relay_batch_failed")
                    count = 0
                stopped.wait(0.05 if count else 0.5)
    else:
        app = (
            ledger_app(LedgerStore(settings.ledger_db), settings.api_token)
            if args.service == "ledger"
            else summary_app(
                SummaryStore(settings.summary_db), settings.api_token, settings.event_token
            )
        )
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=args.port or (8000 if args.service == "ledger" else 8001),
            access_log=False,
            limit_concurrency=200,
            timeout_keep_alive=5,
        )


if __name__ == "__main__":
    main()
