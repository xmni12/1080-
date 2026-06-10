import asyncio
import logging
import os
import random
from datetime import datetime
from backend.database import AsyncSessionLocal
from backend.services.spider_service import DiscuzSpiderService
from backend.routers.websocket import manager, sniper_manager
from DrissionPage import ChromiumPage, ChromiumOptions
from core.utils import load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import time

class TaskManager:
    def __init__(self):
        self.active_spiders: dict[str, DiscuzSpiderService] = {}
        self.active_pages: dict[str, ChromiumPage] = {}
        self._queue_list = []
        self._queue_lock = asyncio.Lock()
        self._queue_event = asyncio.Event()
        self.worker_task = None
        self.stop_lab_requested = False
        self.current_running_task = None
    def _get_chromium_options(self, config: dict, port: int = 9222):
        from DrissionPage import ChromiumOptions
        co = ChromiumOptions().set_local_port(port)
        
        browser_path = config.get("browser_path", "").strip()
        if browser_path.lower() == "edge":
            browser_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        elif browser_path.lower() == "chrome":
            browser_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            
        if browser_path:
            co.set_browser_path(browser_path)
            
        profile_path = os.path.abspath('data/browser_profile')
        co.set_user_data_path(profile_path)
        
        if config.get("hide_browser", False):
            co.set_argument('--window-position=-32000,-32000')
            
        return co


    async def start_worker(self):
        if self.worker_task is None:
            self.worker_task = asyncio.create_task(self._queue_worker())

    async def _queue_worker(self):
        while True:
            await self._queue_event.wait()
            
            task_item = None
            async with self._queue_lock:
                if not self._queue_list:
                    self._queue_event.clear()
                    continue
                    
                # Sort: is_vip DESC (True first), then timestamp ASC
                self._queue_list.sort(key=lambda x: (not x['is_vip'], x['timestamp']))
                task_item = self._queue_list.pop(0)
                
                if not self._queue_list:
                    self._queue_event.clear()
                    
            if not task_item:
                continue
                
            section_key = task_item['section_key']
            mode = task_item['mode']
            self.current_running_task = section_key
            
            # Broadcast queue update right after popping
            
            try:
                await self._execute_discuz_spider(section_key, mode)
            except Exception as e:
                logger.error(f"Worker execution error: {e}")
            finally:
                self.current_running_task = None
    def _get_chromium_options(self, config: dict, port: int = 9222):
        from DrissionPage import ChromiumOptions
        co = ChromiumOptions().set_local_port(port)
        
        browser_path = config.get("browser_path", "").strip()
        if browser_path.lower() == "edge":
            browser_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        elif browser_path.lower() == "chrome":
            browser_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            
        if browser_path:
            co.set_browser_path(browser_path)
            
        profile_path = os.path.abspath('data/browser_profile')
        co.set_user_data_path(profile_path)
        
        if config.get("hide_browser", False):
            co.set_argument('--window-position=-32000,-32000')
            
        return co

                

    async def broadcast_queue_status(self):
        status = await self.get_queue_status()
        await manager.broadcast_json({"type": "queue_update", "data": status})

    async def get_queue_status(self):
        async with self._queue_lock:
            queued = list(self._queue_list)
        
        running = []
        if self.current_running_task:
            running.append({"section_key": self.current_running_task})
            
        for sec in self.active_spiders.keys():
            if not any(r["section_key"] == sec for r in running):
                running.append({"section_key": sec})
            
        return {"running": running, "queued": queued}

    async def remove_queued_task(self, section_key: str, mode: str):
        async with self._queue_lock:
            original_len = len(self._queue_list)
            self._queue_list = [t for t in self._queue_list if not (t['section_key'] == section_key and t['mode'] == mode)]
            removed = original_len > len(self._queue_list)
            
        if removed:
            await self.broadcast_queue_status()
        return removed

    async def sniper_search(self, code: str) -> list[dict]:
        """
        为精准狙击中心实时爬取论坛搜索结果
        """
        import urllib.parse
        from DrissionPage import ChromiumOptions, ChromiumPage
        from core.utils import load_config
        
        config = load_config()
        co = self._get_chromium_options(config)
        
        page = None
        tab = None
        results = []
        try:
            page = ChromiumPage(co)
            if config.get("hide_browser"):
                try: page.set.window.hide()
                except: pass
            tab = page.new_tab()
            
            # 预热并等待过盾 (共用绿卡，通常秒过)
            tab.get("https://x999x.me/")
            for _ in range(15):
                await asyncio.sleep(0.5)
                html = tab.html or ""
                title = tab.title or ""
                if "forum-" in html or "portal.php" in html or "forum.php" in html or "首页" in title:
                    break
                    
            # 发起搜索
            search_url = f"https://x999x.me/search.php?mod=forum&srchtxt={urllib.parse.quote(code)}&searchsubmit=yes"
            tab.get(search_url)
            
            # 增加充分的等待时间，防止被 CF 拦截在请稍候
            for _ in range(20):
                await asyncio.sleep(1)
                title = tab.title or ""
                html = tab.html or ""
                if "Just a moment" not in title and "Cloudflare" not in title and "cf-turnstile" not in html:
                    if tab.ele('.pb', timeout=0) or tab.ele('.xs3', timeout=0) or "没有找到匹配结果" in html:
                        break
                        
            # 解析搜索结果
            html = tab.html or ""
            logger.info(f"Sniper search page title: {tab.title}")
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # 尝试在列表中查找
            items = soup.select('.pb')
            if not items:
                # 兼容不同版式的搜索结果
                items = soup.select('li.pbw')
                
            for item in items:
                try:
                    title_a = item.select_one('h3.xs3 a') or item.select_one('.xs3 a')
                    if not title_a: continue
                    
                    title_text = title_a.text.strip()
                    href = title_a.get('href', '')
                    if not href: continue
                    
                    forum_a = item.select_one('a.xi1')
                    forum_name = forum_a.text.strip() if forum_a else "未知版块"
                    
                    spans = item.select('p > span')
                    post_date = spans[0].text.strip() if spans else ""
                    
                    # --- 核心降噪漏斗：严格剔除不需要的版块 ---
                    forum_text = forum_name.upper()
                    title_text_upper = title_text.upper()
                    
                    # 绝对屏蔽 VR 和 字幕版
                    if "VR" in forum_text or "VR" in title_text_upper: continue
                    if "字幕" in forum_text or "字" in forum_text: continue
                    
                    # 仅保留 4K 或 HD (高清有碼)
                    is_valid_section = False
                    if "4K" in forum_text or "4K" in title_text_upper:
                        is_valid_section = True
                    elif "高清" in forum_text or "有碼" in forum_text or "HD" in title_text_upper:
                        is_valid_section = True
                        
                    if not is_valid_section:
                        continue
                    
                    # 粗略判断大小
                    size_text = ""
                    import re
                    size_match = re.search(r'([0-9\.]+)\s*(GB|MB)', title_text, re.IGNORECASE)
                    if size_match:
                        size_text = f"{size_match.group(1)} {size_match.group(2).upper()}"
                        
                    results.append({
                        "title": title_text,
                        "href": href,
                        "forum": forum_name,
                        "date": post_date,
                        "size": size_text
                    })
                except Exception as e:
                    logger.error(f"Error parsing sniper search result: {e}")
                    pass
                    
            return results
            
        except Exception as e:
            logger.error(f"Sniper search failed: {e}")
            return []
        finally:
            if page:
                try:
                    page.quit()
                except: pass

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
            self.stop_lab_requested = True
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

    async def run_discuz_spider(self, section_key: str, mode: str = "new", is_vip: bool = True):
        """
        将爬虫任务加入队列
        """
        async with self._queue_lock:
            # Check if already in queue
            for t in self._queue_list:
                if t['section_key'] == section_key and t['mode'] == mode:
                    await manager.broadcast_json({"type": "log", "message": f"❌ [{section_key}] 同模式任务已在队列中，请勿重复投递。", "level": "error"})
                    return
                    
        if section_key in self.active_spiders:
             await manager.broadcast_json({"type": "log", "message": f"❌ [{section_key}] 任务正在运行中，请勿重复投递。", "level": "error"})
             return
             
        new_task = {
            "section_key": section_key,
            "mode": mode,
            "is_vip": is_vip,
            "timestamp": time.time()
        }
        
        async with self._queue_lock:
            self._queue_list.append(new_task)
            self._queue_list.sort(key=lambda x: (not x['is_vip'], x['timestamp']))
            queue_pos = self._queue_list.index(new_task) + 1
            self._queue_event.set()
        
        await self.broadcast_queue_status()
        
        if queue_pos == 1 and not self.active_spiders:
            pass # It will start immediately, no need to say queueing
        else:
            mode_name = "极速追新" if mode == "new" else "深度考古"
            vip_mark = "⭐VIP " if is_vip else ""
            msg = f"📝 [{section_key}] ({mode_name}) {vip_mark}任务已加入等待队列 (当前排在第 {queue_pos} 位)..."
            await manager.broadcast_json({"type": "log", "message": msg, "level": "info"})

    async def _execute_discuz_spider(self, section_key: str, mode: str):
        """
        运行真实的 Discuz 爬虫任务
        """
        if section_key in self.active_spiders:
            await manager.broadcast_json({"type": "log", "message": f"❌ [{section_key}] 爬虫任务已在运行中，请勿重复启动。", "level": "error"})
            return

        def ws_log(msg: str, explicit_level: str = None):
            logger.info(msg)
            try:
                # 异步触发 WebSocket 推送，不阻塞同步的爬虫逻辑
                loop = asyncio.get_running_loop()
                
                level = explicit_level if explicit_level else "info"
                
                # 如果传入的是默认的 info，但信息里包含敏感词，则强行升级日志级别
                if level == "info":
                    if "错误" in msg or "异常" in msg or "失败" in msg: level = "error"
                    elif "避让" in msg or "跳过" in msg or "拦截" in msg: level = "warn"
                    elif "结束" in msg or "完成" in msg or "成功" in msg: level = "success"
                
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
        browser_path = config.get("browser_path", "").strip()
        if browser_path.lower() == "edge":
            browser_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        elif browser_path.lower() == "chrome":
            browser_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            
        if browser_path:
            co.set_browser_path(browser_path)
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

        ws_log("▶ 开始初始化独立的账号登录授权通道 (强制有头模式)...")
        config = load_config()
        co = ChromiumOptions().set_local_port(9222)
        browser_path = config.get("browser_path", "").strip()
        if browser_path.lower() == "edge":
            browser_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        elif browser_path.lower() == "chrome":
            browser_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            
        if browser_path:
            co.set_browser_path(browser_path)
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
        config = load_config()
        co = ChromiumOptions().set_local_port(9222)
        browser_path = config.get("browser_path", "").strip()
        if browser_path.lower() == "edge":
            browser_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        elif browser_path.lower() == "chrome":
            browser_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            
        if browser_path:
            co.set_browser_path(browser_path)
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
                    # 尝试获取标签页数量，如果抛出特定断开异常说明窗口已经被关闭
                    _ = page.tabs_count
                except Exception as e:
                    if type(e).__name__ in ['PageDisconnectedError', 'BrowserConnectError', 'ContextLostError']:
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

    async def sandbox_browser(self):
        """
        纯净沙盒模式：独立打开浏览器，仅前往主页，无限等待用户手动关闭，无任何强制操作和倒计时
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

        if 'sandbox' in self.active_pages:
            ws_log("❌ 自由沙盒浏览器已经在运行中，请不要重复打开。")
            return

        ws_log("▶ 开始初始化零干预自由沙盒浏览器 (强制有头模式)...")
        config = load_config()
        co = ChromiumOptions().set_local_port(9222)
        browser_path = config.get("browser_path", "").strip()
        if browser_path.lower() == "edge":
            browser_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        elif browser_path.lower() == "chrome":
            browser_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            
        if browser_path:
            co.set_browser_path(browser_path)
        profile_path = os.path.abspath('data/browser_profile')
        co.set_user_data_path(profile_path)
        
        try:
            page = ChromiumPage(addr_or_opts=co)
            self.active_pages['sandbox'] = page
            ws_log("✅ 浏览器已成功打开，正前往论坛首页。")
            page.get("https://x999x.me/")
            
            ws_log("💡 【沙盒模式】：你可以随心所欲地浏览、过盾或挂机。后台不会做任何干预。")
            ws_log("💡 结束漫游时，请【手动点击右上角 X 关闭浏览器窗口】，系统会自动保存指纹和绿卡。")
            
            # 无限循环检测浏览器是否被用户手动关闭
            while True:
                await asyncio.sleep(2)
                if not getattr(self, 'active_pages', {}).get('sandbox'):
                    break # 任务被后端提前中止
                try:
                    # 尝试获取标签页数量，如果抛出特定断开异常说明窗口已经被关闭
                    _ = page.tabs_count
                except Exception as e:
                    if type(e).__name__ in ['PageDisconnectedError', 'BrowserConnectError', 'ContextLostError']:
                        ws_log("✅ 漫游结束，产生的高质量指纹和绿卡已安全封存！")
                        break
                
        except Exception as e:
            ws_log(f"❌ 浏览器启动或访问异常: {e}")
        finally:
            if 'sandbox' in self.active_pages:
                del self.active_pages['sandbox']
            try:
                page.quit()
                ws_log("⏹ 沙盒漫游任务彻底结束。")
            except:
                pass

    async def run_retry_tasks(self, records: list[dict]):
        """
        死链精准抢救任务：直接跳转原帖进行重新下载
        """
        def ws_log(msg: str, explicit_level: str = None):
            logger.info(msg)
            try:
                loop = asyncio.get_running_loop()
                level = explicit_level if explicit_level else "info"
                if level == "info":
                    if "错误" in msg or "异常" in msg or "失败" in msg: level = "error"
                    elif "避让" in msg or "跳过" in msg or "拦截" in msg: level = "warn"
                    elif "结束" in msg or "完成" in msg or "成功" in msg: level = "success"
                loop.create_task(manager.broadcast_json({"type": "log", "message": msg, "level": level}))
            except: pass

        if 'retry' in self.active_pages:
            ws_log("❌ 死链抢救任务已经在运行中，请勿重复启动。", explicit_level="error")
            return

        ws_log(f"🚑 死链抢救特遣队出发！收到 {len(records)} 个抢救目标，准备执行定点爆破...")
        
        config = load_config()
        hide_browser = config.get("hide_browser", False)
        
        co = ChromiumOptions().set_local_port(9222)
        browser_path = config.get("browser_path", "").strip()
        if browser_path.lower() == "edge":
            browser_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        elif browser_path.lower() == "chrome":
            browser_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            
        if browser_path:
            co.set_browser_path(browser_path)
        profile_path = os.path.abspath('data/browser_profile')
        co.set_user_data_path(profile_path)
        
        if hide_browser: 
            ws_log("已开启无头静默模式运行。")
            co.set_argument('--window-position=-32000,-32000')
            
        try:
            page = ChromiumPage(addr_or_opts=co)
            if hide_browser:
                try: page.set.window.hide()
                except: pass
            
            self.active_pages['retry'] = page
            tab = page.new_tab()
            ws_log("✅ DrissionPage 浏览器内核启动成功。")
            
            # 必须先访问一次该域名的主页，才能把该域名的持久化 Cookie 注入到 page 实例中
            ws_log("⏳ 正在接驳底层物理下载引擎...")
            tab.get("https://x999x.me/")
            # 等待出现论坛特征，证明破盾成功 (最多等 15 秒)
            passed = False
            for _ in range(15):
                await asyncio.sleep(1)
                html = tab.html or ""
                title = tab.title or ""
                if "forum-" in html or "portal.php" in html or "forum.php" in html or "首页" in title:
                    passed = True
                    break
            
            if passed:
                ws_log("✅ 绿卡预热成功，Cookie 已热加载。")
            else:
                ws_log("⚠️ 绿卡预热超时，疑似遭到极其严厉的 CF 盾拦截，这可能导致接下来的下载遭遇 403。")
            
            
        except Exception as e:
            ws_log(f"❌ 浏览器启动失败: {e}", explicit_level="error")
            return
            
        try:
            spider = DiscuzSpiderService(page=page, log_callback=ws_log)
            from backend.services.avbase_client import avbase_client
            from sqlalchemy import select
            from backend.models import WhitelistActor, FailedRecord
            
            for i, record in enumerate(records):
                if self.stop_lab_requested:
                    ws_log("🛑 抢救计划被强制终止。")
                    break
                    
                code = record["code"]
                target_url = record["post_url"]
                section_key = record["section"]
                title = record["title"]
                
                ws_log(f"🔍 正在执行第 {i+1}/{len(records)} 个抢救目标：[{code}]")
                
                section_config = config.get("sections", {}).get(section_key, {})
                save_path = section_config.get("save_path", f"./downloads/{section_key}")
                
                # 为了确保能存入白名单文件夹，这里需要再次查一次纯净度
                task_save_path = save_path
                work_info = await avbase_client.get_work_info_by_code(code)
                actors_info = work_info.get("actors", [])
                if actors_info:
                    actor_names = [a["name"] for a in actors_info]
                    async with AsyncSessionLocal() as session:
                        wl_stmt = select(WhitelistActor)
                        wl_all = (await session.execute(wl_stmt)).scalars().all()
                        
                        covered_actor_names = set()
                        for wl in wl_all:
                            wl_aliases = [n.strip() for n in wl.aliases.split(',')] if wl.aliases else []
                            wl_names_set = set([wl.name] + wl_aliases)
                            matching_names = wl_names_set.intersection(set(actor_names))
                            if matching_names:
                                covered_actor_names.update(matching_names)
                                
                        if len(covered_actor_names) == len(actor_names) and len(actor_names) > 0:
                            wl_save_path = section_config.get('whitelist_save_path', '').strip()
                            if wl_save_path:
                                task_save_path = wl_save_path
                            else:
                                task_save_path = os.path.join(save_path, "精选演员")
                                
                if not os.path.exists(task_save_path):
                    os.makedirs(task_save_path)
                    
                # 随机延迟，模拟人类操作防封锁
                await asyncio.sleep(random.uniform(5.0, 10.0))
                
                # --- 方案 B: 纯物理肉搏战 ---
                ws_log(f"⚔️ 启动物理肉搏方案，强行驾驶浏览器驶入详情页: {target_url}")
                tab.get(target_url)
                
                # 等待 5 秒盾
                passed_shield = False
                for _ in range(20):
                    await asyncio.sleep(1)
                    title = tab.title or ""
                    html = tab.html or ""
                    if "Just a moment" not in title and "Cloudflare" not in title and "cf-turnstile" not in html:
                        passed_shield = True
                        break
                        
                if not passed_shield:
                    dl_res = "CF_BLOCKED_PHYSICAL"
                else:
                    html_text = tab.html or ""
                    import html as html_lib
                    import re
                    hrefs = re.findall(r'href=["\']([^"\']*mod=attachment[^"\']*)["\']', html_text)
                    if not hrefs:
                        exts = ['.torrent', '.zip', '.rar', '.7z', '.tar', '.gz', '.txt']
                        all_hrefs = re.findall(r'href=["\']([^"\']+)["\']', html_text)
                        hrefs = [h for h in all_hrefs if any(ext in h.lower() for ext in exts)]
                        
                    if not hrefs:
                        dl_res = "NO_ATTACHMENT"
                    else:
                        hrefs = [html_lib.unescape(h) for h in hrefs]
                        
                        # 使用设置好 Cookie 的 curl_cffi 进行物理级辅助下载
                        import urllib.parse
                        from curl_cffi.requests import AsyncSession as CurlAsyncSession
                        
                        try:
                            cookies_dict = tab.cookies().as_dict()
                        except TypeError:
                            cookies_list = tab.cookies(as_dict=False)
                            cookies_dict = {c['name']: c['value'] for c in cookies_list}
                            
                        headers = {
                            "User-Agent": tab.user_agent,
                            "Referer": target_url
                        }
                        
                        dl_res = "NO_VALID_DOWNLOAD"
                        ua = tab.user_agent.lower()
                        impersonate_profile = "chrome120"
                        if "edg/" in ua or "edge" in ua:
                            impersonate_profile = "edge101"
                        async with CurlAsyncSession(impersonate=impersonate_profile, cookies=cookies_dict, headers=headers, verify=False, timeout=25.0) as client:
                            for href in hrefs:
                                try:
                                    download_url = href if href.startswith('http') else urllib.parse.urljoin("https://x999x.me/", href)
                                    await asyncio.sleep(random.uniform(0.5, 1.5))
                                    dl_resp = await client.get(download_url, allow_redirects=True)
                                    if dl_resp.status_code == 200:
                                        if any(kw in dl_resp.content for kw in [b"\xe5\xb7\xb2\xe8\xb6\x85\xe5\x87\xba", b"\xe7\xb8\xbd\xe8\xa8\x88", b"\xe6\x9d\x83\xe9\x99\x90", b"\xe6\xac\xa1\xe6\x95\xb0\xe5\xb7\xb2\xe6\xbb\xa1"]):
                                            dl_res = "QUOTA_LIMIT"
                                            break
                                            
                                        content_head = dl_resp.content[:50]
                                        ext = ""
                                        cd = dl_resp.headers.get("Content-Disposition", "")
                                        server_ext = ""
                                        if "filename=" in cd:
                                            import urllib.parse
                                            filename_raw = cd.split("filename=")[-1].strip('"\'')
                                            server_ext = os.path.splitext(urllib.parse.unquote(filename_raw))[1].lower()

                                        is_valid = False
                                        if content_head.startswith(b'Rar!\x1a\x07'): 
                                            ext = ".rar"
                                            is_valid = True
                                        elif content_head.startswith(b'PK\x03\x04'): 
                                            ext = ".zip"
                                            is_valid = True
                                        elif content_head.startswith(b'7z\xbc\xaf\x27\x1c'): 
                                            ext = ".7z"
                                            is_valid = True
                                        elif content_head.startswith(b'd8:announce') or content_head.startswith(b'd4:info') or b':announce' in content_head: 
                                            ext = ".torrent"
                                            is_valid = True
                                        elif server_ext in ['.srt', '.ass', '.vtt', '.txt'] and not content_head.strip().startswith(b'<'):
                                            ext = server_ext
                                            is_valid = True
                                            
                                        if not is_valid:
                                            dl_res = "INVALID_FILE_CONTENT"
                                            continue
                                            
                                        safe_code = code.replace(":", "_").replace(" ", "_")
                                        filename = f"{safe_code}{ext}"
                                        file_path = os.path.join(task_save_path, filename)
                                        
                                        with open(file_path, "wb") as f:
                                            f.write(dl_resp.content)
                                            
                                        dl_res = "SUCCESS"
                                        break
                                    else:
                                        dl_res = f"DL_HTTP_ERROR_{dl_resp.status_code}"
                                except Exception as e:
                                    logger.error(f"Physical rescue download failed: {e}")
                                    continue
                
                async with AsyncSessionLocal() as session:
                    if dl_res == "SUCCESS":
                        await spider.save_record(session, section_key, code, title, target_url)
                        # 删除旧的失败记录
                        fail_stmt = select(FailedRecord).where(FailedRecord.code == code.upper())
                        fail_record = (await session.execute(fail_stmt)).scalar_one_or_none()
                        if fail_record:
                            await session.delete(fail_record)
                            await session.commit()
                        ws_log(f"✅ 🚑 [{code}] 抢救成功！附件已入库，已从回收站中移除。", explicit_level="success")
                    elif dl_res == "QUOTA_LIMIT":
                        ws_log("！！！触发论坛配额限制，抢救任务被迫终止！！！", explicit_level="error")
                        break
                    else:
                        ws_log(f"❌ 🚑 [{code}] 抢救依然失败，原因码: {dl_res}。记录继续保留在回收站中。", explicit_level="error")
                        # 更新失败时间或记录（可选）
                        fail_stmt = select(FailedRecord).where(FailedRecord.code == code.upper())
                        fail_record = (await session.execute(fail_stmt)).scalar_one_or_none()
                        if fail_record:
                            fail_record.reason = f"{dl_res} (重试失败)"
                            fail_record.failed_time = datetime.now()
                            await session.commit()
                            
        except Exception as e:
            ws_log(f"❌ 死链抢救任务出现异常: {e}", explicit_level="error")
        finally:
            if 'retry' in self.active_pages:
                del self.active_pages['retry']
            try:
                if 'tab' in locals() and tab:
                    tab.close()
                if not self.active_spiders:
                    page.quit()
            except:
                pass
            ws_log("✅ 执行完毕。独立任务标签页已安全释放。", explicit_level="success")

    async def run_sniper_task(self, records: list[dict]):
        """
        死链精准抢救任务：直接跳转原帖进行重新下载
        """
        def ws_log(msg: str, explicit_level: str = None):
            logger.info(msg)
            try:
                loop = asyncio.get_running_loop()
                level = explicit_level if explicit_level else "info"
                if level == "info":
                    if "错误" in msg or "异常" in msg or "失败" in msg: level = "error"
                    elif "避让" in msg or "跳过" in msg or "拦截" in msg: level = "warn"
                    elif "结束" in msg or "完成" in msg or "成功" in msg: level = "success"
                loop.create_task(sniper_manager.broadcast_json({"type": "log", "message": msg, "level": level}))
            except: pass

        if 'sniper' in self.active_pages:
            ws_log("❌ 精准狙击任务已经在运行中，请勿重复启动。", explicit_level="error")
            return

        ws_log(f"🚑 精准狙击特遣队出发！收到 {len(records)} 个抢救目标，准备执行定点爆破...")
        
        config = load_config()
        co = self._get_chromium_options(config)
        
        try:
            page = ChromiumPage(co)
            if config.get("hide_browser"):
                try: page.set.window.hide()
                except: pass
            
            self.active_pages['sniper'] = page
            tab = page.new_tab()
            ws_log("✅ DrissionPage 浏览器内核启动成功。")
            
            # 必须先访问一次该域名的主页，才能把该域名的持久化 Cookie 注入到 page 实例中
            ws_log("⏳ 正在接驳底层物理下载引擎...")
            tab.get("https://x999x.me/")
            # 等待出现论坛特征，证明破盾成功 (最多等 15 秒)
            passed = False
            for _ in range(15):
                await asyncio.sleep(1)
                html = tab.html or ""
                title = tab.title or ""
                if "forum-" in html or "portal.php" in html or "forum.php" in html or "首页" in title:
                    passed = True
                    break
            
            if passed:
                ws_log("✅ 绿卡预热成功，Cookie 已热加载。")
            else:
                ws_log("⚠️ 绿卡预热超时，疑似遭到极其严厉的 CF 盾拦截，这可能导致接下来的下载遭遇 403。")
            
            
        except Exception as e:
            ws_log(f"❌ 浏览器启动失败: {e}", explicit_level="error")
            return
            
        try:
            spider = DiscuzSpiderService(page=page, log_callback=ws_log)
            from backend.services.avbase_client import avbase_client
            from sqlalchemy import select
            from backend.models import WhitelistActor, FailedRecord
            
            for i, record in enumerate(records):
                if self.stop_lab_requested:
                    ws_log("🛑 抢救计划被强制终止。")
                    break
                    
                code = record["code"]
                target_url = record["post_url"]
                section_key = record["section"]
                title = record["title"]
                
                ws_log(f"🔍 正在执行第 {i+1}/{len(records)} 个抢救目标：[{code}]")
                
                section_config = config.get("sections", {}).get(section_key, {})
                save_path = section_config.get("save_path", f"./downloads/{section_key}")
                
                # 为了确保能存入白名单文件夹，这里需要再次查一次纯净度
                task_save_path = save_path
                work_info = await avbase_client.get_work_info_by_code(code)
                actors_info = work_info.get("actors", [])
                if actors_info:
                    actor_names = [a["name"] for a in actors_info]
                    async with AsyncSessionLocal() as session:
                        wl_stmt = select(WhitelistActor)
                        wl_all = (await session.execute(wl_stmt)).scalars().all()
                        
                        covered_actor_names = set()
                        for wl in wl_all:
                            wl_aliases = [n.strip() for n in wl.aliases.split(',')] if wl.aliases else []
                            wl_names_set = set([wl.name] + wl_aliases)
                            matching_names = wl_names_set.intersection(set(actor_names))
                            if matching_names:
                                covered_actor_names.update(matching_names)
                                
                        if len(covered_actor_names) == len(actor_names) and len(actor_names) > 0:
                            wl_save_path = section_config.get('whitelist_save_path', '').strip()
                            if wl_save_path:
                                task_save_path = wl_save_path
                            else:
                                task_save_path = os.path.join(save_path, "精选演员")
                                
                if not os.path.exists(task_save_path):
                    os.makedirs(task_save_path)
                    
                # 随机延迟，模拟人类操作防封锁
                await asyncio.sleep(random.uniform(5.0, 10.0))
                
                # --- 方案 B: 纯物理肉搏战 ---
                ws_log(f"⚔️ 启动物理肉搏方案，强行驾驶浏览器驶入详情页: {target_url}")
                tab.get(target_url)
                
                # 等待 5 秒盾
                passed_shield = False
                for _ in range(20):
                    await asyncio.sleep(1)
                    title = tab.title or ""
                    html = tab.html or ""
                    if "Just a moment" not in title and "Cloudflare" not in title and "cf-turnstile" not in html:
                        passed_shield = True
                        break
                        
                if not passed_shield:
                    dl_res = "CF_BLOCKED_PHYSICAL"
                else:
                    html_text = tab.html or ""
                    import html as html_lib
                    import re
                    hrefs = re.findall(r'href=["\']([^"\']*mod=attachment[^"\']*)["\']', html_text)
                    if not hrefs:
                        exts = ['.torrent', '.zip', '.rar', '.7z', '.tar', '.gz', '.txt']
                        all_hrefs = re.findall(r'href=["\']([^"\']+)["\']', html_text)
                        hrefs = [h for h in all_hrefs if any(ext in h.lower() for ext in exts)]
                        
                    if not hrefs:
                        dl_res = "NO_ATTACHMENT"
                    else:
                        hrefs = [html_lib.unescape(h) for h in hrefs]
                        
                        # 使用设置好 Cookie 的 curl_cffi 进行物理级辅助下载
                        import urllib.parse
                        from curl_cffi.requests import AsyncSession as CurlAsyncSession
                        
                        try:
                            cookies_dict = tab.cookies().as_dict()
                        except TypeError:
                            cookies_list = tab.cookies(as_dict=False)
                            cookies_dict = {c['name']: c['value'] for c in cookies_list}
                            
                        headers = {
                            "User-Agent": tab.user_agent,
                            "Referer": target_url
                        }
                        
                        dl_res = "NO_VALID_DOWNLOAD"
                        ua = tab.user_agent.lower()
                        impersonate_profile = "chrome120"
                        if "edg/" in ua or "edge" in ua:
                            impersonate_profile = "edge101"
                        async with CurlAsyncSession(impersonate=impersonate_profile, cookies=cookies_dict, headers=headers, verify=False, timeout=25.0) as client:
                            for href in hrefs:
                                try:
                                    download_url = href if href.startswith('http') else urllib.parse.urljoin("https://x999x.me/", href)
                                    await asyncio.sleep(random.uniform(0.5, 1.5))
                                    dl_resp = await client.get(download_url, allow_redirects=True)
                                    if dl_resp.status_code == 200:
                                        if any(kw in dl_resp.content for kw in [b"\xe5\xb7\xb2\xe8\xb6\x85\xe5\x87\xba", b"\xe7\xb8\xbd\xe8\xa8\x88", b"\xe6\x9d\x83\xe9\x99\x90", b"\xe6\xac\xa1\xe6\x95\xb0\xe5\xb7\xb2\xe6\xbb\xa1"]):
                                            dl_res = "QUOTA_LIMIT"
                                            break
                                            
                                        content_head = dl_resp.content[:50]
                                        ext = ""
                                        cd = dl_resp.headers.get("Content-Disposition", "")
                                        server_ext = ""
                                        if "filename=" in cd:
                                            import urllib.parse
                                            filename_raw = cd.split("filename=")[-1].strip('"\'')
                                            server_ext = os.path.splitext(urllib.parse.unquote(filename_raw))[1].lower()

                                        is_valid = False
                                        if content_head.startswith(b'Rar!\x1a\x07'): 
                                            ext = ".rar"
                                            is_valid = True
                                        elif content_head.startswith(b'PK\x03\x04'): 
                                            ext = ".zip"
                                            is_valid = True
                                        elif content_head.startswith(b'7z\xbc\xaf\x27\x1c'): 
                                            ext = ".7z"
                                            is_valid = True
                                        elif content_head.startswith(b'd8:announce') or content_head.startswith(b'd4:info') or b':announce' in content_head: 
                                            ext = ".torrent"
                                            is_valid = True
                                        elif server_ext in ['.srt', '.ass', '.vtt', '.txt'] and not content_head.strip().startswith(b'<'):
                                            ext = server_ext
                                            is_valid = True
                                            
                                        if not is_valid:
                                            dl_res = "INVALID_FILE_CONTENT"
                                            continue
                                            
                                        safe_code = code.replace(":", "_").replace(" ", "_")
                                        filename = f"{safe_code}{ext}"
                                        file_path = os.path.join(task_save_path, filename)
                                        
                                        with open(file_path, "wb") as f:
                                            f.write(dl_resp.content)
                                            
                                        dl_res = "SUCCESS"
                                        break
                                    else:
                                        dl_res = f"DL_HTTP_ERROR_{dl_resp.status_code}"
                                except Exception as e:
                                    logger.error(f"Physical rescue download failed: {e}")
                                    continue
                
                async with AsyncSessionLocal() as session:
                    if dl_res == "SUCCESS":
                        await spider.save_record(session, section_key, code, title, target_url)
                        # 删除旧的失败记录
                        fail_stmt = select(FailedRecord).where(FailedRecord.code == code.upper())
                        fail_record = (await session.execute(fail_stmt)).scalar_one_or_none()
                        if fail_record:
                            await session.delete(fail_record)
                            await session.commit()
                        ws_log(f"✅ 🚑 [{code}] 抢救成功！附件已入库，已从狙击目标中移除。", explicit_level="success")
                    elif dl_res == "QUOTA_LIMIT":
                        ws_log("！！！触发论坛配额限制，抢救任务被迫终止！！！", explicit_level="error")
                        break
                    else:
                        ws_log(f"❌ 🚑 [{code}] 抢救依然失败，原因码: {dl_res}。记录继续保留在狙击目标中。", explicit_level="error")
                        # 更新失败时间或记录（可选）
                        fail_stmt = select(FailedRecord).where(FailedRecord.code == code.upper())
                        fail_record = (await session.execute(fail_stmt)).scalar_one_or_none()
                        if fail_record:
                            fail_record.reason = f"{dl_res} (重试失败)"
                            fail_record.failed_time = datetime.now()
                            await session.commit()
                            
        except Exception as e:
            ws_log(f"❌ 精准狙击任务出现异常: {e}", explicit_level="error")
        finally:
            if 'sniper' in self.active_pages:
                del self.active_pages['sniper']
            try:
                if 'tab' in locals() and tab:
                    tab.close()
                if not self.active_spiders:
                    page.quit()
            except:
                pass
            ws_log("✅ 执行完毕。独立任务标签页已安全释放。", explicit_level="success")

task_manager = TaskManager()
