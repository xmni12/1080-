from fastapi import APIRouter, BackgroundTasks
from backend.schemas import TaskRequest, RenameRequest
from backend.services.task_manager import task_manager
from backend.services.rename_service import rename_service

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

@router.post("/spider")
async def trigger_spider(request: TaskRequest, background_tasks: BackgroundTasks):
    """
    触发后台爬虫任务
    """
    background_tasks.add_task(task_manager.run_discuz_spider, request.section)
    return {"status": "started", "section": request.section}

@router.post("/stop")
async def stop_spider(request: TaskRequest = None):
    """
    停止爬虫任务
    """
    section = request.section if request else None
    result = task_manager.stop_spider(section)
    return result

@router.post("/rename")
async def trigger_rename(request: RenameRequest, background_tasks: BackgroundTasks):
    """
    触发后台智能重命名识别任务
    """
    background_tasks.add_task(
        rename_service.run_rename_task, 
        request.files, 
        request.rules, 
        request.threads
    )
    return {"status": "started"}
