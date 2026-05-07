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

class RenameRequest(BaseModel):
    files: list[str]
    rules: list[str]
    threads: int = 3

class SectionSettings(BaseModel):
    start_page: str = "1"
    history_page: str = "1"
    save_path: str = ""
    timer_enabled: bool = False
    timer_time: str = "03:00"
    simulate_human: bool = True
    daily_limit: Optional[int] = None

class RenameSettings(BaseModel):
    rules: str = ""
    threads: str = "3"

class GlobalSettings(BaseModel):
    sections: dict[str, SectionSettings]
    hide_browser: bool = False
    rename_settings: RenameSettings
    spider_threads: int = 1

class RecognizeRequest(BaseModel):
    filename: str

class RecognizeResponse(BaseModel):
    code: str
    actor: str
    cover_url: str

class BlacklistActorResponse(BaseModel):
    name: str

class AddBlacklistRequest(BaseModel):
    name: str
