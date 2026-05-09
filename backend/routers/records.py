from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, case
from typing import List, Optional
from datetime import datetime, date, time

from backend.database import get_db
from backend.models import DownloadRecord
from backend.schemas import RecordResponse, PaginatedRecordResponse, ManualEntryRequest, DeleteRequest

router = APIRouter(prefix="/api/records", tags=["records"])

@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    # 获取各个版块的总量和今日新增（排除手动录入）
    today_start = datetime.combine(date.today(), time.min)
    
    stmt = select(
        DownloadRecord.section,
        func.count(DownloadRecord.id).label('total'),
        func.sum(case(((DownloadRecord.download_time >= today_start) & (DownloadRecord.title != '[手动录入]'), 1), else_=0)).label('today')
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

@router.get("/trend")
async def get_trend(db: AsyncSession = Depends(get_db)):
    # 获取最近7天的每日抓取量
    from datetime import timedelta
    seven_days_ago = date.today() - timedelta(days=6)
    
    stmt = select(
        func.date(DownloadRecord.download_time).label('date'),
        func.count(DownloadRecord.id).label('count')
    ).where(
        DownloadRecord.download_time >= datetime.combine(seven_days_ago, time.min),
        DownloadRecord.title != '[手动录入]'
    ).group_by(
        func.date(DownloadRecord.download_time)
    ).order_by(
        func.date(DownloadRecord.download_time).asc()
    )
    
    result = await db.execute(stmt)
    rows = result.all()
    
    trend_map = {row[0]: row[1] for row in rows}
    final_data = []
    for i in range(7):
        d = seven_days_ago + timedelta(days=i)
        curr_date_str = d.isoformat()
        final_data.append({
            "name": d.strftime('%m-%d'),
            "count": trend_map.get(curr_date_str, 0)
        })
    return final_data

@router.get("/", response_model=PaginatedRecordResponse)
async def get_records(
    section: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(DownloadRecord)
    
    if section and section != 'all':
        stmt = stmt.where(DownloadRecord.section == section)
        
    if search:
        search_term = f"%{search}%"
        stmt = stmt.where((DownloadRecord.code.ilike(search_term)) | (DownloadRecord.title.ilike(search_term)))
        
    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0
    
    # Paginate
    stmt = stmt.order_by(DownloadRecord.download_time.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    records = result.scalars().all()
    
    return {"total": total, "items": records}

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
