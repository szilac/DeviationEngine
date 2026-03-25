import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services import generation_progress


@pytest.mark.asyncio
async def test_sse_streams_events_and_closes_on_done():
    token = "sse-test-token"

    async def publish_events():
        await asyncio.sleep(0.05)
        await generation_progress.publish(token, {"step": "historian", "status": "started", "label": "test"})
        await generation_progress.publish(token, {"step": "done"})

    asyncio.create_task(publish_events())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        lines = []
        async with client.stream("GET", f"/api/timelines/progress/{token}") as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    lines.append(line)
                if "done" in line:
                    break

    assert any("historian" in l for l in lines)
    assert any("done" in l for l in lines)
