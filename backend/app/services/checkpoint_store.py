from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
import json


class CheckpointStore:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self._lock = Lock()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def append(self, job_id: str, event: str, payload: dict[str, Any], state: dict[str, Any] | None = None) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "job_id": job_id,
            "event": event,
            "payload": payload,
            "state": state or {},
        }
        path = self.base_dir / f"{job_id}.jsonl"
        with self._lock:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, default=str) + "\n")

    def read(self, job_id: str) -> list[dict[str, Any]]:
        path = self.base_dir / f"{job_id}.jsonl"
        if not path.exists():
            return []
        records: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                records.append(json.loads(line))
        return records


checkpoint_store = CheckpointStore(Path("backend/generated_projects/checkpoints"))
