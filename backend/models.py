from datetime import datetime
from sqlalchemy import String, DateTime, Index, Boolean
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

class AvMetadata(Base):
    __tablename__ = "av_metadata"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True, comment="核心番号")
    actor: Mapped[str] = mapped_column(String(255), nullable=True, comment="演员名称")
    cover_url: Mapped[str] = mapped_column(String(500), nullable=True, comment="封面图链接")
    scraped_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="刮削时间")

class BlacklistActor(Base):
    __tablename__ = "blacklist_actors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, comment="女优名称")
    aliases: Mapped[str] = mapped_column(String(500), default="", server_default="", comment="曾用名/别名(逗号分隔)")
    avatar_url: Mapped[str] = mapped_column(String(500), nullable=True, comment="头像URL")
    added_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="添加时间")

class WhitelistActor(Base):
    __tablename__ = "whitelist_actors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, comment="女优名称")
    aliases: Mapped[str] = mapped_column(String(500), default="", server_default="", comment="曾用名/别名(逗号分隔)")
    avatar_url: Mapped[str] = mapped_column(String(500), nullable=True, comment="头像URL")
    added_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="添加时间")
