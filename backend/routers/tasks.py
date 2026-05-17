from fastapi import APIRouter, BackgroundTasks
from backend.schemas import TaskRequest, QueueRemoveRequest, SyncCompletionRequest, SearchCompletionRequest
from backend.services.task_manager import task_manager
from backend.services.avbase_client import avbase_client
from backend.services.emby_client import emby_client
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

@router.post("/completion/sync")
async def sync_completion(request: SyncCompletionRequest):
    """
    执行 AVBase 与 Emby 媒体库的双向对账
    """
    # 1. Get works from AVBase
    avbase_data = await avbase_client.get_works_by_talent_url(request.url)
    actor_name = avbase_data.get("actor_name", "未知演员")
    avbase_works = avbase_data.get("works", [])
    
    # 2. Get owned codes from Emby
    owned_codes = await emby_client.get_all_movie_codes()
    
    # 3. Compute missing
    missing_items = []
    for work in avbase_works:
        if work["code"] not in owned_codes:
            missing_items.append(work)
            
    # Sort missing items (simplistic sorting)
    missing_items.sort(key=lambda x: x["code"])
            
    return {
        "status": "success",
        "actor": actor_name,
        "total_works": len(avbase_works),
        "emby_owned": len(avbase_works) - len(missing_items),
        "missing": len(missing_items),
        "missing_items": missing_items
    }

@router.post("/completion/search")
async def search_completion(request: SearchCompletionRequest, background_tasks: BackgroundTasks):
    """
    触发后台针对缺失番号的强行搜索下载任务
    """
    background_tasks.add_task(task_manager.run_completion_search, request.codes)
    return {"status": "started"}

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
