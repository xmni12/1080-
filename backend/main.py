from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import records, tasks, websocket, settings, blacklist, whitelist, failed_records, title_blocklist
from backend.database import engine, Base
from backend.services.scheduler_service import scheduler_service
from backend.services.task_manager import task_manager
from backend import models
import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="DiscuzSpider API")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    body = await request.body()
    logger.error(f"Validation Error: {exc.errors()}")
    logger.error(f"Request Body: {body.decode()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "body": body.decode()},
    )

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
app.include_router(blacklist.router)
app.include_router(whitelist.router)
app.include_router(failed_records.router)
app.include_router(title_blocklist.router)

@app.get("/")
async def read_root():
    return {"status": "online", "message": "DiscuzSpider API"}
