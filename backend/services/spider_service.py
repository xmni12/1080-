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

from backend.models import DownloadRecord, BlacklistActor, WhitelistActor
from backend.services.avbase_client import avbase_client
from core.utils import extract_code

logger = logging.getLogger(__name__)

class DiscuzSpiderService:
    def __init__(self, page: Optional[ChromiumPage] = None, log_callback: Optional[Callable[[str, str], None]] = None):
        self.page = page
        self.log_callback = log_callback
        self.stop_requested = False

    def _log(self, message: str, level: str = "info"):
        if self.log_callback:
            self.log_callback(message, level)
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
        stmt = select(DownloadRecord.id).where(DownloadRecord.section == section, DownloadRecord.code == code.upper())
        result = await session.execute(stmt)
        return result.first() is not None

    async def check_code_exists_globally(self, session: AsyncSession, code: str) -> bool:
        stmt = select(DownloadRecord.id).where(DownloadRecord.code == code.upper())
        result = await session.execute(stmt)
        return result.first() is not None

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

    async def run_task(self, session: AsyncSession, config: Dict[str, Any], section_key: str, mode: str = "new"):
        if not self.page:
            self._log("错误：未初始化浏览器页面实例。")
            return

        try:
            self.stop_requested = False
            downloaded_count = 0
            limit = config.get('daily_limit')
            if limit is None: limit = 55
            
            if mode == "new":
                start_page = 1
                # 极速追新模式：扫描深度从设置中读取，默认10页
                max_depth = int(config.get('quick_scan_depth', 10))
                end_page = max_depth
                self._log(f"🚀 极速追新模式启动：将固定扫描前 {max_depth} 页内容。")
            else:
                start_page = int(config.get('history_page', 1))
                end_page = 9999 # 考古模式无深度限制，直到配额满或见底
                
            save_path = config.get('save_path', './downloads')
            section_url = config.get('url')
            
            if not os.path.exists(save_path):
                os.makedirs(save_path)
            
            # 获取该版块已下载的番号，用于去重
            stmt = select(DownloadRecord.code).where(DownloadRecord.section == section_key)
            result = await session.execute(stmt)
            downloaded_codes = set(result.scalars().all())
            
            page_num = start_page
            
            while not self.stop_requested and downloaded_count < limit and page_num <= end_page:
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
                    
                    from core.utils import load_config
                    global_config = load_config()
                    spider_threads = int(global_config.get("spider_threads", 3)) # 默认为3并发
                    sem = asyncio.Semaphore(spider_threads)
                    db_lock = asyncio.Lock()

                    async def process_task(task_obj):
                        nonlocal downloaded_count
                        if self.stop_requested: return
                        code = task_obj['code']
                        title = task_obj['title']
                        post_url = task_obj['link']
                        
                        skip_download = False
                        is_upgrade = False
                        
                        async with db_lock:
                            is_global_exists = await self.check_code_exists_globally(session, code)
                            
                            if section_key == '4k':
                                if await self.check_code_exists_in_section(session, '4k', code):
                                    skip_download = True
                                elif await self.check_code_exists_in_section(session, 'hd', code):
                                    self._log(f"🔄 [检测升级] {code} 在 HD 库已存在，正在准备升级为 4K...", level="info")
                                    is_upgrade = True
                                elif is_global_exists:
                                    skip_download = True
                            elif section_key == 'hd':
                                if await self.check_code_exists_in_section(session, '4k', code):
                                    self._log(f"🚧 [避让] {code} 在 4K 库已存在，HD 版块跳过。", level="warn")
                                    skip_download = True
                                elif is_global_exists:
                                    skip_download = True
                            else:
                                if is_global_exists:
                                    skip_download = True
                        
                        if skip_download:
                            return
                        
                        # --- AVBase 智能多维演员滤网 (A+B方案) ---
                        actors_info = await avbase_client.get_actors_by_code(code)
                        if actors_info:
                            actor_names = [a["name"] for a in actors_info]
                            async with db_lock:
                                wl_stmt = select(WhitelistActor)
                                wl_all = (await session.execute(wl_stmt)).scalars().all()
                                bl_stmt = select(BlacklistActor)
                                bl_all = (await session.execute(bl_stmt)).scalars().all()
                                
                                whitelisted = []
                                for wl in wl_all:
                                    wl_aliases = [n.strip() for n in wl.aliases.split(',')] if wl.aliases else []
                                    wl_names_set = set([wl.name] + wl_aliases)
                                    matching_names = wl_names_set.intersection(set(actor_names))
                                    if matching_names:
                                        whitelisted.append(wl.name)
                                        if not wl.avatar_url:
                                            for info in actors_info:
                                                if info["name"] in matching_names and info["avatar_url"]:
                                                    wl.avatar_url = info["avatar_url"]
                                                    break
                                
                                if whitelisted:
                                    await session.commit()
                                    wl_names_str = ", ".join(whitelisted)
                                    # 如果命中了白名单，直接跳过黑名单检查，无敌放行
                                    self._log(f"💖 [{code}] 喜爱名单特权：包含心动女优 [{wl_names_str}]，最高优先级放行！", level="success")
                                else:
                                    blocked = []
                                    for bl in bl_all:
                                        bl_aliases = [n.strip() for n in bl.aliases.split(',')] if bl.aliases else []
                                        bl_names_set = set([bl.name] + bl_aliases)
                                        matching_names = bl_names_set.intersection(set(actor_names))
                                        if matching_names:
                                            blocked.append(bl.name)
                                            if not bl.avatar_url:
                                                for info in actors_info:
                                                    if info["name"] in matching_names and info["avatar_url"]:
                                                        bl.avatar_url = info["avatar_url"]
                                                        break
                                    
                                    if blocked:
                                        await session.commit()
                                        if len(actor_names) == 1:
                                            # 单体作品，直接枪毙
                                            self._log(f"🚧 [{code}] 单人黑名单拦截：主演 [{blocked[0]}]，已丢弃！", level="warn")
                                            return
                                        else:
                                            # 多人共演
                                            if len(blocked) == len(actor_names):
                                                # 全员恶人，全在黑名单里
                                                blocked_names = ", ".join(blocked)
                                                self._log(f"🚧 [{code}] 全员黑名单拦截：所有主演 [{blocked_names}] 皆被封杀，已丢弃！", level="warn")
                                                return
                                            else:
                                                # 存在非黑名单的其他演员（陌生人），手下留情
                                                strangers = [a for a in actor_names if a not in blocked]
                                                stranger_names = ", ".join(strangers)
                                                blocked_names = ", ".join(blocked)
                                                self._log(f"💡 [{code}] 多人共演豁免：虽然含黑名单 [{blocked_names}]，但存在共演 [{stranger_names}]，放行下载。", level="info")
                                                
                                await session.commit() # Ensure any avatar updates are saved even if not blocked/whitelisted
                        
                        async with sem:
                            if self.stop_requested: return
                            if downloaded_count >= limit:
                                self._log("！！！已达到每日下载配额，正在停止当前批次任务！！！")
                                self.stop_requested = True
                                return
                                
                            self._log(f"[并发线程] 正在处理: {code}")
                            
                            result = await self._download_attachments(post_url, code, save_path, config)
                            
                            if result == "SUCCESS":
                                async with db_lock:
                                    downloaded_count += 1
                                    downloaded_codes.add(code)
                                    await self.save_record(session, section_key, code, title, post_url)
                                msg = f"✅ [{code}] 成功入库" + (" (画质已升档)" if is_upgrade else "")
                                self._log(msg)
                            elif result == "QUOTA_LIMIT":
                                self._log("！！！触发论坛防御：配额或次数已满，强制停止！！！", level="error")
                                self.stop_requested = True
                            elif result == "CF_BLOCKED":
                                self._log(f"❌ [{code}] 失败跳过：详情页被 CF 盾拦截。", level="error")
                            else:
                                if result == "NO_ATTACHMENT": err_msg = "当前帖子中未找到任何附件下载链接"
                                elif result.startswith("HTTP_ERROR_"): err_msg = f"访问详情页被拒绝 ({result})"
                                elif result.startswith("DL_HTTP_ERROR_"): err_msg = f"附件下载被拒绝 ({result})"
                                elif result == "TIMEOUT": err_msg = "纯代码网络引擎请求超时，可能代理波动"
                                elif result == "NO_VALID_DOWNLOAD": err_msg = "找到了附件链接，但所有的下载尝试均失败"
                                elif result.startswith("ERR:"): err_msg = f"网络/解析异常 ({result[4:]})"
                                else: err_msg = f"未知异常 ({result})"
                                
                                self._log(f"❌ [{code}] 失败跳过：{err_msg}", level="error")
                            
                            await asyncio.sleep(random.uniform(1.0, 3.0))

                    # 并发执行当前页的所有任务
                    await asyncio.gather(*(process_task(t) for t in tasks))

                if not self.stop_requested:
                    page_num += 1
                else:
                    break
            
            # 任务结束，如果是 archive 模式，保存高水位线
            if mode == "archive":
                current_history = int(config.get('history_page', 1))
                if page_num > current_history:
                    from core.utils import save_config, load_config
                    full_config = load_config()
                    if "sections" not in full_config: full_config["sections"] = {}
                    if section_key not in full_config["sections"]: full_config["sections"][section_key] = {}
                    full_config["sections"][section_key]["history_page"] = str(page_num)
                    save_config(full_config)
                    self._log(f"⛏️ 深度考古完成，历史最高水位线已更新至第 {page_num} 页。")

            self._log(f"任务结束。")
        except Exception as e:
            self._log(f"崩溃: {e}")
            logger.exception("Spider task crashed")

    async def _download_attachments(self, detail_url: str, code: str, save_path: str, config: Dict[str, Any]) -> str:
        if not self.page: return "FAILED"
        import httpx
        import urllib.parse

        try:
            cookies_dict = self.page.cookies().as_dict()
        except TypeError:
            # 兼容老版本 DrissionPage
            cookies_list = self.page.cookies(as_dict=False)
            cookies_dict = {c['name']: c['value'] for c in cookies_list}
            
        headers = {
            "User-Agent": self.page.user_agent,
            "Referer": "https://x999x.me/forum.php"
        }

        try:
            async with httpx.AsyncClient(cookies=cookies_dict, headers=headers, verify=False, timeout=25.0) as client:
                await asyncio.sleep(random.uniform(1.0, 2.5)) # 并发前微调延迟
                
                # 1. 纯代码并发获取帖子详情页
                detail_url_full = detail_url if detail_url.startswith('http') else urllib.parse.urljoin("https://x999x.me/", detail_url)
                resp = await client.get(detail_url_full, follow_redirects=True)
                
                if resp.status_code != 200:
                    return f"HTTP_ERROR_{resp.status_code}"
                    
                html_text = resp.text
                
                # 校验CF盾拦截
                if "Just a moment" in html_text or "cf-turnstile" in html_text:
                    return "CF_BLOCKED"
                
                # 2. 正则提取附件链接
                import html
                hrefs = re.findall(r'href=["\']([^"\']*mod=attachment[^"\']*)["\']', html_text)
                if not hrefs:
                    exts = ['.torrent', '.zip', '.rar', '.7z', '.tar', '.gz', '.txt']
                    all_hrefs = re.findall(r'href=["\']([^"\']+)["\']', html_text)
                    hrefs = [h for h in all_hrefs if any(ext in h.lower() for ext in exts)]
                
                if not hrefs:
                    return "NO_ATTACHMENT"
                    
                # 解码 HTML 实体，将 &amp; 还原为 &，否则参数无法被服务器识别
                hrefs = [html.unescape(h) for h in hrefs]
                
                # 3. 纯代码极速下载真实附件
                for href in hrefs:
                    try:
                        download_url = href if href.startswith('http') else urllib.parse.urljoin("https://x999x.me/", href)
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                        
                        dl_resp = await client.get(download_url, follow_redirects=True)
                        if dl_resp.status_code == 200:
                            # 校验是否超配额 (以二进制方式查找关键字)
                            if any(kw in dl_resp.content for kw in [b"\xe5\xb7\xb2\xe8\xb6\x85\xe5\x87\xba", b"\xe7\xb8\xbd\xe8\xa8\x88", b"\xe6\x9d\x83\xe9\x99\x90", b"\xe6\xac\xa1\xe6\x95\xb0\xe5\xb7\xb2\xe6\xbb\xa1"]): # UTF-8 编码的 "已超出", "總計", "权限", "次数已满"
                                return "QUOTA_LIMIT"

                            content_head = dl_resp.content[:50]
                            ext = ""
                            
                            # 方案二：穿透检测真实文件魔数 (Magic Number)
                            if content_head.startswith(b'Rar!\x1a\x07'):
                                ext = ".rar"
                            elif content_head.startswith(b'PK\x03\x04'):
                                ext = ".zip"
                            elif content_head.startswith(b'7z\xbc\xaf\x27\x1c'):
                                ext = ".7z"
                            elif content_head.startswith(b'd8:announce') or content_head.startswith(b'd4:info') or b':announce' in content_head:
                                ext = ".torrent"
                            else:
                                # 魔数不匹配任何已知压缩包或种子，说明大概率下载到了伪装成 200 的 HTML 报错页
                                debug_file = os.path.join(save_path, f"debug_{code}.html")
                                with open(debug_file, "wb") as f:
                                    f.write(dl_resp.content)
                                logger.error(f"[{code}] Invalid content dumped to {debug_file}")
                                return "INVALID_FILE_CONTENT"
                            
                            safe_code = code.replace(":", "_").replace(" ", "_")
                            filename = f"{safe_code}{ext}"
                            file_path = os.path.join(save_path, filename)
                            
                            with open(file_path, "wb") as f:
                                f.write(dl_resp.content)
                            
                            return "SUCCESS"
                        else:
                            return f"DL_HTTP_ERROR_{dl_resp.status_code}"
                    except httpx.TimeoutException:
                        continue # 尝试下一个链接
                    except Exception as e:
                        logger.error(f"HTTPX File Download failed for {code}: {e}")
                        continue
                        
                return "NO_VALID_DOWNLOAD"
                
        except httpx.TimeoutException:
            return "TIMEOUT"
        except httpx.RequestError as e:
            logger.error(f"HTTPX Request Error for {code}: {e}")
            return f"ERR:{type(e).__name__}"
        except Exception as e:
            logger.error(f"HTTPX Detail Fetch failed for {code}: {e}")
            return f"ERR:{type(e).__name__}"

    def stop(self):
        self.stop_requested = True
