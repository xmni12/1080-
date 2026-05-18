from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from typing import Optional
from datetime import datetime

from backend.database import get_db
from backend.models import TitleBlocklist
from backend.schemas import PaginatedTitleBlocklistResponse, AddTitleBlocklistRequest, DeleteRequest

router = APIRouter(prefix="/api/title_blocklist", tags=["title_blocklist"])

@router.get("/", response_model=PaginatedTitleBlocklistResponse)
async def get_title_blocklist(
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100000),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(TitleBlocklist)
    
    if search:
        stmt = stmt.where(TitleBlocklist.keyword.ilike(f"%{search}%"))
        
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0
    
    stmt = stmt.order_by(TitleBlocklist.added_time.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    records = result.scalars().all()
    
    return {"total": total, "items": records}

@router.post("/add")
async def add_title_blocklist(request: AddTitleBlocklistRequest, db: AsyncSession = Depends(get_db)):
    keywords = [k.strip() for k in request.keywords.replace('，', ',').split(',') if k.strip()]
    added_count = 0
    
    # Python-level deduplication
    keywords = list(dict.fromkeys(keywords))
    
    for keyword in keywords:
        stmt = select(TitleBlocklist).where(TitleBlocklist.keyword == keyword)
        result = await db.execute(stmt)
        if not result.scalar_one_or_none():
            new_record = TitleBlocklist(keyword=keyword)
            db.add(new_record)
            added_count += 1
            
    if added_count > 0:
        await db.commit()
        
    return {"status": "success", "added": added_count}

@router.post("/delete")
async def delete_title_blocklist(request: DeleteRequest, db: AsyncSession = Depends(get_db)):
    if not request.ids:
        return {"status": "success", "deleted": 0}
    stmt = delete(TitleBlocklist).where(TitleBlocklist.id.in_(request.ids))
    result = await db.execute(stmt)
    await db.commit()
    return {"status": "success", "deleted": result.rowcount}
