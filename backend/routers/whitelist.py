from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from typing import Optional
from datetime import datetime

from backend.database import get_db
from backend.models import WhitelistActor
from backend.schemas import PaginatedWhitelistResponse, AddWhitelistRequest, DeleteRequest
from backend.services.avbase_client import avbase_client

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
        # Auto-fetch aliases from AVBase
        scraped_aliases = await avbase_client.get_actor_aliases(name)
        combined_aliases_set = set([a.strip() for a in aliases.split(',') if a.strip()])
        for sa in scraped_aliases:
            combined_aliases_set.add(sa.strip())
        final_aliases = ",".join(filter(None, combined_aliases_set))

        stmt = select(WhitelistActor).where(WhitelistActor.name == name)
        result = await db.execute(stmt)
        actor = result.scalar_one_or_none()
        if not actor:
            new_actor = WhitelistActor(name=name, aliases=final_aliases, added_time=datetime.now())
            db.add(new_actor)
            added += 1
        else:
            if final_aliases:
                existing_set = set([a.strip() for a in (actor.aliases or "").split(',') if a.strip()])
                new_set = existing_set.union(combined_aliases_set)
                actor.aliases = ",".join(filter(None, new_set))
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

@router.post("/completion/{actor_name}")
async def start_actor_completion(actor_name: str, db: AsyncSession = Depends(get_db)):
    """
    触发单个演员的全集制霸刮削任务
    """
    from backend.services.avbase_client import avbase_client
    from backend.models import DownloadRecord
    from sqlalchemy import select
    from backend.services.task_manager import task_manager
    import asyncio
    
    # 1. 抓取 AVBase 全集番号
    works = await avbase_client.get_actor_works(actor_name)
    if not works:
        return {"status": "error", "message": f"未能在 AVBase 上找到 [{actor_name}] 的任何作品，或网络受限。"}
        
    all_codes = [w['code'].upper() for w in works]
    
    # 2. 从数据库中查询已拥有的
    stmt = select(DownloadRecord.code).where(DownloadRecord.code.in_(all_codes))
    result = await db.execute(stmt)
    owned_codes = set(result.scalars().all())
    
    # 3. 计算缺失的番号
    missing_codes = [code for code in all_codes if code not in owned_codes]
    
    if not missing_codes:
        return {"status": "success", "message": f"[{actor_name}] 的生涯全集已 100% 存在于你的数据库中，无需补全！"}
        
    # 4. 派发给特遣队
    asyncio.create_task(task_manager.run_completion_search(missing_codes))
    
    return {
        "status": "success", 
        "total": len(all_codes),
        "owned": len(owned_codes),
        "missing": len(missing_codes),
        "message": f"已将 {len(missing_codes)} 个缺失番号投入补全队列！"
    }
