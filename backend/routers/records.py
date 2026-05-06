from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, case
from typing import List, Optional
from datetime import datetime, date, time

from backend.database import get_db
from backend.models import DownloadRecord
from backend.schemas import RecordResponse, ManualEntryRequest, DeleteRequest

router = APIRouter(prefix="/api/records", tags=["records"])

@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    # 获取各个版块的总量和今日新增
    today_start = datetime.combine(date.today(), time.min)
    
    stmt = select(
        DownloadRecord.section,
        func.count(DownloadRecord.id).label('total'),
        func.sum(case((DownloadRecord.download_time >= today_start, 1), else_=0)).label('today')
    ).group_by(DownloadRecord.section)
    
    result = await db.execute(stmt)
    stats = {}
    for row in result.all():
        section = row[0]
        stats[section] = {
            "total": row[1],
            "today": int(row[2]) if row[2] else 0
        }
    
    # 保证四个基础版块都存在
    for sec in ['vr', '4k', 'hd', 'sub']:
        if sec not in stats:
            stats[sec] = {"total": 0, "today": 0}
            
    return stats

@router.get("/", response_model=List[RecordResponse])
async def get_records(
    section: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(DownloadRecord)
    
    if section and section != 'all':
        stmt = stmt.where(DownloadRecord.section == section)
        
    if search:
        search_term = f"%{search}%"
        stmt = stmt.where((DownloadRecord.code.ilike(search_term)) | (DownloadRecord.title.ilike(search_term)))
        
    result = await db.execute(stmt.order_by(DownloadRecord.download_time.desc()).limit(300))
    records = result.scalars().all()
    return records

@router.post("/manual")
async def add_manual_records(request: ManualEntryRequest, db: AsyncSession = Depends(get_db)):
    added = 0
    codes = [c.strip().upper() for c in request.codes.split('\n') if c.strip()]
    for code in codes:
        stmt = select(DownloadRecord).where(DownloadRecord.code == code)
        result = await db.execute(stmt)
        if not result.scalar_one_or_none():
            record = DownloadRecord(
                section=request.section,
                code=code,
                title="[手动录入]",
                post_url="",
                download_time=datetime.now()
            )
            db.add(record)
            added += 1
    await db.commit()
    return {"status": "success", "added": added}

@router.post("/delete")
async def delete_records(request: DeleteRequest, db: AsyncSession = Depends(get_db)):
    if not request.ids:
        return {"status": "success", "deleted": 0}
    stmt = delete(DownloadRecord).where(DownloadRecord.id.in_(request.ids))
    result = await db.execute(stmt)
    await db.commit()
    return {"status": "success", "deleted": result.rowcount}
