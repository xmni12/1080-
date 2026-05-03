from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
from datetime import datetime

from backend.database import get_db
from backend.models import DownloadRecord
from backend.schemas import RecordResponse, ManualEntryRequest, DeleteRequest

router = APIRouter(prefix="/api/records", tags=["records"])

@router.get("/", response_model=List[RecordResponse])
async def get_records(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DownloadRecord).order_by(DownloadRecord.download_time.desc()).limit(300))
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
