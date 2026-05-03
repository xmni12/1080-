# FastAPI Backend Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the monolithic PySide6 application into a decoupled FastAPI backend architecture, establishing the foundation for a modern web frontend.

**Architecture:** We will create a REST API using FastAPI. The existing `sqlite3` database logic will be wrapped or migrated to SQLAlchemy (we will use SQLAlchemy asyncio with Pydantic for validation). Background tasks will handle the long-running spider and renaming tasks, decoupling them from the HTTP request/response cycle.

**Tech Stack:** FastAPI, Uvicorn, SQLAlchemy (asyncio), Pydantic, Pytest.

### Task 1: Setup Backend Foundation and Dependencies

**Files:**
- Modify: `requirements.txt`
- Create: `backend/__init__.py`
- Create: `backend/main.py`
- Create: `tests/backend/__init__.py`
- Create: `tests/backend/test_main.py`
- Create: `pytest.ini`

- [ ] **Step 1: Write the failing test**

```python
# tests/backend/test_main.py
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "online", "message": "DiscuzSpider API"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/backend/test_main.py -v`
Expected: FAIL with "ModuleNotFoundError" or "FileNotFoundError"

- [ ] **Step 3: Write minimal implementation**

```python
# requirements.txt (Append these at the bottom)
fastapi>=0.100.0
uvicorn>=0.23.0
sqlalchemy>=2.0.0
aiosqlite>=0.19.0
pydantic>=2.0.0
pytest>=7.0.0
httpx>=0.24.0
pytest-asyncio>=0.21.0

# pytest.ini
[pytest]
asyncio_mode = auto
pythonpath = .

# backend/__init__.py
# (Leave empty)

# tests/backend/__init__.py
# (Leave empty)

# backend/main.py
from fastapi import FastAPI

app = FastAPI(title="DiscuzSpider API")

@app.get("/")
async def root():
    return {"status": "online", "message": "DiscuzSpider API"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pip install -r requirements.txt && pytest tests/backend/test_main.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add requirements.txt backend/ tests/ pytest.ini
git commit -m "feat(backend): initialize FastAPI application structure"
```

### Task 2: Implement SQLAlchemy Database Models

**Files:**
- Create: `backend/database.py`
- Create: `backend/models.py`
- Create: `tests/backend/test_database.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/backend/test_database.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.models import DownloadRecord

@pytest.mark.asyncio
async def test_database_connection():
    db_gen = get_db()
    session = await anext(db_gen)
    assert isinstance(session, AsyncSession)
    await session.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/backend/test_database.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Write minimal implementation**

```python
# backend/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./data/spider_v5.db"

engine = create_async_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# backend/models.py
from sqlalchemy import Column, Integer, String, DateTime
from backend.database import Base
from datetime import datetime

class DownloadRecord(Base):
    __tablename__ = "downloads"

    id = Column(Integer, primary_key=True, index=True)
    section = Column(String, index=True)
    code = Column(String, unique=True, index=True)
    download_time = Column(DateTime, default=datetime.utcnow)
    post_url = Column(String, nullable=True)
    title = Column(String, nullable=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/backend/test_database.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/database.py backend/models.py tests/backend/test_database.py
git commit -m "feat(backend): configure SQLAlchemy asyncio models"
```

### Task 3: Pydantic Schemas and Records API

**Files:**
- Create: `backend/schemas.py`
- Create: `backend/routers/__init__.py`
- Create: `backend/routers/records.py`
- Modify: `backend/main.py`
- Create: `tests/backend/test_records.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/backend/test_records.py
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_get_records_empty():
    response = client.get("/api/records/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/backend/test_records.py -v`
Expected: FAIL with 404 Not Found

- [ ] **Step 3: Write minimal implementation**

```python
# backend/schemas.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class RecordBase(BaseModel):
    section: str
    code: str
    post_url: Optional[str] = None
    title: Optional[str] = None

class RecordResponse(RecordBase):
    id: int
    download_time: datetime
    
    class Config:
        from_attributes = True

# backend/routers/__init__.py
# (Leave empty)

# backend/routers/records.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from backend.database import get_db
from backend.models import DownloadRecord
from backend.schemas import RecordResponse

router = APIRouter(prefix="/api/records", tags=["Records"])

@router.get("/", response_model=List[RecordResponse])
async def get_records(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DownloadRecord).limit(100))
    return result.scalars().all()

# backend/main.py (Replace entire file to include router and create tables)
from fastapi import FastAPI
from backend.routers import records
from backend.database import engine, Base

app = FastAPI(title="DiscuzSpider API")

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.include_router(records.router)

@app.get("/")
async def root():
    return {"status": "online", "message": "DiscuzSpider API"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/backend/test_records.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/schemas.py backend/routers/ backend/main.py tests/backend/test_records.py
git commit -m "feat(backend): add records API and Pydantic schemas"
```

### Task 4: Task Manager Scaffold (Spider Trigger)

**Files:**
- Create: `backend/services/__init__.py`
- Create: `backend/services/task_manager.py`
- Create: `backend/routers/tasks.py`
- Modify: `backend/schemas.py`
- Modify: `backend/main.py`
- Create: `tests/backend/test_tasks.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/backend/test_tasks.py
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_start_spider_task():
    response = client.post("/api/tasks/spider", json={"section": "4k"})
    assert response.status_code == 200
    assert response.json()["status"] == "started"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/backend/test_tasks.py -v`
Expected: FAIL 404

- [ ] **Step 3: Write minimal implementation**

```python
# backend/schemas.py (Append to file)
class TaskRequest(BaseModel):
    section: str

# backend/services/__init__.py
# (Leave empty)

# backend/services/task_manager.py
import asyncio

class TaskManager:
    def __init__(self):
        self.active_tasks = {}

    async def run_spider_mock(self, section: str):
        print(f"Spider for {section} started...")
        await asyncio.sleep(2)
        print(f"Spider for {section} finished.")

task_manager = TaskManager()

# backend/routers/tasks.py
from fastapi import APIRouter, BackgroundTasks
from backend.schemas import TaskRequest
from backend.services.task_manager import task_manager

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])

@router.post("/spider")
async def start_spider(request: TaskRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(task_manager.run_spider_mock, request.section)
    return {"status": "started", "section": request.section}

# backend/main.py (Append router inclusion at the bottom, before the root endpoint if you prefer, or just below app.include_router(records.router))
# Note: In standard practice, just insert below the records router:
# from backend.routers import tasks
# app.include_router(tasks.router)
```

**Wait**, to be precise, here is the exact content to replace `backend/main.py` with:
```python
from fastapi import FastAPI
from backend.routers import records, tasks
from backend.database import engine, Base

app = FastAPI(title="DiscuzSpider API")

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.include_router(records.router)
app.include_router(tasks.router)

@app.get("/")
async def root():
    return {"status": "online", "message": "DiscuzSpider API"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/backend/test_tasks.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/ backend/routers/tasks.py backend/main.py backend/schemas.py tests/backend/test_tasks.py
git commit -m "feat(backend): implement background task routing for spider"
```
