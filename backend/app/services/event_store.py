from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, List
import json


class EventStore:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self._lock = Lock()
        self._events: dict[str, List[dict[str, Any]]] = {}
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def append(self, job_id: str, event: dict[str, Any]) -> None:
        with self._lock:
            self._events.setdefault(job_id, []).append(event)
            # append to a file for durability
            log_file = self.base_dir / f"{job_id}.events.jsonl"
            with log_file.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(), **event}, default=str) + "\n")

    def get(self, job_id: str) -> List[dict[str, Any]]:
        with self._lock:
            return list(self._events.get(job_id, []))


# default store
store = EventStore(Path("backend/generated_projects/events"))
