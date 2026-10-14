"""Generate local-only tokens without overwriting an existing configuration."""

import secrets
from pathlib import Path

with Path(".env").open("x") as stream:
    stream.write("API_TOKEN=" + secrets.token_hex(32) + "\n")
    stream.write("EVENT_TOKEN=" + secrets.token_hex(32) + "\n")
    stream.write("AI_PROVIDER=offline\nANTHROPIC_API_KEY=\nANTHROPIC_MODEL=\n")
print("Created .env. Keep this file private.")
