import asyncio
import pytest
from app.services.generation_progress import publish, subscribe, _queues


@pytest.mark.asyncio
async def test_publish_creates_queue_and_delivers_event():
    token = "test-token-1"
    event = {"step": "historian", "status": "started", "label": "Analysing history"}

    # Subscribe first (creates the queue)
    gen = subscribe(token)

    # Publish
    await publish(token, event)
    await publish(token, {"step": "done"})

    received = await gen.__anext__()
    assert received == event

    done_event = await gen.__anext__()
    assert done_event["step"] == "done"

    # Queue cleaned up after done
    assert token not in _queues


@pytest.mark.asyncio
async def test_publish_before_subscribe_does_not_raise():
    """publish() before subscribe() should not raise — queue is created on publish."""
    token = "test-token-2"
    # No subscribe yet — should not raise
    await publish(token, {"step": "historian", "status": "started", "label": "test"})
    assert token in _queues
    # Clean up
    _queues.pop(token, None)


@pytest.mark.asyncio
async def test_subscribe_receives_event_published_concurrently():
    token = "test-token-3"

    async def producer():
        await asyncio.sleep(0.01)
        await publish(token, {"step": "historian", "status": "started", "label": "test"})
        await publish(token, {"step": "done"})

    asyncio.create_task(producer())
    events = []
    async for event in subscribe(token):
        events.append(event)

    assert len(events) == 2
    assert events[-1]["step"] == "done"
