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
        self.task_queue = asyncio.Queue()
        self.worker_task = None
        self.queued_sections = set()

    async def start_worker(self):
        if self.worker_task is None:
            self.worker_task = asyncio.create_task(self._queue_worker())

    async def _queue_worker(self):
        while True:
            task_item = await self.task_queue.get()
            section_key = None
            try:
                if isinstance(task_item, tuple):
                    section_key, mode = task_item
                else:
                    section_key = task_item
                    mode = "new"
                await self._execute_discuz_spider(section_key, mode)
            except Exception as e:
                logger.error(f"Worker execution error: {e}")
            finally:
                if section_key and section_key in self.queued_sections:
                    self.queued_sections.remove(section_key)
                self.task_queue.task_done()

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

    async def run_discuz_spider(self, section_key: str, mode: str = "new"):
        """
        将爬虫任务加入队列
        """
        if section_key in self.queued_sections or section_key in self.active_spiders:
            await manager.broadcast_json({"type": "log", "message": f"❌ [{section_key}] 任务已在队列或运行中，请勿重复投递。", "level": "error"})
            return
            
        self.queued_sections.add(section_key)
        await self.task_queue.put((section_key, mode))
        
        queue_pos = self.task_queue.qsize()
        if queue_pos == 1 and not self.active_spiders:
            pass # It will start immediately, no need to say queueing
        else:
            mode_name = "极速追新" if mode == "new" else "深度考古"
            msg = f"📝 [{section_key}] ({mode_name}) 任务已加入等待队列 (当前排在第 {queue_pos} 位)..."
            await manager.broadcast_json({"type": "log", "message": msg, "level": "info"})

    async def _execute_discuz_spider(self, section_key: str, mode: str):
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
                '4k': 'https://x999x.me/forum.php?mod=forumdisplay&fid=202',
                'vr': 'https://x999x.me/forum.php?mod=forumdisplay&fid=163',
                'hd': 'https://x999x.me/forum.php?mod=forumdisplay&fid=75',
                'sub': 'https://x999x.me/forum.php?mod=forumdisplay&fid=185'
            }
            section_config['url'] = default_urls.get(section_key, '')

        co = ChromiumOptions().set_local_port(9222)
        # 持久化用户数据，完美对抗 CF 盾
        profile_path = os.path.abspath('data/browser_profile')
        co.set_user_data_path(profile_path)
        
        if hide_browser: 
            ws_log("已开启无头静默模式运行 (采用伪装模式防指纹泄露)。")
            # 不使用 co.headless() 防止指纹发生变化，改将窗口移出屏幕外
            co.set_argument('--window-position=-32000,-32000')
            
        try:
            page = ChromiumPage(addr_or_opts=co)
            if hide_browser:
                # 进一步将窗口彻底隐藏 (从任务栏蒸发)
                try: page.set.window.hide()
                except: pass
            
            self.active_pages[section_key] = page
            ws_log("✅ DrissionPage 浏览器内核启动成功 (已加载绿卡持久化环境)。")
        except Exception as e:
            ws_log(f"❌ 浏览器启动失败: {e}")
            return
            
        try:
            async with AsyncSessionLocal() as session:
                spider = DiscuzSpiderService(page=page, log_callback=ws_log)
                self.active_spiders[section_key] = spider
                await spider.run_task(session, section_config, section_key, mode)
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

        ws_log("▶ 开始初始化独立的绿卡获取任务 (强制有头模式)...")
        co = ChromiumOptions().set_local_port(9222)
        profile_path = os.path.abspath('data/browser_profile')
        co.set_user_data_path(profile_path)
        
        try:
            page = ChromiumPage(addr_or_opts=co)
            self.active_pages['cf_clearance'] = page
            ws_log("✅ 浏览器已打开，正在尝试访问论坛...")
            
            page.get("https://x999x.me/")
            
            # 延长监听至 120 秒，并且增加强制延迟，让人眼能看到主页
            passed = False
            for i in range(120):
                await asyncio.sleep(1)
                if not getattr(self, 'active_pages', {}).get('cf_clearance'):
                    break
                    
                title = page.title or ""
                html = page.html or ""
                
                # 如果遇到 5秒盾，等待
                if "Just a moment" in title or "Cloudflare" in title or "cf-turnstile" in html:
                    if i % 5 == 0: ws_log("⏳ 仍在等待通过 CF 盾，如果出现验证码请手动勾选...")
                    continue
                    
                # 只有真正看到论坛的特征元素（如头部导航栏、板块列表）才算成功
                if "forum-" in html or "portal.php" in html or "forum.php" in html or "首页" in title:
                    passed = True
                    break
                    
            if passed:
                ws_log("✅ 恭喜！成功突破 CF 盾，已真实进入论坛首页。")
                ws_log("👀 为确保 Cookie 稳固写入硬盘，浏览器将保持开启 5 秒钟...")
                await asyncio.sleep(5)
                ws_log("💡 绿卡已安全保存。你现在可以去【系统设置】开启无头模式愉快地爬取了！")
            else:
                ws_log("⚠️ 120 秒内未成功进入主页，绿卡获取失败。请检查网络或重试。")
                
        except Exception as e:
            ws_log(f"❌ 浏览器启动或访问异常: {e}")
        finally:
            if 'cf_clearance' in self.active_pages:
                del self.active_pages['cf_clearance']
            try:
                page.quit()
                ws_log("⏹ 绿卡获取任务结束，浏览器已自动关闭。")
            except:
                pass

    async def login_authorize(self):
        """
        独立打开浏览器，无限等待用户手动完成登录与授权，直到用户关闭窗口
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

        if 'login_auth' in self.active_pages:
            ws_log("❌ 授权登录窗口已经在运行中，请不要重复打开。")
            return

        ws_log("▶ 开始初始化独立的账号登录授权通道 (强制有头模式)...")
        co = ChromiumOptions().set_local_port(9222)
        profile_path = os.path.abspath('data/browser_profile')
        co.set_user_data_path(profile_path)
        
        try:
            page = ChromiumPage(addr_or_opts=co)
            self.active_pages['login_auth'] = page
            ws_log("✅ 浏览器已成功打开，正前往论坛首页。")
            page.get("https://x999x.me/")
            
            ws_log("⏳ 请在弹出的浏览器中慢慢操作：1.通过 CF 验证(如有)；2.输入账号密码登录；3.勾选【自动登录/记住密码】。")
            ws_log("💡 操作全部完成后，请【手动点击右上角 X 关闭浏览器窗口】，系统会自动保存你的授权状态。")
            
            # 无限循环检测浏览器是否被用户手动关闭
            while True:
                await asyncio.sleep(2)
                if not getattr(self, 'active_pages', {}).get('login_auth'):
                    break # 任务被后端提前中止
                try:
                    # 尝试获取页面标题，如果抛出异常说明窗口已经被关闭
                    _ = page.title
                except Exception:
                    ws_log("✅ 检测到授权浏览器窗口已关闭。所有的 Cookie 和登录状态已安全落盘并持久化！")
                    break
                
        except Exception as e:
            ws_log(f"❌ 浏览器启动或访问异常: {e}")
        finally:
            if 'login_auth' in self.active_pages:
                del self.active_pages['login_auth']
            try:
                page.quit()
                ws_log("⏹ 账号授权登录任务彻底结束。")
            except:
                pass

task_manager = TaskManager()
