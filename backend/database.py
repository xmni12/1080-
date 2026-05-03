import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator

# 确保 data 目录存在
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

DATABASE_URL = "sqlite+aiosqlite:///./data/spider_v5.db"

# 创建异步引擎
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # 开发环境下打印 SQL 语句
    future=True
)

# 配置异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

# 定义模型基类
class Base(DeclarativeBase):
    pass

# 提供 get_db 异步生成器用于依赖注入
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
