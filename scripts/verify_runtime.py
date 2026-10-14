"""Real HTTP fault recovery + paced open-loop benchmark; isolated temp databases."""

import argparse
import asyncio
import json
import os
import platform
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

from cashflow.domain.model import Entry

ROOT = Path(__file__).resolve().parents[1]


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_ready(url):
    with httpx.Client(timeout=1, trust_env=False) as client:
        for _ in range(100):
            try:
                if client.get(url + "/health/ready").status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.1)
    raise RuntimeError("Service failed to start")


async def load(url, token, seconds, profile):
    expected = seconds * 50
    results = []
    auth = {"Authorization": "Bearer " + token}
    async with httpx.AsyncClient(
        timeout=3, trust_env=False, limits=httpx.Limits(max_connections=100)
    ) as client:
        start = time.perf_counter()

        async def request(index, scheduled):
            actual = time.perf_counter()
            try:
                if profile == "read":
                    response = await client.get(url + "/balances/2026-10-13", headers=auth)
                else:
                    response = await client.post(
                        url + "/internal/events",
                        headers=auth,
                        json=Entry.create("credit", 1, "2026-10-13", "load test").event(),
                    )
                ok = response.status_code == 200
            except httpx.HTTPError:
                ok = False
            results.append(
                (ok, (time.perf_counter() - scheduled) * 1000, (actual - scheduled) * 1000)
            )

        tasks = []
        for i in range(expected):
            scheduled = start + i / 50
            await asyncio.sleep(max(0, scheduled - time.perf_counter()))
            tasks.append(asyncio.create_task(request(i, scheduled)))
        await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - start
    latencies = sorted(r[1] for r in results)
    failed = sum(not r[0] for r in results)
    rate = failed / expected
    result = {
        "profile": profile,
        "offered_rps": 50,
        "scheduled": expected,
        "completed": len(results),
        "failed": failed,
        "failure_rate": rate,
        "duration_seconds": round(elapsed, 3),
        "p95_ms_from_scheduled": round(latencies[int(len(latencies) * 0.95) - 1], 2),
        "max_scheduling_delay_ms": round(max(r[2] for r in results), 2),
        "passed": rate <= 0.05 and len(results) == expected,
    }
    print(json.dumps(result), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=int, default=60)
    parser.add_argument("--output", default="docs/verification-runtime.json")
    args = parser.parse_args()
    if not 1 <= args.seconds <= 3600:
        parser.error("--seconds must be in 1..3600")
    processes = []
    with tempfile.TemporaryDirectory() as folder:
        ledger_port, summary_port = free_port(), free_port()
        ledger_url, summary_url = (
            f"http://127.0.0.1:{ledger_port}",
            f"http://127.0.0.1:{summary_port}",
        )
        env = {
            **os.environ,
            "API_TOKEN": secrets.token_hex(32),
            "EVENT_TOKEN": secrets.token_hex(32),
            "LEDGER_DB": folder + "/ledger.db",
            "SUMMARY_DB": folder + "/summary.db",
            "SUMMARY_URL": summary_url,
        }

        def start(service, port=None):
            command = [sys.executable, "-m", "cashflow.main", service]
            if port:
                command += ["--port", str(port)]
            process = subprocess.Popen(
                command, cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            processes.append(process)
            return process

        try:
            start("ledger", ledger_port)
            # Summary has never started: all acknowledgements must still succeed.
            start("relay")
            wait_ready(ledger_url)
            headers = {"Authorization": "Bearer " + env["API_TOKEN"]}
            with httpx.Client(timeout=5, trust_env=False) as client:
                for i in range(30):
                    response = client.post(
                        ledger_url + "/entries",
                        headers={**headers, "Idempotency-Key": f"outage-{i}"},
                        json={"kind": "credit", "amount_cents": 100, "business_date": "2026-10-13"},
                    )
                    assert response.status_code == 201, response.text
                assert (
                    client.get(ledger_url + "/ops/outbox", headers=headers).json()["pending"] == 30
                )
                summary_process = start("summary", summary_port)
                wait_ready(summary_url)
                for _ in range(150):
                    report = client.get(
                        summary_url + "/balances/2026-10-13", headers=headers
                    ).json()
                    if report["closing_cents"] == 3000:
                        break
                    time.sleep(0.1)
                assert report["closing_cents"] == 3000, report
                summary_process.terminate()
                summary_process.wait(timeout=5)
                response = client.post(
                    ledger_url + "/entries",
                    headers={**headers, "Idempotency-Key": "crash-write"},
                    json={"kind": "debit", "amount_cents": 500, "business_date": "2026-10-13"},
                )
                assert response.status_code == 201
                start("summary", summary_port)
                wait_ready(summary_url)
                for _ in range(150):
                    report = client.get(
                        summary_url + "/balances/2026-10-13", headers=headers
                    ).json()
                    if report["closing_cents"] == 2500:
                        break
                    time.sleep(0.1)
                assert report["closing_cents"] == 2500, report
                print("HTTP outage/restart recovery: passed", flush=True)
                read = asyncio.run(load(summary_url, env["API_TOKEN"], args.seconds, "read"))
                ingest = asyncio.run(load(summary_url, env["EVENT_TOKEN"], args.seconds, "ingest"))
                final = client.get(summary_url + "/balances/2026-10-13", headers=headers).json()
                expected = 2500 + ingest["completed"] - ingest["failed"]
                assert final["closing_cents"] == expected, (final, expected)
            result = {
                "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "python": platform.python_version(),
                "platform": platform.platform(),
                "cpu_count": os.cpu_count(),
                "fault_recovery": "passed",
                "profiles": [read, ingest],
                "reconciliation": "passed",
                "scope": "Local loopback single-instance SQLite; not a production HA certification",
            }
            Path(args.output).write_text(json.dumps(result, indent=2) + "\n")
            assert read["passed"] and ingest["passed"]
        finally:
            for process in processes:
                if process.poll() is None:
                    process.terminate()
            for process in processes:
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


if __name__ == "__main__":
    main()
