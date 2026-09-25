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
KEEPALIVE_SECONDS = 5  # hält Proxys wie ngrok davon ab, die Verbindung zu kappen
# Jede Verbindung endet nach dieser Zeit, der Browser verbindet sich sofort neu (Last-Event-ID, nichts geht
# verloren). Ohne das hinge uvicorn beim Reload/Stoppen ewig in „Waiting for connections to close“.
STREAM_SECONDS = 10
RECONNECT_MS = 1000


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

    async def stream(self, last_event_id: int | None = None) -> AsyncIterator[str]:
        """SSE-Datenstrom: erst die jüngsten Ereignisse, dann live – für höchstens STREAM_SECONDS.

        Neue Verbindung: Rückblick mit replay=True. Wiederverbindung (Last-Event-ID): alles Neuere
        kommt als live, damit zwischen zwei Verbindungen nichts verloren geht.
        """
        queue: asyncio.Queue = asyncio.Queue()
        with self._lock:
            self._subscribers.add(queue)
            backlog = list(self._recent)
        # Last-Event-ID größer als alles Bekannte: Server wurde neu gestartet, ids beginnen wieder bei 1
        if last_event_id is not None and backlog and last_event_id > backlog[-1]["id"]:
            last_event_id = None
        loop = asyncio.get_running_loop()
        deadline = loop.time() + STREAM_SECONDS
        try:
            yield f"retry: {RECONNECT_MS}\n\n"
            for event in backlog:
                if last_event_id is None:
                    yield _sse({**event, "replay": True})  # Rückblick, nicht neu
                elif event["id"] > last_event_id:
                    yield _sse(
                        event
                    )  # in der Lücke zwischen zwei Verbindungen passiert
            while (remaining := deadline - loop.time()) > 0:
                try:
                    event = await asyncio.wait_for(
                        queue.get(), min(KEEPALIVE_SECONDS, remaining)
                    )
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
