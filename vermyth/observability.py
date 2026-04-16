from __future__ import annotations

import json
import logging
import os
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from ulid import ULID


@dataclass(frozen=True)
class VermythEvent:
    event_id: str
    event_type: str
    ts: datetime
    payload: dict[str, Any]
    cast_id: str | None = None
    branch_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["ts"] = self.ts.isoformat()
        return out


@dataclass
class EventBus:
    max_events: int = 1000
    _events: deque[VermythEvent] = field(default_factory=lambda: deque(maxlen=1000))
    _subscribers: list[Callable[[VermythEvent], None]] = field(default_factory=list)

    def emit(self, event: VermythEvent) -> None:
        self._events.append(event)
        logging.getLogger("vermyth.events").info("%s %s", event.event_type, event.payload)
        sink = os.getenv("VERMYTH_EVENT_LOG")
        if sink:
            with open(sink, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(event.to_dict(), default=str) + "\n")
        for fn in list(self._subscribers):
            fn(event)

    def emit_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        cast_id: str | None = None,
        branch_id: str | None = None,
    ) -> VermythEvent:
        event = VermythEvent(
            event_id=str(ULID()),
            event_type=event_type,
            ts=datetime.now(timezone.utc),
            payload=payload,
            cast_id=cast_id,
            branch_id=branch_id,
        )
        self.emit(event)
        return event

    def subscribe(self, fn: Callable[[VermythEvent], None]) -> Callable[[], None]:
        self._subscribers.append(fn)

        def unsubscribe() -> None:
            if fn in self._subscribers:
                self._subscribers.remove(fn)

        return unsubscribe

    def recent(self, n: int = 100, *, event_type: str | None = None) -> list[VermythEvent]:
        items = list(self._events)
        if event_type is not None:
            items = [ev for ev in items if ev.event_type == event_type]
        return items[-int(n) :]
