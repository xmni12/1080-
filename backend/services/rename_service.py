import os
import re
import concurrent.futures
import logging
import asyncio
from typing import List, Dict, Any, Optional
from DrissionPage import ChromiumPage, ChromiumOptions
from core.avbase_spider import AvbaseSpider
from backend.routers.websocket import manager

logger = logging.getLogger(__name__)

class RenameService:
    def __init__(self, page: Optional[ChromiumPage] = None):
        self._page = page
        self.stop_requested = False

    def _get_page(self):
        """延迟初始化浏览器页面"""
        if not self._page:
            try:
                co = ChromiumOptions()
                co.set_argument('--no-window-focus')
                co.set_argument('--disable-notifications')
                # 后端服务通常建议静默运行，但为了兼容性暂不强制 headless
                # co.set_argument('--headless') 
                self._page = ChromiumPage(co)
            except Exception as e:
                logger.error(f"Failed to initialize ChromiumPage: {e}")
                raise e
        return self._page

    async def run_rename_task(self, files: List[str], rules: List[str], threads: int):
        self.stop_requested = False
        total = len(files)
        completed = 0
        
        try:
            page = self._get_page()
        except Exception as e:
            await manager.broadcast_json({"type": "log", "message": f"错误: 浏览器初始化失败 - {str(e)}"})
            return

        loop = asyncio.get_running_loop()
        
        def process_file(file_path):
            if self.stop_requested:
                return None
            tab = None
            try:
                orig_name = os.path.basename(file_path)
                search_term = orig_name
                # 应用清理规则
                for rule in rules:
                    r = rule.strip()
                    if r:
                        try:
                            search_term = re.sub(r, "", search_term, flags=re.IGNORECASE)
                        except:
                            search_term = search_term.replace(r, "")
                
                # 移除扩展名进行搜索
                search_term, ext = os.path.splitext(search_term)
                
                tab = page.new_tab()
                spider = AvbaseSpider(tab)
                new_code, img_url, error_msg = spider.search_code(search_term.strip())
                
                if new_code:
                    return {
                        "path": file_path, 
                        "orig_name": orig_name, 
                        "new_code": new_code, 
                        "img_url": img_url, 
                        "new_name": new_code + ext,
                        "status": "success"
                    }
                else:
                    return {
                        "path": file_path, 
                        "orig_name": orig_name, 
                        "status": "failed", 
                        "error": error_msg or "未找到匹配番号"
                    }
            except Exception as e:
                logger.error(f"Error identifying {file_path}: {e}")
                return {
                    "path": file_path, 
                    "orig_name": os.path.basename(file_path), 
                    "status": "error", 
                    "error": str(e)
                }
            finally:
                if tab:
                    try:
                        tab.close()
                    except:
                        pass

        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            # 使用 loop.run_in_executor 配合 asyncio.as_completed 实现非阻塞并发
            tasks = [loop.run_in_executor(executor, process_file, f) for f in files]
            
            for task in asyncio.as_completed(tasks):
                if self.stop_requested:
                    break
                
                try:
                    result = await task
                    completed += 1
                    if result:
                        # 推送进度到 WebSocket
                        await manager.broadcast_json({
                            "type": "rename_progress",
                            "completed": completed,
                            "total": total,
                            "result": result
                        })
                        # 推送日志
                        status_str = "成功" if result.get('status') == 'success' else "失败"
                        msg = f"[{completed}/{total}] {status_str}: {result.get('orig_name')} -> {result.get('new_code') or result.get('error')}"
                        await manager.broadcast_json({"type": "log", "message": msg})
                except Exception as e:
                    logger.error(f"Task execution error: {e}")
                    completed += 1

        await manager.broadcast_json({"type": "log", "message": "智能重命名任务执行完毕。"})

    def stop(self):
        self.stop_requested = True

# 实例化全局服务
rename_service = RenameService()
