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
    whitelist_save_path: Optional[str] = ""
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
    aliases: str = ""
    avatar_url: Optional[str] = None
    added_time: datetime

    model_config = ConfigDict(from_attributes=True)

class FailedRecordResponse(BaseModel):
    id: int
    section: str
    code: str
    title: str
    post_url: str
    reason: str
    failed_time: datetime

    model_config = ConfigDict(from_attributes=True)

class PaginatedFailedRecordResponse(BaseModel):
    total: int
    items: List[FailedRecordResponse]

class PaginatedBlacklistResponse(BaseModel):
    total: int
    items: List[BlacklistActorResponse]

class AddBlacklistRequest(BaseModel):
    names: str

class WhitelistActorResponse(BaseModel):
    id: int
    name: str
    aliases: str = ""
    avatar_url: Optional[str] = None
    added_time: datetime

    model_config = ConfigDict(from_attributes=True)

class PaginatedWhitelistResponse(BaseModel):
    total: int
    items: List[WhitelistActorResponse]

class AddWhitelistRequest(BaseModel):
    names: str

class SyncCompletionRequest(BaseModel):
    url: str

class SearchCompletionRequest(BaseModel):
    codes: List[str]
