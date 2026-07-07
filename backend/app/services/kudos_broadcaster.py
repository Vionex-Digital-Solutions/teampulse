"""In-memory pub/sub broadcaster for the live kudos feed.

Fan-out is simple: every connected SSE client gets its own ``asyncio.Queue``.
``publish()`` drops one event onto every subscriber's queue; each streaming
endpoint drains its own queue and forwards events to that client.

Limitation (worth knowing): this state lives *inside a single process*. With
multiple Uvicorn workers, a kudos created on worker A would not reach a client
connected to worker B. A production deploy would swap this for a shared broker
(Postgres ``LISTEN``/``NOTIFY``, Redis pub/sub, etc.). For single-process dev
this is enough — and the ``subscribe``/``publish`` interface stays the same if
we swap the backend later.
"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager


class KudosBroadcaster:
    """Fan out kudos events to every connected SSE subscriber."""

    def __init__(self) -> None:
        # One queue per connected client. A set so subscribe/unsubscribe is O(1)
        # and we never deliver the same event to a client twice.
        self._subscribers: set[asyncio.Queue[str]] = set()

    @asynccontextmanager
    async def subscribe(self) -> AsyncGenerator[asyncio.Queue[str], None]:
        """Register a new subscriber and yield its queue.

        Used as ``async with broadcaster.subscribe() as queue:`` so the queue is
        always removed when the client disconnects — even if the connection
        drops mid-stream and the generator is torn down.
        """
        queue: asyncio.Queue[str] = asyncio.Queue()
        self._subscribers.add(queue)
        try:
            yield queue
        finally:
            self._subscribers.discard(queue)

    def publish(self, data: str) -> None:
        """Push one already-serialized event to every subscriber.

        ``put_nowait`` never blocks (the queues are unbounded), so a slow client
        can't stall the caller that created the kudos.
        """
        for queue in self._subscribers:
            queue.put_nowait(data)


# Process-wide singleton. Import this everywhere; do not construct your own.
broadcaster = KudosBroadcaster()
