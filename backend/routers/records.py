from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from backend.database import get_db
from backend.models import DownloadRecord
from backend.schemas import RecordResponse

router = APIRouter(prefix="/api/records", tags=["records"])

@router.get("/", response_model=List[RecordResponse])
async def get_records(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DownloadRecord).limit(100))
    records = result.scalars().all()
    return records
