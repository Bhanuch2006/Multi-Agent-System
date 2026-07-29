from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import uuid4


@dataclass
class JobRecord:
    job_id: str
    prompt: str
    status: str = "queued"
    current_agent: str = "Supervisor"
    progress: int = 0
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class JobStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._jobs: dict[str, JobRecord] = {}

    def create(self, prompt: str) -> JobRecord:
        record = JobRecord(job_id=str(uuid4()), prompt=prompt)
        with self._lock:
            self._jobs[record.job_id] = record
        return record

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **fields: Any) -> JobRecord:
        with self._lock:
            record = self._jobs[job_id]
            for key, value in fields.items():
                setattr(record, key, value)
            record.updated_at = datetime.now(timezone.utc).isoformat()
            return record

    def complete(self, job_id: str, result: dict[str, Any]) -> JobRecord:
        return self.update(job_id, status="completed", current_agent="Documentation", progress=100, result=result, error=None)

    def fail(self, job_id: str, error: str) -> JobRecord:
        return self.update(job_id, status="failed", error=error)


job_store = JobStore()