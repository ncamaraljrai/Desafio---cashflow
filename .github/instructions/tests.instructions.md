---
applyTo: "tests/**/*.py"
---
Test observable behavior with real temporary SQLite databases. Include failure before commit, failure after commit/before acknowledgement, concurrent duplicate requests, replay after restart and altered duplicate event. Expected balances must come from independent examples, not the production calculation function. Network tests must have timeouts and clean up subprocesses.
