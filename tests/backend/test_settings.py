import pytest
from httpx import AsyncClient
from backend.main import app
import os
import json
from core.utils import CONFIG_FILE

@pytest.mark.asyncio
async def test_settings_api():
    # 备份原有配置
    config_backup = None
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config_backup = f.read()

    async with AsyncClient(app=app, base_url="http://test") as ac:
        # 1. GET settings
        get_resp = await ac.get("/api/settings")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert "sections" in data
        assert "hide_browser" in data
        assert "rename_settings" in data

        # 2. POST settings
        # 构造测试数据
        test_data = {
            "sections": {
                "test_section": {
                    "start_page": "1",
                    "history_page": "1",
                    "save_path": "C:/test_path",
                    "timer_enabled": True,
                    "timer_time": "05:00",
                    "simulate_human": False,
                    "daily_limit": 50
                }
            },
            "hide_browser": True,
            "rename_settings": {
                "rules": "rule1",
                "threads": "5"
            }
        }

        post_resp = await ac.post("/api/settings", json=test_data)
        assert post_resp.status_code == 200
        assert post_resp.json()["status"] == "success"

        # 3. GET settings again to verify persistence
        verify_resp = await ac.get("/api/settings")
        assert verify_resp.status_code == 200
        new_data = verify_resp.json()
        
        assert "test_section" in new_data["sections"]
        assert new_data["sections"]["test_section"]["save_path"] == "C:/test_path"
        assert new_data["sections"]["test_section"]["daily_limit"] == 50
        assert new_data["hide_browser"] is True
        assert new_data["rename_settings"]["threads"] == "5"

    # 恢复原有配置
    if config_backup:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            f.write(config_backup)
    elif os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)
