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
                '4k': 'https://x999x.me/forum-65-1.html',
                'vr': 'https://x999x.me/forum-80-1.html',
                'hd': 'https://x999x.me/forum-58-1.html',
                'sub': 'https://x999x.me/forum-60-1.html'
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

    async def get_cf_clearance(self):
        """
        独立打开浏览器获取 CF 绿卡
        """
        def ws_log(msg: str):
            logger.info(msg)
            try:
                loop = asyncio.get_running_loop()
                level = "info"
                if "错误" in msg or "异常" in msg or "失败" in msg: level = "error"
                elif "结束" in msg or "完成" in msg or "成功" in msg: level = "success"
                loop.create_task(manager.broadcast_json({"type": "log", "message": msg, "level": level}))
            except: pass

        if 'cf_clearance' in self.active_pages:
            ws_log("❌ 获取绿卡任务已经在运行中。")
            return

        ws_log("▶ 开始初始化独立的绿卡获取任务 (有头模式)...")
        co = ChromiumOptions().set_local_port(9222)
        profile_path = os.path.abspath('data/browser_profile')
        co.set_user_data_path(profile_path)
        
        try:
            page = ChromiumPage(addr_or_opts=co)
            self.active_pages['cf_clearance'] = page
            ws_log("✅ 浏览器已打开，请在弹出的窗口中等待或手动点击 CF 验证码！")
            ws_log("⏳ 系统将自动监听过盾状态（最长等待 60 秒）...")
            
            page.get("https://x999x.me/")
            
            # 简单监听 60 秒，看看是否成功进入论坛首页
            passed = False
            for _ in range(60):
                await asyncio.sleep(1)
                if not getattr(self, 'active_pages', {}).get('cf_clearance'):
                    # 任务可能被提前中止
                    break
                title = page.title or ""
                if "Just a moment" not in title and "Cloudflare" not in title:
                    passed = True
                    break
                    
            if passed:
                ws_log("✅ 恭喜！成功检测到论坛首页，CF 绿卡已安全保存。")
                ws_log("💡 你现在可以关闭此窗口，去【系统设置】开启无头模式愉快地爬取了！")
            else:
                ws_log("⚠️ 60 秒内未检测到过盾成功，可能是网络慢或验证失败，请重试。")
                
        except Exception as e:
            ws_log(f"❌ 浏览器启动或访问异常: {e}")
        finally:
            if 'cf_clearance' in self.active_pages:
                del self.active_pages['cf_clearance']
            try:
                page.quit()
                ws_log("⏹ 绿卡获取任务结束，浏览器已关闭。")
            except:
                pass

task_manager = TaskManager()
