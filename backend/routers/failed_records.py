from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from typing import Optional
from datetime import datetime

from backend.database import get_db
from backend.models import FailedRecord
from backend.schemas import PaginatedFailedRecordResponse, DeleteRequest
from backend.services.task_manager import task_manager

router = APIRouter(prefix="/api/failed_records", tags=["failed_records"])

@router.get("/", response_model=PaginatedFailedRecordResponse)
async def get_failed_records(
    section: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(FailedRecord)
    
    if section and section != 'all':
        stmt = stmt.where(FailedRecord.section == section)
        
    if search:
        search_term = f"%{search}%"
        stmt = stmt.where((FailedRecord.code.ilike(search_term)) | (FailedRecord.title.ilike(search_term)))
        
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0
    
    stmt = stmt.order_by(FailedRecord.failed_time.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    records = result.scalars().all()
    
    return {"total": total, "items": records}

@router.post("/delete")
async def delete_failed_records(request: DeleteRequest, db: AsyncSession = Depends(get_db)):
    if not request.ids:
        return {"status": "success", "deleted": 0}
    stmt = delete(FailedRecord).where(FailedRecord.id.in_(request.ids))
    result = await db.execute(stmt)
    await db.commit()
    return {"status": "success", "deleted": result.rowcount}

@router.post("/retry")
async def retry_failed_records(request: DeleteRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """
    重试失败的记录
    获取指定的失败记录，触发该版块的爬虫。
    爬虫只有在真正成功入库后，才会从失败列表中清理掉这些记录。
    """
    if not request.ids:
        return {"status": "success", "retried": 0}
        
    stmt = select(FailedRecord).where(FailedRecord.id.in_(request.ids))
    result = await db.execute(stmt)
    records = result.scalars().all()
    
    retried_count = 0
    # Group by section
    sections_to_run = set()
    for record in records:
        sections_to_run.add(record.section)
        retried_count += 1
        
    for section in sections_to_run:
        background_tasks.add_task(task_manager.run_discuz_spider, section, "archive", True)
        
    # 我们不再主动删除这些失败记录。
    # spider_service.py 在判断下载成功时，会顺手将对应的 FailedRecord 抹除。
    
    return {"status": "success", "retried": retried_count}
