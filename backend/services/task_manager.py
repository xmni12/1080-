import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaskManager:
    async def run_spider_mock(self, section: str):
        """
        模拟爬虫任务执行
        """
        logger.info(f"Starting spider task for section: {section}")
        # 模拟爬取耗时
        await asyncio.sleep(5)
        logger.info(f"Finished spider task for section: {section}")

# 实例化全局任务管理器
task_manager = TaskManager()
