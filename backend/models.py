from datetime import datetime
from sqlalchemy import String, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from backend.database import Base

class DownloadRecord(Base):
    __tablename__ = "download_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    section: Mapped[str] = mapped_column(String(100), index=True, comment="版块名称")
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True, comment="番号/唯一标识")
    download_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="下载时间")
    post_url: Mapped[str] = mapped_column(String(255), comment="帖子链接")
    title: Mapped[str] = mapped_column(String(255), comment="帖子标题")

    def __repr__(self) -> str:
        return f"<DownloadRecord(code={self.code}, section={self.section})>"
