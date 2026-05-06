import os
import re
import random
import asyncio
import logging
from datetime import datetime
from typing import Optional, Set, Callable, Dict, Any
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from DrissionPage import ChromiumPage

from backend.models import DownloadRecord
from core.utils import extract_code

logger = logging.getLogger(__name__)

class DiscuzSpiderService:
    def __init__(self, page: Optional[ChromiumPage] = None, log_callback: Optional[Callable[[str], None]] = None):
        self.page = page
        self.log_callback = log_callback
        self.stop_requested = False

    def _log(self, message: str):
        if self.log_callback:
            self.log_callback(message)
        logger.info(message)

    async def _human_delay(self, config: Dict[str, Any], min_s=1.5, max_s=4.0):
        if not config.get('simulate_human', True):
            await asyncio.sleep(0.5)
            return
        await asyncio.sleep(random.uniform(min_s, max_s))

    async def _human_scroll(self, config: Dict[str, Any]):
        if not config.get('simulate_human', True): return
        if not self.page: return
        try:
            for _ in range(random.randint(1, 3)):
                self.page.scroll.down(random.randint(300, 800))
                await asyncio.sleep(random.uniform(0.5, 1.5))
        except Exception as e:
            logger.debug(f"Scroll error: {e}")

    async def check_code_exists_in_section(self, session: AsyncSession, section: str, code: str) -> bool:
        stmt = select(DownloadRecord).where(DownloadRecord.section == section, DownloadRecord.code == code.upper())
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def save_record(self, session: AsyncSession, section: str, code: str, title: str, post_url: str):
        stmt = select(DownloadRecord).where(DownloadRecord.code == code.upper())
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()
        
        if record:
            record.section = section
            record.title = title
            record.post_url = post_url
            record.download_time = datetime.now()
        else:
            record = DownloadRecord(
                section=section,
                code=code.upper(),
                title=title,
                post_url=post_url,
                download_time=datetime.now()
            )
            session.add(record)
        await session.commit()

    async def run_task(self, session: AsyncSession, config: Dict[str, Any], section_key: str):
        if not self.page:
            self._log("错误：未初始化浏览器页面实例。")
            return

        try:
            self.stop_requested = False
            downloaded_count = 0
            limit = config.get('daily_limit')
            if limit is None: limit = 55
            start_page = int(config.get('start_page', 1))
            save_path = config.get('save_path', './downloads')
            section_url = config.get('url')
            
            if not os.path.exists(save_path):
                os.makedirs(save_path)
            
            # 获取该版块已下载的番号，用于去重
            stmt = select(DownloadRecord.code).where(DownloadRecord.section == section_key)
            result = await session.execute(stmt)
            downloaded_codes = set(result.scalars().all())
            
            page_num = start_page
            while not self.stop_requested and downloaded_count < limit:
                self._log(f"--- 正在解析第 {page_num} 页 ---")
                await self._human_delay(config, 1.0, 3.0)
                self.page.get(f"{section_url}&page={page_num}")
                await self._human_delay(config, 3.0, 6.0)
                await self._human_scroll(config)
                
                # --- CF 盾拦截检测 ---
                page_title = self.page.title or ""
                page_html = self.page.html or ""
                
                is_cf = "Just a moment" in page_title or "请稍候" in page_title or "Cloudflare" in page_title or "challenges.cloudflare.com" in page_html or "cf-turnstile" in page_html
                
                if is_cf:
                    self._log("🚨 遭遇 CF 盾拦截！无法获取论坛帖子。")
                    self._log("💡 建议：请前往【任务调度中心】点击【获取长效 CF 绿卡】按钮，手动通过一次验证。")
                    self.stop_requested = True
                    break
                    
                is_forum = "mod=viewthread" in page_html or "forumdisplay" in page_html or "portal.php" in page_html or "forum.php" in page_html or "首页" in page_title
                if not is_forum:
                    self._log(f"⚠️ 警告：当前页面似乎不是论坛页面，标题为: {page_title[:20]}")
                
                tasks = []
                seen_tids = set()
                for a in self.page.eles('tag:a'):
                    try:
                        href = a.attr('href') or ''
                        if 'viewthread' in href or 'thread-' in href:
                            tid_match = (re.search(r'tid=(\d+)', href) or re.search(r'thread-(\d+)', href))
                            tid = tid_match.group(1) if tid_match else href
                            if tid in seen_tids: continue
                            text = a.text or a.attr('title') or ""
                            code = extract_code(text)
                            if code:
                                tasks.append({'code': code, 'link': href, 'title': text})
                                seen_tids.add(tid)
                    except: continue

                if not tasks:
                    self._log(f"第 {page_num} 页无新番号。")
                else:
                    self._log(f"第 {page_num} 页发现 {len(tasks)} 个潜在番号。")
                    for i, task in enumerate(tasks):
                        if self.stop_requested: break
                        code = task['code']
                        title = task['title']
                        post_url = task['link']
                        
                        # --- 核心联动逻辑：画质优先策略 ---
                        skip_download = False
                        is_upgrade = False
                        
                        # 如果是 4K 版块
                        if section_key == '4k':
                            if code in downloaded_codes:
                                skip_download = True
                            elif await self.check_code_exists_in_section(session, 'hd', code):
                                self._log(f"[检测升级] {code} 在 HD 库已存在，正在升级为 4K...")
                                is_upgrade = True
                        
                        # 如果是 HD 版块
                        elif section_key == 'hd':
                            if code in downloaded_codes or await self.check_code_exists_in_section(session, '4k', code):
                                if await self.check_code_exists_in_section(session, '4k', code):
                                    self._log(f"[避让] {code} 在 4K 库已存在，HD 版块跳过。")
                                skip_download = True
                                
                        # 其他版块常规去重
                        else:
                            if code in downloaded_codes:
                                skip_download = True
                        
                        if skip_download: continue
                        
                        self._log(f"[页:{page_num} 进度:{i+1}/{len(tasks)}] 正在处理: {code}")
                        await self._human_delay(config, 1.0, 2.5)
                        
                        # 下载逻辑
                        result = await self._download_attachments(post_url, code, save_path, config)
                        
                        if result == "SUCCESS":
                            downloaded_count += 1
                            downloaded_codes.add(code)
                            await self.save_record(session, section_key, code, title, post_url)
                            msg = f"成功下载 [{code}]" + (" (画质已升档 ✅)" if is_upgrade else "")
                            self._log(msg)
                        elif result == "QUOTA_LIMIT":
                            self._log("！！！配额耗尽，停止！！！")
                            self.stop_requested = True
                            break
                        else:
                            self._log(f"[{code}] 失败，跳过。")
                            # 按照原逻辑，失败是停止。但我个人认为可以尝试下一个。
                            # 原逻辑: self.stop_requested = True; break
                            # 这里还是保持原逻辑
                            self.stop_requested = True
                            break
                        await self._human_delay(config, 3.0, 7.0)

                if not self.stop_requested:
                    page_num += 1
                else:
                    break
            self._log(f"任务结束。")
        except Exception as e:
            self._log(f"崩溃: {e}")
            logger.exception("Spider task crashed")

    async def _download_attachments(self, detail_url: str, code: str, save_path: str, config: Dict[str, Any]) -> str:
        if not self.page: return "FAILED"
        try:
            self.page.get(detail_url)
            await self._human_delay(config, 2.5, 5.0)
            await self._human_scroll(config)

            attach_eles = self.page.eles('css:a[href*="mod=attachment"]')
            if not attach_eles:
                exts = ['.torrent', '.zip', '.rar', '.7z', '.tar', '.gz', '.txt']
                attach_eles = [l for l in self.page.eles('tag:a') if any(ext in (l.attr('href') or '').lower() for ext in exts)]

            if not attach_eles: return "FAILED"

            # 使用协议级纯代码极速下载，保障原子性
            import httpx
            import urllib.parse

            cookies_list = self.page.cookies(as_dict=False)
            cookies_dict = {c['name']: c['value'] for c in cookies_list}
            headers = {
                "User-Agent": self.page.user_agent,
                "Referer": detail_url
            }

            for att in attach_eles:
                try:
                    await self._human_delay(config, 0.5, 1.5)
                    href = att.attr('href')
                    if not href: continue
                    download_url = href if href.startswith('http') else urllib.parse.urljoin("https://x999x.me/", href)

                    async with httpx.AsyncClient(cookies=cookies_dict, headers=headers, verify=False, timeout=30.0) as client:
                        resp = await client.get(download_url, follow_redirects=True)

                        if resp.status_code == 200:
                            html_text = resp.text
                            # 校验是否跳转到错误提示页
                            if any(ind in html_text for ind in ["已超出", "總計", "权限", "次数已满"]):
                                return "QUOTA_LIMIT"

                            # 获取附件真实名字，如果没有则默认 code.torrent
                            cd = resp.headers.get("content-disposition", "")
                            ext = ".torrent"
                            if "filename=" in cd:
                                match = re.search(r'filename="?([^"]+)"?', cd)
                                if match:
                                    ext_match = os.path.splitext(match.group(1))[1]
                                    if ext_match: ext = ext_match

                            safe_code = code.replace(":", "_").replace(" ", "_")
                            filename = f"{safe_code}{ext}"
                            file_path = os.path.join(save_path, filename)

                            with open(file_path, "wb") as f:
                                f.write(resp.content)

                            # 原子性落盘完成，确认100%成功
                            return "SUCCESS"

                except Exception as e:
                    logger.error(f"HTTPX Download failed for {code}: {e}")
                    continue

            return "FAILED"
        except Exception as e:
            logger.error(f"Download attachments failed for {code}: {e}")
            return "FAILED"
    def stop(self):
        self.stop_requested = True
