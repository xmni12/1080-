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
    获取指定的失败记录，直接进行点对点的精准重新下载。
    """
    if not request.ids:
        return {"status": "success", "retried": 0}
        
    stmt = select(FailedRecord).where(FailedRecord.id.in_(request.ids))
    result = await db.execute(stmt)
    records = result.scalars().all()
    
    if not records:
        return {"status": "success", "retried": 0}
        
    records_data = []
    for r in records:
        records_data.append({
            "id": r.id,
            "section": r.section,
            "code": r.code,
            "title": r.title,
            "post_url": r.post_url
        })
        
    # 将打包好的死链数据交给 task_manager 进行定点爆破
    background_tasks.add_task(task_manager.run_retry_tasks, records_data)
    
    return {"status": "success", "retried": len(records_data)}
