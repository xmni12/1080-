from fastapi import APIRouter, BackgroundTasks
from backend.schemas import TaskRequest, QueueRemoveRequest
from backend.services.task_manager import task_manager

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

@router.get("/queue")
async def get_queue():
    """
    获取当前排队和运行中的任务状态
    """
    return await task_manager.get_queue_status()

@router.post("/queue/remove")
async def remove_queued_task(request: QueueRemoveRequest):
    """
    从队列中移除任务
    """
    removed = await task_manager.remove_queued_task(request.section, request.mode)
    return {"status": "success", "removed": removed}

@router.post("/spider")
async def trigger_spider(request: TaskRequest, background_tasks: BackgroundTasks):
    """
    触发后台爬虫任务
    """
    background_tasks.add_task(task_manager.run_discuz_spider, request.section, request.mode)
    return {"status": "started", "section": request.section, "mode": request.mode}

@router.post("/stop")
async def stop_spider(request: TaskRequest = None):
    """
    停止爬虫任务
    """
    section = request.section if request else None
    result = task_manager.stop_spider(section)
    return result

@router.post("/cf_clearance")
async def trigger_cf_clearance(background_tasks: BackgroundTasks):
    """
    触发独立的获取 CF 绿卡任务
    """
    background_tasks.add_task(task_manager.get_cf_clearance)
    return {"status": "started"}

@router.post("/authorize")
async def trigger_authorize(background_tasks: BackgroundTasks):
    """
    触发独立的账号登录授权任务
    """
    background_tasks.add_task(task_manager.login_authorize)
    return {"status": "started"}

@router.post("/sandbox")
async def trigger_sandbox(background_tasks: BackgroundTasks):
    """
    触发独立的自由沙盒浏览器
    """
    background_tasks.add_task(task_manager.sandbox_browser)
    return {"status": "started"}
