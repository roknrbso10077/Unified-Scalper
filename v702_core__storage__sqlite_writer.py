"""One process-wide SQLite writer lock for the shared V702 runtime database.

SQLite busy_timeout remains a last-resort cross-process safeguard; this RLock
serializes the in-process ledger, portfolio guard, and shadow writers before
SQLite can block an asyncio worker on its 5-second busy timeout.
"""
from __future__ import annotations

import threading

SQLITE_WRITER_LOCK = threading.RLock()
