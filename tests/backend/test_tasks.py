import pytest
from httpx import AsyncClient
from backend.main import app

@pytest.mark.asyncio
async def test_trigger_spider_task():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/tasks/spider", json={"section": "4k"})
    
    assert response.status_code == 200
    assert response.json() == {"status": "started", "section": "4k"}
