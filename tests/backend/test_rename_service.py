import pytest
from httpx import AsyncClient
from backend.main import app

@pytest.mark.asyncio
async def test_trigger_rename_task():
    """
    测试触发重命名任务接口
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        payload = {
            "files": ["SSIS-123.mp4", "EBOD-456.mkv"],
            "rules": ["\\[1080P\\]"],
            "threads": 2
        }
        response = await ac.post("/api/tasks/rename", json=payload)
    
    assert response.status_code == 200
    assert response.json() == {"status": "started"}

@pytest.mark.asyncio
async def test_rename_schema_validation():
    """
    测试重命名接口的参数验证
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # 缺失 files 字段
        payload = {
            "rules": [],
            "threads": 3
        }
        response = await ac.post("/api/tasks/rename", json=payload)
        assert response.status_code == 422
