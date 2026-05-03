from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class RecordBase(BaseModel):
    section: str
    code: str
    post_url: str
    title: str

class RecordResponse(RecordBase):
    id: int
    download_time: datetime

    model_config = ConfigDict(from_attributes=True)

class TaskRequest(BaseModel):
    section: str
