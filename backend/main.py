from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import records, tasks, websocket, settings, lab
from backend.database import engine, Base
from backend.services.scheduler_service import scheduler_service
from backend.services.task_manager import task_manager
from backend import models

app = FastAPI(title="DiscuzSpider API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await task_manager.start_worker()
    scheduler_service.start()

app.include_router(records.router)
app.include_router(tasks.router)
app.include_router(websocket.router)
app.include_router(settings.router)
app.include_router(lab.router)

@app.get("/")
async def read_root():
    return {"status": "online", "message": "DiscuzSpider API"}
