import os
import shutil
import logging
from sqlalchemy import text
from backend.database import engine

logger = logging.getLogger(__name__)

class CleanupService:
    def __init__(self):
        self.project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
    async def execute_cleanup(self):
        """
        执行全面的系统深度清理
        """
        logger.info("🧹 正在启动系统深度清理与垃圾回收程序...")
        results = []
        
        # 1. 清理日志文件
        try:
            logs_dir = os.path.join(self.project_dir, 'logs')
            if os.path.exists(logs_dir):
                cleared_logs = 0
                for filename in os.listdir(logs_dir):
                    if filename.endswith(".log"):
                        file_path = os.path.join(logs_dir, filename)
                        # Open and truncate the file instead of deleting, 
                        # to prevent issues with processes that are currently writing to it.
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.truncate()
                        cleared_logs += 1
                msg = f"已清空 {cleared_logs} 个日志文件。"
                logger.info(msg)
                results.append(msg)
        except Exception as e:
            logger.error(f"清理日志文件失败: {e}")
            results.append(f"清理日志失败: {e}")

        # 2. 精准清理浏览器无用缓存 (保留 Local Storage 和 Cookies)
        try:
            profile_dir = os.path.join(self.project_dir, 'data', 'browser_profile', 'Default')
            if os.path.exists(profile_dir):
                # 需要被删除的无用缓存子目录列表
                cache_dirs = [
                    'Cache', 
                    'Code Cache', 
                    'DawnCache', 
                    'GPUCache', 
                    'Service Worker\\CacheStorage',
                    'Service Worker\\ScriptCache'
                ]
                deleted_size = 0
                for cache_sub in cache_dirs:
                    target_path = os.path.join(profile_dir, cache_sub)
                    if os.path.exists(target_path):
                        # Calculate size before deletion
                        for dirpath, _, filenames in os.walk(target_path):
                            for f in filenames:
                                fp = os.path.join(dirpath, f)
                                if not os.path.islink(fp):
                                    deleted_size += os.path.getsize(fp)
                        shutil.rmtree(target_path, ignore_errors=True)
                
                mb_freed = deleted_size / (1024 * 1024)
                msg = f"已释放浏览器网页缓存约 {mb_freed:.2f} MB。"
                logger.info(msg)
                results.append(msg)
            else:
                results.append("未发现浏览器缓存目录。")
        except Exception as e:
            logger.error(f"清理浏览器缓存失败: {e}")
            results.append(f"清理浏览器缓存失败: {e}")

        # 3. SQLite 数据库碎片整理 (VACUUM)
        try:
            db_path = os.path.join(self.project_dir, 'data', 'spider_v5.db')
            if os.path.exists(db_path):
                size_before = os.path.getsize(db_path)
                
                # VACUUM 必须在 transaction 外执行
                async with engine.connect() as conn:
                    # 对于 sqlite 的 asyncio 驱动，我们先设置为 autocommit 模式
                    await conn.execution_options(isolation_level="AUTOCOMMIT").execute(text("VACUUM"))
                    
                size_after = os.path.getsize(db_path)
                freed_kb = (size_before - size_after) / 1024
                
                if freed_kb > 0:
                    msg = f"数据库压缩完成，释放了 {freed_kb:.2f} KB 的碎片空间。"
                else:
                    msg = "数据库运行良好，无需释放碎片。"
                    
                logger.info(msg)
                results.append(msg)
        except Exception as e:
            logger.error(f"数据库 VACUUM 失败: {e}")
            results.append(f"数据库 VACUUM 失败: {e}")
            
        return results

cleanup_service = CleanupService()
