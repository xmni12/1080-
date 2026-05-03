from fastapi import FastAPI
from backend.routers import records, tasks
from backend.database import engine, Base
from backend import models  # 导入模型以注册到 Base.metadata

app = FastAPI(title="DiscuzSpider API")

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.include_router(records.router)
app.include_router(tasks.router)

@app.get("/")
async def read_root():
    return {"status": "online", "message": "DiscuzSpider API"}
