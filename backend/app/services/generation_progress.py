"""
In-memory SSE progress event queue for timeline generation.

Maps progress_token → asyncio.Queue. The backend publishes step events
as generation proceeds; the SSE endpoint drains the queue and streams
to the frontend.
"""

import asyncio
import logging
from typing import AsyncIterator, Optional

logger = logging.getLogger(__name__)

# Module-level registry: token -> Queue
_queues: dict[str, asyncio.Queue] = {}


async def publish(token: Optional[str], event: dict) -> None:
    """Publish a progress event for the given token. No-op if token is None."""
    if not token:
        return
    if token not in _queues:
        _queues[token] = asyncio.Queue()
    await _queues[token].put(event)


async def subscribe(token: str) -> AsyncIterator[dict]:
    """
    Yield progress events for the given token until a 'done' event is received.
    Creates the queue if it does not exist yet (handles subscribe-before-publish).
    Cleans up the queue after the done event is consumed.
    """
    if token not in _queues:
        _queues[token] = asyncio.Queue()
    queue = _queues[token]
    try:
        while True:
            event = await queue.get()
            if event.get("step") == "done":
                _queues.pop(token, None)
                yield event
                break
            yield event
    finally:
        _queues.pop(token, None)
