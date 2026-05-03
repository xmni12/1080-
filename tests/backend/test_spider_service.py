import pytest
import os
import shutil
from backend.services.task_manager import task_manager

@pytest.mark.asyncio
async def test_task_manager_has_run_discuz_spider():
    """
    验证 TaskManager 是否具备 run_discuz_spider 方法
    """
    assert hasattr(task_manager, "run_discuz_spider")
    assert callable(getattr(task_manager, "run_discuz_spider"))

@pytest.mark.asyncio
async def test_run_discuz_spider_execution():
    """
    验证 run_discuz_spider 能够成功运行（使用 Mock 浏览器）
    """
    test_save_path = "./test_downloads_temp"
    config = {
        "url": "http://example.com/forum.php?mod=forumdisplay&fid=2",
        "daily_limit": 1,
        "start_page": 1,
        "save_path": test_save_path,
        "simulate_human": False
    }
    
    # 确保测试目录干净
    if os.path.exists(test_save_path):
        shutil.rmtree(test_save_path)
        
    try:
        # 运行爬虫，因为使用的是 MockPage 且 eles 返回空，它应该很快结束（"无新番号"）
        await task_manager.run_discuz_spider("test_section", config)
        # 如果没有抛出异常，说明逻辑链路是通的
    finally:
        # 清理测试目录
        if os.path.exists(test_save_path):
            shutil.rmtree(test_save_path)
