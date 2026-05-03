import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db

@pytest.mark.asyncio
async def test_get_db_session():
    """验证 get_db 能够产生一个 AsyncSession 实例"""
    async_gen = get_db()
    session = await async_gen.__anext__()
    try:
        assert isinstance(session, AsyncSession)
    finally:
        # 尝试关闭生成器以释放资源
        try:
            await async_gen.__anext__()
        except StopAsyncIteration:
            pass
