"""Transaktions-Ticker: Ereignisse im Speicher sammeln und per SSE an Browser verteilen.

Bewusst ohne account_id oder u – der Ticker ist öffentlich auf der Startseite.
"""

import asyncio
import itertools
import json
import threading
from collections import deque
from collections.abc import AsyncIterator
from datetime import UTC, datetime

RECENT_LIMIT = 30  # so viele bekommt ein neuer Browser sofort
KEEPALIVE_SECONDS = 15  # hält Proxys wie ngrok davon ab, die Verbindung zu kappen


class EventBus:
    def __init__(self) -> None:
        self._recent: deque[dict] = deque(maxlen=RECENT_LIMIT)
        self._subscribers: set[asyncio.Queue] = set()
        self._ids = itertools.count(1)
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Beim Start aufrufen – sync-Endpoints laufen in Threads und brauchen den Loop."""
        self._loop = loop

    def publish(self, kind: str, **data) -> None:
        """Thread-sicher, darf aus normalen (sync) Endpoints aufgerufen werden."""
        with self._lock:
            event = {
                "id": next(self._ids),
                "time": datetime.now(UTC).isoformat(),
                "kind": kind,
                **data,
            }
            self._recent.append(event)
            subscribers = list(self._subscribers)
        if self._loop is None:
            return
        for queue in subscribers:
            self._loop.call_soon_threadsafe(queue.put_nowait, event)

    async def stream(self) -> AsyncIterator[str]:
        """SSE-Datenstrom: erst die jüngsten Ereignisse, dann live."""
        queue: asyncio.Queue = asyncio.Queue()
        with self._lock:
            self._subscribers.add(queue)
            backlog = list(self._recent)
        try:
            yield "retry: 3000\n\n"
            for event in backlog:
                yield _sse({**event, "replay": True})  # Rückblick, nicht neu
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), KEEPALIVE_SECONDS)
                except TimeoutError:
                    yield ": ping\n\n"
                    continue
                yield _sse(event)
        finally:
            with self._lock:
                self._subscribers.discard(queue)


def _sse(event: dict) -> str:
    return f"id: {event['id']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"


bus = EventBus()
