from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List

from backend.database import get_db
from backend.models import BlacklistActor, AvMetadata
from backend.schemas import RecognizeRequest, RecognizeResponse, BlacklistActorResponse, AddBlacklistRequest
from backend.services.avbase_service import avbase_service
from core.utils import extract_code

router = APIRouter(prefix="/api/lab", tags=["lab"])

@router.get("/blacklist", response_model=List[BlacklistActorResponse])
async def get_blacklist(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BlacklistActor).order_by(BlacklistActor.added_time.desc()))
    return result.scalars().all()

@router.post("/blacklist", response_model=BlacklistActorResponse)
async def add_blacklist(request: AddBlacklistRequest, db: AsyncSession = Depends(get_db)):
    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    
    stmt = select(BlacklistActor).where(BlacklistActor.name == name)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
         raise HTTPException(status_code=400, detail="Actor already in blacklist")
         
    actor = BlacklistActor(name=name)
    db.add(actor)
    await db.commit()
    return actor

@router.delete("/blacklist/{name}")
async def remove_blacklist(name: str, db: AsyncSession = Depends(get_db)):
    stmt = delete(BlacklistActor).where(BlacklistActor.name == name)
    result = await db.execute(stmt)
    await db.commit()
    return {"status": "success", "deleted": result.rowcount}

@router.post("/recognize", response_model=RecognizeResponse)
async def recognize_file(request: RecognizeRequest, db: AsyncSession = Depends(get_db)):
    code = extract_code(request.filename)
    if not code:
        raise HTTPException(status_code=400, detail="未在文件名中发现有效番号")
        
    # 先查本地缓存档案
    stmt = select(AvMetadata).where(AvMetadata.code == code)
    result = await db.execute(stmt)
    metadata = result.scalar_one_or_none()
    
    if metadata:
        return RecognizeResponse(
            code=metadata.code,
            actor=metadata.actor or "未知",
            cover_url=metadata.cover_url or ""
        )
        
    # 本地没有，启动后端的浏览器影分身刮削引擎
    scraped_data = await avbase_service.scrape_avbase(code)
    
    if not scraped_data:
        raise HTTPException(status_code=404, detail="AVBase 刮削失败或未找到数据")
        
    # 保存到本地缓存
    new_metadata = AvMetadata(
        code=code,
        actor=scraped_data.get('actor', ''),
        cover_url=scraped_data.get('cover_url', '')
    )
    db.add(new_metadata)
    await db.commit()
    
    return RecognizeResponse(
        code=code,
        actor=new_metadata.actor or "未知",
        cover_url=new_metadata.cover_url or ""
    )