import asyncio
import logging
import os
import random
from datetime import datetime
from backend.database import AsyncSessionLocal
from backend.services.spider_service import DiscuzSpiderService
from backend.routers.websocket import manager
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
            await self.broadcast_queue_status()
            
            try:
                await self._execute_discuz_spider(section_key, mode)
            except Exception as e:
                logger.error(f"Worker execution error: {e}")
            finally:
                self.current_running_task = None
                
            # Broadcast queue update after completion
            await self.broadcast_queue_status()

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

    async def run_completion_search(self, codes: list[str]):
        """
        女优补全计划：带着缺失番号列表前往论坛进行逐个搜索并下载
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

        if 'completion' in self.active_pages:
            ws_log("❌ 补全搜索任务已经在运行中，请勿重复启动。", explicit_level="error")
            return

        ws_log(f"🚀 女优补全计划正式启动！收到 {len(codes)} 个缺失番号清单，准备切入论坛主动检索模式...")
        
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
            
            self.active_pages['completion'] = page
            ws_log("✅ DrissionPage 浏览器内核启动成功。")
        except Exception as e:
            ws_log(f"❌ 浏览器启动失败: {e}", explicit_level="error")
            return
            
        try:
            # 实例化一个临时的 Spider Service 以复用其下载附件的底层能力
            spider = DiscuzSpiderService(page=page, log_callback=ws_log)
            
            for i, code in enumerate(codes):
                if self.stop_lab_requested:
                    ws_log("🛑 补全计划被强制终止。")
                    break
                    
                ws_log(f"🔍 正在执行第 {i+1}/{len(codes)} 个目标搜索：{code}")
                
                # 访问搜索页面
                search_url = f"https://x999x.me/search.php?mod=forum&srchtxt={code}&searchsubmit=yes"
                page.get(search_url)
                
                # 随机延迟，不仅防盾，还要规避论坛“15秒内不能连续搜索”的限制
                await asyncio.sleep(random.uniform(16.0, 20.0))
                
                page_title = page.title or ""
                page_html = page.html or ""
                
                if "Just a moment" in page_title or "Cloudflare" in page_title:
                    ws_log(f"❌ 搜刮 {code} 时遭遇 CF 盾拦截，暂缓执行。", explicit_level="error")
                    continue
                    
                if "抱歉，您在" in page_html and "秒内只能进行一次搜索" in page_html:
                    ws_log(f"⏳ 触发论坛搜索频率限制，退避等待 20 秒...", explicit_level="warn")
                    await asyncio.sleep(20)
                    page.get(search_url)
                    await asyncio.sleep(random.uniform(5.0, 8.0))
                    page_html = page.html or ""
                
                if "抱歉，没有找到匹配结果" in page_html:
                    ws_log(f"🚧 [{code}] 论坛内暂无资源，标记为缺失。", explicit_level="warn")
                    continue
                    
                # 提取搜索结果列表
                # Discuz 搜索结果通常在 class="pbw" 或特定的 li/div 中
                results = []
                for item in page.eles('tag:li@class:pbw'):
                    try:
                        title_a = item.ele('tag:h3').ele('tag:a')
                        title_text = title_a.text
                        href = title_a.attr('href')
                        
                        # 找到版块名称
                        forum_a = item.ele('tag:p').eles('tag:a')[1] # 通常第二个a标签是版块名
                        forum_name = forum_a.text if forum_a else ""
                        
                        results.append({
                            "title": title_text,
                            "href": href,
                            "forum": forum_name
                        })
                    except:
                        pass
                
                if not results:
                    # 尝试其他可能的 DOM 结构
                    for item in page.eles('tag:h3'):
                        try:
                            title_a = item.ele('tag:a')
                            if not title_a: continue
                            href = title_a.attr('href')
                            if 'tid=' not in href and 'thread-' not in href: continue
                            
                            title_text = title_a.text
                            # 粗略提取版块名（如果没有明确的标签，就当作未知）
                            results.append({
                                "title": title_text,
                                "href": href,
                                "forum": "未知"
                            })
                        except: pass

                if not results:
                    ws_log(f"🚧 [{code}] 未解析到有效的搜索结果条目。", explicit_level="warn")
                    continue
                    
                # 优先级排序: 4K超清 > VR視頻 > 高清有碼 > 其他
                target_result = None
                
                for res in results:
                    forum = res["forum"]
                    title = res["title"]
                    # 必须确认标题真的包含目标番号，防止论坛搜索引擎瞎匹配
                    if code.upper() not in title.upper():
                        continue
                        
                    if "4K" in forum or "4K" in title.upper():
                        target_result = res
                        target_result["section"] = "4k"
                        break # 找到了最高优先级，直接选定
                        
                if not target_result:
                    for res in results:
                        forum = res["forum"]
                        title = res["title"]
                        if code.upper() not in title.upper(): continue
                        if "VR" in forum or "VR" in title.upper():
                            target_result = res
                            target_result["section"] = "vr"
                            break
                            
                if not target_result:
                    for res in results:
                        forum = res["forum"]
                        title = res["title"]
                        if code.upper() not in title.upper(): continue
                        if "高清" in forum or "有碼" in forum or "HD" in title.upper():
                            target_result = res
                            target_result["section"] = "hd"
                            break

                if not target_result:
                    # 随便选一个包含番号的
                    for res in results:
                        if code.upper() in res["title"].upper():
                            target_result = res
                            target_result["section"] = "hd" # 默认归入 hd
                            break
                            
                if not target_result:
                    ws_log(f"🚧 [{code}] 搜索结果中没有完全匹配的标题，安全跳过。", explicit_level="warn")
                    continue
                    
                # 开始执行下载
                section_key = target_result["section"]
                target_url = target_result["href"]
                target_title = target_result["title"]
                
                section_config = config.get("sections", {}).get(section_key, {})
                save_path = section_config.get("save_path", f"./downloads/{section_key}")
                
                ws_log(f"🎯 成功锁定 [{code}] 目标资源 (判为 {section_key} 级): {target_title[:20]}...")
                
                # 借用 spider_service 的 _download_attachments
                # 因为补全计划肯定是白名单级别的女优，所以可以直接放进 whitelist_save_path (如果配置了的话)
                wl_save_path = section_config.get('whitelist_save_path', '').strip()
                if wl_save_path:
                    final_save_path = wl_save_path
                else:
                    final_save_path = os.path.join(save_path, "精选演员")
                    
                if not os.path.exists(final_save_path):
                    os.makedirs(final_save_path)
                
                # 执行纯代码静默下载
                dl_res = await spider._download_attachments(target_url, code, final_save_path, section_config)
                
                if dl_res == "SUCCESS":
                    # 入库
                    async with AsyncSessionLocal() as session:
                        await spider.save_record(session, section_key, code, target_title, target_url)
                    ws_log(f"✅ [{code}] 补全下载成功，已归档入库！", explicit_level="success")
                elif dl_res == "QUOTA_LIMIT":
                    ws_log("！！！触发论坛配额限制，补全计划被迫终止！！！", explicit_level="error")
                    break
                else:
                    ws_log(f"❌ [{code}] 补全下载失败，原因码: {dl_res}", explicit_level="error")
                    
        except Exception as e:
            ws_log(f"❌ 补全搜索任务出现异常: {e}", explicit_level="error")
        finally:
            if 'completion' in self.active_pages:
                del self.active_pages['completion']
            try:
                page.quit()
            except:
                pass
            ws_log("✅ 补全计划所有扫描流程执行完毕。浏览器资源已释放。", explicit_level="success")

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
            ws_log("✅ DrissionPage 浏览器内核启动成功。")
            
            # 必须先访问一次该域名的主页，才能把该域名的持久化 Cookie 注入到 page 实例中
            page.get("https://x999x.me/")
            
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
                actors_info = await avbase_client.get_actors_by_code(code)
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
                
                # 直接执行定点下载
                dl_res = await spider._download_attachments(target_url, code, task_save_path, section_config)
                
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
                page.quit()
            except:
                pass
            ws_log("✅ 死链抢救列车执行完毕。浏览器资源已释放。", explicit_level="success")

task_manager = TaskManager()
