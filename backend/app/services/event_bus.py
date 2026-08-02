from __future__ import annotations

from typing import Callable, Dict, List, Any
from threading import Lock


class EventBus:
    """Simple in-memory pub/sub event bus with synchronous delivery."""

    def __init__(self) -> None:
        self._subs: Dict[str, List[Callable[[dict], None]]] = {}
        self._lock = Lock()

    def subscribe(self, event_name: str, handler: Callable[[dict], None]) -> None:
        with self._lock:
            self._subs.setdefault(event_name, []).append(handler)

    def publish(self, event_name: str, payload: dict[str, Any]) -> None:
        # deliver to exact event subscribers and to wildcards like 'review.*' via simple matching
        handlers: List[Callable[[dict], None]] = []
        with self._lock:
            handlers.extend(self._subs.get(event_name, []))
            # simple prefix wildcard support
            for key, subs in self._subs.items():
                if key.endswith(".*") and event_name.startswith(key[:-2]):
                    handlers.extend(subs)

        event = {"event": event_name, "payload": payload}
        for h in handlers:
            try:
                h(event)
            except Exception:
                # subscribers should be resilient; ignore errors here
                pass


# global default bus instance
bus = EventBus()
