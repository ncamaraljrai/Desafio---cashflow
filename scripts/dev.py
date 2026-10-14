"""Cross-platform local launcher. Credentials are taken from .env/environment."""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path


def main():
    env = dict(os.environ)
    path = Path(".env")
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip() and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                env.setdefault(key.strip(), value.strip())
    processes = []
    try:
        for service in ["ledger", "summary", "relay"]:
            processes.append(
                subprocess.Popen([sys.executable, "-m", "cashflow.main", service], env=env)
            )
        if "--ai" in sys.argv:
            processes.append(subprocess.Popen([sys.executable, "-m", "cashflow.ai_main"], env=env))
        signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
        while all(p.poll() is None for p in processes):
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
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
