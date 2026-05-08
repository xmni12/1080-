import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from core.utils import load_config
from backend.services.task_manager import task_manager

logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.jobs = {}

    def setup_jobs(self):
        """
        根据 config_v4.json 挂载定时任务
        """
        config = load_config()
        sections = config.get("sections", {})
        
        # 清理旧任务
        for job_id in list(self.jobs.keys()):
            self.scheduler.remove_job(job_id)
            del self.jobs[job_id]

        for section_key, s_config in sections.items():
            if s_config.get("timer_enabled"):
                timer_time = s_config.get("timer_time", "03:00")
                try:
                    hour, minute = map(int, timer_time.split(':'))
                    job_id = f"spider_{section_key}"
                    
                    # 包装异步方法
                    async def run_job(sk=section_key):
                        logger.info(f"Cron triggered for {sk} (mode: new)")
                        await task_manager.run_discuz_spider(sk, mode="new")
                        
                    self.scheduler.add_job(
                        run_job, 
                        'cron', 
                        hour=hour, 
                        minute=minute, 
                        id=job_id,
                        replace_existing=True
                    )
                    self.jobs[job_id] = True
                    logger.info(f"✅ 定时任务挂载成功: {section_key} 每天 {timer_time} 执行")
                except Exception as e:
                    logger.error(f"❌ 解析 {section_key} 定时配置失败: {e}")

    def start(self):
        self.setup_jobs()
        self.scheduler.start()
        logger.info("APScheduler engine started.")

    def stop(self):
        self.scheduler.shutdown(wait=False)

scheduler_service = SchedulerService()
