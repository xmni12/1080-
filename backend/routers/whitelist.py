from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from typing import Optional
from datetime import datetime

from backend.database import get_db
from backend.models import WhitelistActor
from backend.schemas import PaginatedWhitelistResponse, AddWhitelistRequest, DeleteRequest

router = APIRouter(prefix="/api/whitelist", tags=["whitelist"])

@router.get("/", response_model=PaginatedWhitelistResponse)
async def get_whitelist(
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100000),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(WhitelistActor)
    
    if search:
        search_term = f"%{search}%"
        stmt = stmt.where(WhitelistActor.name.ilike(search_term))
        
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0
    
    stmt = stmt.order_by(WhitelistActor.added_time.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    actors = result.scalars().all()
    
    return {"total": total, "items": actors}

@router.post("/add")
async def add_whitelist(request: AddWhitelistRequest, db: AsyncSession = Depends(get_db)):
    added = 0
    skipped = 0
    raw_lines = [n.strip() for n in request.names.split('\n') if n.strip()]
    
    unique_names = {}
    for line in raw_lines:
        parts = [p.strip() for p in line.split(',') if p.strip()]
        if not parts:
            continue
        primary_name = parts[0]
        aliases = ",".join(parts[1:])
        
        if primary_name not in unique_names:
            unique_names[primary_name] = aliases
        else:
            skipped += 1

    for name, aliases in unique_names.items():
        stmt = select(WhitelistActor).where(WhitelistActor.name == name)
        result = await db.execute(stmt)
        actor = result.scalar_one_or_none()
        if not actor:
            new_actor = WhitelistActor(name=name, aliases=aliases, added_time=datetime.now())
            db.add(new_actor)
            added += 1
        else:
            if aliases and actor.aliases != aliases:
                actor.aliases = aliases
            skipped += 1
    await db.commit()
    return {"status": "success", "added": added, "skipped": skipped}

@router.post("/delete")
async def delete_whitelist(request: DeleteRequest, db: AsyncSession = Depends(get_db)):
    if not request.ids:
        return {"status": "success", "deleted": 0}
    stmt = delete(WhitelistActor).where(WhitelistActor.id.in_(request.ids))
    result = await db.execute(stmt)
    await db.commit()
    return {"status": "success", "deleted": result.rowcount}
