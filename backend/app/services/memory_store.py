from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
import json


@dataclass
class MemoryEntry:
    created_at: str
    prompt: str
    lessons: list[str] = field(default_factory=list)
    preferences: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    successes: list[str] = field(default_factory=list)


class MemoryStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save(self, entries: list[dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(entries, indent=2), encoding="utf-8")

    def remember(self, prompt: str, lessons: list[str], preferences: list[str] | None = None, failures: list[str] | None = None, successes: list[str] | None = None) -> None:
        entry = MemoryEntry(
            created_at=datetime.now(timezone.utc).isoformat(),
            prompt=prompt,
            lessons=lessons,
            preferences=preferences or [],
            failures=failures or [],
            successes=successes or [],
        )
        with self._lock:
            entries = self._load()
            entries.append(entry.__dict__)
            self._save(entries)

    def recall(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        query = query.lower()
        entries = self._load()
        ranked: list[dict[str, Any]] = []
        for entry in entries:
            blob = json.dumps(entry).lower()
            if query in blob:
                ranked.append(entry)
        return ranked[-limit:]


memory_store = MemoryStore(Path("backend/generated_projects/memory/memory.json"))
