from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
import asyncio

from backend.database import get_db, AsyncSessionLocal
from backend.models import BlacklistActor, AvMetadata
from backend.schemas import RecognizeRequest, RecognizeBatchRequest, RecognizeResponse, BlacklistActorResponse, AddBlacklistRequest
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

from backend.routers.websocket import manager

@router.post("/recognize", response_model=RecognizeResponse)
async def recognize_file(request: RecognizeRequest, db: AsyncSession = Depends(get_db)):
    code = extract_code(request.filename)
    if not code:
        raise HTTPException(status_code=400, detail="未在文件名中发现有效番号")
        
    await manager.broadcast_json({"type": "lab_status", "message": f"👉 开始处理: 识别到番号 [{code}]，正在核对本地档案库..."})
        
    # 先查本地缓存档案
    stmt = select(AvMetadata).where(AvMetadata.code == code)
    result = await db.execute(stmt)
    metadata = result.scalar_one_or_none()
    
    if metadata:
        await manager.broadcast_json({"type": "lab_status", "message": f"✅ 本地档案命中，瞬间返回结果！"})
        return RecognizeResponse(
            code=metadata.code,
            actor=metadata.actor or "未知",
            cover_url=metadata.cover_url or ""
        )
        
    await manager.broadcast_json({"type": "lab_status", "message": f"⏳ 本地无记录，即将呼叫 AVBase 隐身刮削引擎..."})
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

async def _process_batch(filenames: List[str]):
    total = len(filenames)
    await manager.broadcast_json({"type": "lab_status", "message": f"📦 收到 {total} 个文件的批量识别请求，加入处理队列..."})
    
    for idx, filename in enumerate(filenames):
        await asyncio.sleep(1)
        code = extract_code(filename)
        if not code:
            await manager.broadcast_json({
                "type": "lab_result", 
                "success": False, 
                "filename": filename,
                "error": "未在文件名中发现有效番号",
                "code": "未知"
            })
            continue

        await manager.broadcast_json({"type": "lab_status", "message": f"👉 [{idx+1}/{total}] 正在处理: [{code}]..."})
        
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(AvMetadata).where(AvMetadata.code == code)
                result = await session.execute(stmt)
                metadata = result.scalar_one_or_none()
                
                if metadata:
                    await manager.broadcast_json({"type": "lab_status", "message": f"✅ [{code}] 本地档案命中！"})
                    await manager.broadcast_json({
                        "type": "lab_result",
                        "success": True,
                        "filename": filename,
                        "data": {
                            "code": metadata.code,
                            "actor": metadata.actor or "未知",
                            "cover_url": metadata.cover_url or ""
                        }
                    })
                    continue
                    
                await manager.broadcast_json({"type": "lab_status", "message": f"⏳ [{code}] 本地无记录，呼叫 AVBase 引擎..."})
                scraped_data = await avbase_service.scrape_avbase(code)
                
                if not scraped_data:
                    await manager.broadcast_json({
                        "type": "lab_result", 
                        "success": False, 
                        "filename": filename,
                        "error": "AVBase 刮削失败或未找到数据",
                        "code": code
                    })
                    continue
                    
                new_metadata = AvMetadata(
                    code=code,
                    actor=scraped_data.get('actor', ''),
                    cover_url=scraped_data.get('cover_url', '')
                )
                session.add(new_metadata)
                await session.commit()
                
                await manager.broadcast_json({
                    "type": "lab_result",
                    "success": True,
                    "filename": filename,
                    "data": {
                        "code": code,
                        "actor": new_metadata.actor or "未知",
                        "cover_url": new_metadata.cover_url or ""
                    }
                })
        except Exception as e:
            await manager.broadcast_json({
                "type": "lab_result", 
                "success": False, 
                "filename": filename,
                "error": f"系统异常: {str(e)}",
                "code": code
            })
            
    await manager.broadcast_json({"type": "lab_status", "message": f"🎉 批量识别任务 ({total}个) 全部处理完成！"})

@router.post("/recognize_batch")
async def recognize_batch(request: RecognizeBatchRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(_process_batch, request.filenames)
    return {"status": "queued", "count": len(request.filenames)}