import asyncio
import logging
import os
from backend.database import AsyncSessionLocal
from backend.services.spider_service import DiscuzSpiderService
from backend.routers.websocket import manager
from DrissionPage import ChromiumPage, ChromiumOptions
from core.utils import load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaskManager:
    def __init__(self):
        self.active_spiders: dict[str, DiscuzSpiderService] = {}
        self.active_pages: dict[str, ChromiumPage] = {}

    def stop_spider(self, section_key: str = None):
        """
        强制停止指定或所有版块的爬虫
        """
        if section_key and section_key in self.active_spiders:
            self.active_spiders[section_key].stop_requested = True
            logger.info(f"Requested stop for spider: {section_key}")
            return {"status": "stopping", "section": section_key}
        elif not section_key:
            for key, spider in self.active_spiders.items():
                spider.stop_requested = True
                logger.info(f"Requested stop for spider: {key}")
            return {"status": "stopping_all"}
        return {"status": "not_running"}

    async def run_spider_mock(self, section: str):
        """
        模拟爬虫任务执行
        """
        log_msg = f"Starting spider task for section: {section}"
        logger.info(log_msg)
        await manager.broadcast_json({"type": "log", "message": log_msg, "level": "info"})
        
        await asyncio.sleep(5)
        
        log_msg = f"Finished spider task for section: {section}"
        logger.info(log_msg)
        await manager.broadcast_json({"type": "log", "message": log_msg, "level": "success"})

    async def run_discuz_spider(self, section_key: str):
        """
        运行真实的 Discuz 爬虫任务
        """
        if section_key in self.active_spiders:
            await manager.broadcast_json({"type": "log", "message": f"❌ [{section_key}] 爬虫任务已在运行中，请勿重复启动。", "level": "error"})
            return

        def ws_log(msg: str):
            logger.info(msg)
            try:
                # 异步触发 WebSocket 推送，不阻塞同步的爬虫逻辑
                loop = asyncio.get_running_loop()
                level = "info"
                if "错误" in msg or "异常" in msg or "失败" in msg: level = "error"
                elif "结束" in msg or "完成" in msg or "成功" in msg: level = "success"
                elif "避让" in msg or "跳过" in msg: level = "warn"
                
                loop.create_task(manager.broadcast_json({"type": "log", "message": msg, "level": level}))
            except Exception as e:
                logger.error(f"WebSocket broadcast error: {e}")

        ws_log(f"▶ 开始初始化 [{section_key}] 版块爬虫任务...")
        
        config = load_config()
        section_config = config.get("sections", {}).get(section_key, {})
        if not section_config: section_config = config.get(section_key, {}) # 兼容旧版配置结构
        hide_browser = config.get("hide_browser", False)
        
        if not section_config.get("url"):
            default_urls = {
                '4k': 'https://www.hhd800.com/forum-65-1.html',
                'vr': 'https://www.hhd800.com/forum-80-1.html',
                'hd': 'https://www.hhd800.com/forum-58-1.html',
                'sub': 'https://www.hhd800.com/forum-60-1.html'
            }
            section_config['url'] = default_urls.get(section_key, '')

        co = ChromiumOptions().set_local_port(9222)
        # 持久化用户数据，完美对抗 CF 盾
        profile_path = os.path.abspath('data/browser_profile')
        co.set_user_data_path(profile_path)
        
        if hide_browser: 
            ws_log("已开启无头静默模式运行。")
            co.headless()
            
        try:
            page = ChromiumPage(addr_or_opts=co)
            self.active_pages[section_key] = page
            ws_log("✅ DrissionPage 浏览器内核启动成功 (已加载绿卡持久化环境)。")
        except Exception as e:
            ws_log(f"❌ 浏览器启动失败: {e}")
            return
            
        try:
            async with AsyncSessionLocal() as session:
                spider = DiscuzSpiderService(page=page, log_callback=ws_log)
                self.active_spiders[section_key] = spider
                await spider.run_task(session, section_config, section_key)
        except Exception as e:
            ws_log(f"❌ 爬虫执行出现致命异常: {str(e)}")
        finally:
            if section_key in self.active_spiders:
                del self.active_spiders[section_key]
            if section_key in self.active_pages:
                del self.active_pages[section_key]
            try:
                page.quit()
            except:
                pass
            ws_log(f"⏹ [{section_key}] 爬虫任务已安全结束，浏览器资源已释放。")

task_manager = TaskManager()
