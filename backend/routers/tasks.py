from fastapi import APIRouter, BackgroundTasks
from backend.schemas import TaskRequest
from backend.services.task_manager import task_manager

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

@router.post("/spider")
async def trigger_spider(request: TaskRequest, background_tasks: BackgroundTasks):
    """
    触发后台爬虫任务
    """
    background_tasks.add_task(task_manager.run_spider_mock, request.section)
    return {"status": "started", "section": request.section}
