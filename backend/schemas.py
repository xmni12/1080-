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

from typing import List

class PaginatedRecordResponse(BaseModel):
    total: int
    items: List[RecordResponse]

class ManualEntryRequest(BaseModel):
    codes: str
    section: str

class DeleteRequest(BaseModel):
    ids: list[int]

class TaskRequest(BaseModel):
    section: str
    mode: str = "new" # new or archive

class QueueRemoveRequest(BaseModel):
    section: str
    mode: str

class RenameRequest(BaseModel):
    files: list[str]
    rules: list[str]
    threads: int = 3

class SectionSettings(BaseModel):
    start_page: int = 1
    history_page: int = 1
    save_path: str = ""
    timer_enabled: bool = False
    timer_time: str = "03:00"
    simulate_human: bool = True
    daily_limit: Optional[int] = None
    quick_scan_depth: Optional[int] = 10

class GlobalSettings(BaseModel):
    sections: dict[str, SectionSettings]
    hide_browser: bool = False
    spider_threads: int = 1

class BlacklistActorResponse(BaseModel):
    id: int
    name: str
    added_time: datetime

    model_config = ConfigDict(from_attributes=True)

class PaginatedBlacklistResponse(BaseModel):
    total: int
    items: List[BlacklistActorResponse]

class AddBlacklistRequest(BaseModel):
    names: str
