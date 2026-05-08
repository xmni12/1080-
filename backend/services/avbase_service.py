import asyncio
import logging
import re
from backend.services.task_manager import task_manager
from backend.routers.websocket import manager

logger = logging.getLogger(__name__)

class AvbaseService:
    async def scrape_avbase(self, code: str) -> dict:
        """
        借用 task_manager 中的常驻隐身浏览器抓取 AVBase。
        使用独立的新标签页，抓完即焚。
        """
        async def push_status(msg: str):
            await manager.broadcast_json({"type": "lab_status", "message": msg})
            
        # 寻找可用的常驻浏览器
        page = None
        for key in ['cf_clearance', 'login_auth', 'vr', '4k', 'hd', 'sub']:
            if key in task_manager.active_pages:
                page = task_manager.active_pages[key]
                break
                
        is_temp_browser = False
        if not page:
            await push_status("🤖 正在唤醒底层隐身浏览器 (Temp Browser)...")
            logger.info("AvBase Scraper: No active browser found, starting a temp one...")
            from DrissionPage import ChromiumPage, ChromiumOptions
            import os
            co = ChromiumOptions().set_local_port(9222)
            profile_path = os.path.abspath('data/browser_profile')
            co.set_user_data_path(profile_path)
            co.set_argument('--window-position=-32000,-32000')
            try:
                page = ChromiumPage(addr_or_opts=co)
                try: page.set.window.hide()
                except: pass
                is_temp_browser = True
            except Exception as e:
                logger.error(f"Failed to start temp browser for AvBase: {e}")
                return None
        else:
            await push_status("⚡ 成功借用常驻浏览器，准备进入暗网...")

        # 打开新标签页
        tab = page.new_tab()
        try:
            # 1. 搜索
            search_url = f"https://www.avbase.net/works?q={code}"
            await push_status(f"🌐 正在突破 avbase.net，执行深度检索...")
            logger.info(f"AvBase Scraper: Navigating to {search_url}")
            tab.get(search_url)
            await asyncio.sleep(2) # 等待加载和潜在的 CF 盾
            
            # 判断 CF
            if "Just a moment" in tab.title or "cf-turnstile" in tab.html:
                await push_status("🛡️ 遭遇五秒 CF 盾！执行强制静默等待 (8秒)...")
                logger.warning("AvBase Scraper: Encountered CF shield, waiting longer...")
                await asyncio.sleep(8)
                
            await push_status("✅ 破盾成功！正在解析 DOM 树提取档案数据...")
            
            # 检查是否还在列表页
            # 如果 URL 中没有包含 "/works/" 或者 URL 中包含 "?q="，说明我们在搜索结果页
            if "/works/" not in tab.url or "?q=" in tab.url:
                # 寻找第一个匹配的详情页链接
                detail_link = None
                for a in tab.eles('tag:a'):
                    href = a.attr('href') or ""
                    if "/works/" in href and "?q=" not in href and "date/" not in href:
                        detail_link = href
                        break
                
                if detail_link:
                    await push_status("🔎 发现详情页入口，正在潜入...")
                    tab.get(detail_link if detail_link.startswith('http') else f"https://www.avbase.net{detail_link}")
                    await asyncio.sleep(2)
                else:
                    logger.warning(f"AvBase Scraper: Could not find detail page link for {code}")
                    return None

            # 现在应该在详情页了
            actor = "未知演员"
            cover_url = ""
            
            # 提取演员 (AVBase 的演员链接是以 /talents/ 开头)
            actor_eles = tab.eles('css:a[href*="/talents/"]')
            if actor_eles:
                # 过滤掉空的，并且去重
                actors = []
                for a in actor_eles:
                    text = a.text.strip()
                    if text and text not in actors:
                        actors.append(text)
                if actors:
                    actor = " ".join(actors)
                    
            # 提取封面 (通常包含 max-w-full 或 img-fallback class)
            img_eles = tab.eles('tag:img')
            for img in img_eles:
                cls = img.attr('class') or ""
                src = img.attr('src') or ""
                if "max-w-full" in cls or "pl.jpg" in src or "ps.jpg" in src:
                    cover_url = src
                    break

            if cover_url and cover_url.startswith('/'):
                cover_url = "https://www.avbase.net" + cover_url

            if not cover_url and actor == "未知演员":
                logger.warning(f"AvBase Scraper: Could not find any valid data on detail page for {code}")
                return None

            return {
                "actor": actor,
                "cover_url": cover_url
            }

        except Exception as e:
            logger.error(f"AvBase Scraper Error: {e}")
            return None
        finally:
            try:
                tab.close()
            except: pass
            if is_temp_browser:
                try: page.quit()
                except: pass

avbase_service = AvbaseService()