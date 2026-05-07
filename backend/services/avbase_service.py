import asyncio
import logging
import re
from backend.services.task_manager import task_manager

logger = logging.getLogger(__name__)

class AvbaseService:
    async def scrape_avbase(self, code: str) -> dict:
        """
        借用 task_manager 中的常驻隐身浏览器抓取 AVBase。
        使用独立的新标签页，抓完即焚。
        """
        # 寻找可用的常驻浏览器 (例如 cf_clearance 或 其他版块活跃的 page)
        # 如果没有，可能需要新开一个临时浏览器，但为了性能和伪装，最好借助已有的
        
        # 考虑到目前系统可能没在跑任务，如果没有浏览器，我们需要起一个伪无头的
        page = None
        for key in ['cf_clearance', 'login_auth', 'vr', '4k', 'hd', 'sub']:
            if key in task_manager.active_pages:
                page = task_manager.active_pages[key]
                break
                
        is_temp_browser = False
        if not page:
            # 临时启动一个伪无头浏览器
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

        # 打开新标签页
        tab = page.new_tab()
        try:
            # 1. 搜索
            search_url = f"https://avbase.net/search?q={code}"
            logger.info(f"AvBase Scraper: Navigating to {search_url}")
            tab.get(search_url)
            await asyncio.sleep(2) # 等待加载和潜在的 CF 盾
            
            # 判断 CF
            if "Just a moment" in tab.title or "cf-turnstile" in tab.html:
                logger.warning("AvBase Scraper: Encountered CF shield, waiting longer...")
                await asyncio.sleep(8)
                
            html = tab.html
            
            # 解析
            # 如果搜索结果只有一条，AVBase 通常会直接跳转到详情页
            # 判断是在搜索列表还是在详情页
            actor = "未知演员"
            cover_url = ""
            
            if "Video Details" in tab.title or "作品详情" in html or "Movie Details" in html or "影片详情" in html or code.upper() in tab.title.upper():
                # 在详情页
                img_tag = tab.ele('css:img.video-cover')
                if img_tag:
                    cover_url = img_tag.attr('src')
                
                # 找演员
                # 简单用正则找女优名字的区域，或者直接用元素定位
                actor_eles = tab.eles('css:a[href*="/star/"]')
                if actor_eles:
                    actor = " ".join([a.text for a in actor_eles if a.text])
            else:
                # 在列表页
                card = tab.ele('.video-card')
                if card:
                    img = card.ele('tag:img')
                    if img: cover_url = img.attr('src')
                    
                    # 尝试点进去拿演员
                    detail_link = card.ele('tag:a')
                    if detail_link:
                        href = detail_link.attr('href')
                        tab.get(href)
                        await asyncio.sleep(1)
                        actor_eles = tab.eles('css:a[href*="/star/"]')
                        if actor_eles:
                            actor = " ".join([a.text for a in actor_eles if a.text])

            if cover_url and cover_url.startswith('/'):
                cover_url = "https://avbase.net" + cover_url

            if not cover_url:
                logger.warning(f"AvBase Scraper: Could not find data for {code}")
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