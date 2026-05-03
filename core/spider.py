from DrissionPage import ChromiumPage
import time
import os
import re
import random
from .utils import extract_code
from .database import save_code, check_code_exists_in_section

class DiscuzSpider:
    def __init__(self, log_callback, update_codes_callback, downloaded_codes, page_callback, section_key):
        self.log = log_callback
        self.update_codes = update_codes_callback
        self.report_page = page_callback
        self.downloaded_codes = downloaded_codes
        self.section_key = section_key
        self.page = None
        self.stop_requested = False

    def set_browser(self, page_instance):
        self.page = page_instance

    def _human_delay(self, config, min_s=1.5, max_s=4.0):
        if not config.get('simulate_human', True):
            time.sleep(0.5)
            return
        time.sleep(random.uniform(min_s, max_s))

    def _human_scroll(self, config):
        if not config.get('simulate_human', True): return
        try:
            for _ in range(random.randint(1, 3)):
                self.page.scroll.down(random.randint(300, 800))
                time.sleep(random.uniform(0.5, 1.5))
        except: pass

    def run_task(self, config):
        try:
            self.stop_requested = False
            downloaded_count = 0
            limit = config.get('daily_limit', 55)
            start_page = config.get('start_page', 1)
            save_path = config.get('save_path', './downloads')
            section_url = config.get('url')
            if not os.path.exists(save_path): os.makedirs(save_path)
            
            page_num = start_page
            while not self.stop_requested and downloaded_count < limit:
                self.report_page.emit(page_num)
                self.log(f"--- 正在解析第 {page_num} 页 ---")
                self._human_delay(config, 1.0, 3.0)
                self.page.get(f"{section_url}&page={page_num}")
                self._human_delay(config, 3.0, 6.0)
                self._human_scroll(config)
                
                tasks = []
                seen_tids = set()
                for a in self.page.eles('tag:a'):
                    try:
                        href = a.attr('href') or ''
                        if 'viewthread' in href or 'thread-' in href:
                            tid = (re.search(r'tid=(\d+)', href) or re.search(r'thread-(\d+)', href))
                            tid = tid.group(1) if tid else href
                            if tid in seen_tids: continue
                            text = a.text or a.attr('title') or ""
                            code = extract_code(text)
                            if code:
                                tasks.append({'code': code, 'link': href, 'title': text})
                                seen_tids.add(tid)
                    except: continue

                if not tasks: self.log(f"第 {page_num} 页无新番号。")
                else:
                    self.log(f"第 {page_num} 页发现 {len(tasks)} 个潜在番号。")
                    for i, task in enumerate(tasks):
                        if self.stop_requested: break
                        code = task['code']
                        title = task['title']
                        post_url = task['link']
                        
                        # --- 核心联动逻辑：画质优先策略 ---
                        skip_download = False
                        is_upgrade = False
                        
                        # 如果是 4K 版块
                        if self.section_key == '4k':
                            if code in self.downloaded_codes:
                                skip_download = True # 4K 库已经有了，无需处理
                            elif check_code_exists_in_section('hd', code):
                                self.log(f"[检测升级] {code} 在 HD 库已存在，正在升级为 4K...")
                                is_upgrade = True # 标记为升级，不跳过下载
                        
                        # 如果是 HD 版块
                        elif self.section_key == 'hd':
                            if code in self.downloaded_codes or check_code_exists_in_section('4k', code):
                                if check_code_exists_in_section('4k', code):
                                    self.log(f"[避让] {code} 在 4K 库已存在，HD 版块跳过。")
                                skip_download = True
                                
                        # 其他版块常规去重
                        else:
                            if code in self.downloaded_codes: skip_download = True
                        
                        if skip_download: continue
                        
                        self.log(f"[页:{page_num} 进度:{i+1}/{len(tasks)}] 正在处理: {code}")
                        self._human_delay(config, 1.0, 2.5)
                        result = self._download_attachments(post_url, code, save_path, config)
                        
                        if result == "SUCCESS":
                            downloaded_count += 1
                            self.downloaded_codes.add(code)
                            save_code(self.section_key, code, title, post_url)
                            self.update_codes.emit(code)
                            msg = f"成功下载 [{code}]" + (" (画质已升档 ✅)" if is_upgrade else "")
                            self.log(msg)
                        elif result == "QUOTA_LIMIT":
                            self.log("！！！配额耗尽，停止！！！")
                            self.stop_requested = True; break
                        else:
                            self.log(f"[{code}] 失败，停止。")
                            self.stop_requested = True; break
                        self._human_delay(config, 3.0, 7.0)

                if not self.stop_requested: page_num += 1
                else: break
            self.log(f"任务结束。")
        except Exception as e: self.log(f"崩溃: {e}")

    def _download_attachments(self, detail_url, code, save_path, config):
        try:
            self.page.get(detail_url)
            self._human_delay(config, 2.5, 5.0)
            self._human_scroll(config)
            self.page.set.download_path(os.path.abspath(save_path))
            files_before = set(os.listdir(save_path)) if os.path.exists(save_path) else set()
            attach_eles = self.page.eles('css:a[href*="mod=attachment"]')
            if not attach_eles:
                exts = ['.torrent', '.zip', '.rar', '.7z', '.tar', '.gz', '.txt']
                attach_eles = [l for l in self.page.eles('tag:a') if any(ext in (l.attr('href') or '').lower() for ext in exts)]
            if not attach_eles: return "FAILED"
            for att in attach_eles:
                try:
                    self._human_delay(config, 0.5, 1.5)
                    att.click()
                    for _ in range(15): 
                        time.sleep(1)
                        if "mod=attachment" in self.page.url and any(ind in self.page.html for ind in ["已超出", "總計", "权限", "次数已满"]): return "QUOTA_LIMIT"
                        files_now = set(os.listdir(save_path))
                        if [f for f in (files_now - files_before) if not f.endswith(('.tmp', '.crdownload'))]: return "SUCCESS"
                except: continue
            return "FAILED"
        except Exception as e: return "FAILED"

    def stop(self): self.stop_requested = True
