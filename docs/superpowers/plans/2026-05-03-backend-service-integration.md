# Backend Service Integration Implementation Plan

> **对于代理工人：** 必须使用子技能：使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans` 来逐项执行此计划。步骤使用复选框 (`- [ ]`) 语法进行跟踪。

**目标：** 将原有的 Discuz 爬虫和智能重命名逻辑迁移至 FastAPI 后端，实现异步化、实时化和配置 API 化。

**架构：** 爬虫逻辑将封装为单例 Service，使用 `AsyncSession` 进行数据库操作。通过 `FastAPI WebSocket` 实现日志的实时下发。配置将存储在数据库或统一的 `config.json` 中并由 API 管理。

**技术栈：** FastAPI, WebSockets, SQLAlchemy (asyncio), DrissionPage, concurrent.futures.

---

### 任务 1：重构 DiscuzSpider 为异步 Service

**文件：**
- 修改：`backend/services/spider_service.py` (从 `core/spider.py` 迁移并重构)
- 修改：`backend/services/task_manager.py` (接入真实爬虫)
- 测试：`tests/backend/test_spider_service.py`

- [ ] **步骤 1：编写失败测试**

```python
# tests/backend/test_spider_service.py
import pytest
from backend.services.task_manager import task_manager

@pytest.mark.asyncio
async def test_spider_service_init():
    # 验证任务管理器能够识别真实的爬虫方法
    assert hasattr(task_manager, "run_discuz_spider")
```

- [ ] **步骤 2：运行测试并验证失败**

运行：`pytest tests/backend/test_spider_service.py -v`
预期结果：FAIL

- [ ] **步骤 3：编写最小化实现**

```python
# backend/services/spider_service.py
# 从 core/spider.py 迁移逻辑，重点是将数据库保存改为异步：
# async def save_to_db(session, data): ...

# backend/services/task_manager.py
from .spider_service import run_discuz_spider # 假设已定义

class TaskManager:
    # ... 现有代码
    async def start_spider(self, section: str, page_instance):
        await run_discuz_spider(section, page_instance)
```

- [ ] **步骤 4：运行测试并验证通过**

运行：`pytest tests/backend/test_spider_service.py -v`
预期结果：PASS

- [ ] **步骤 5：提交代码**

```bash
git add backend/services/ tests/backend/
git commit -m "feat(backend): migrate and asyncify DiscuzSpider logic"
```

### 任务 2：实现 WebSocket 实时日志推送

**文件：**
- 创建：`backend/routers/websocket.py`
- 修改：`backend/main.py`
- 修改：`backend/services/task_manager.py` (任务日志回调)
- 测试：`tests/backend/test_websocket.py`

- [ ] **步骤 1：编写失败测试**

```python
# tests/backend/test_websocket.py
from fastapi.testclient import TestClient
from backend.main import app

def test_websocket_connection():
    client = TestClient(app)
    with client.websocket_connect("/ws/logs") as websocket:
        data = websocket.receive_json()
        assert data["message"] == "Connected to log stream"
```

- [ ] **步骤 2：运行测试并验证失败**

运行：`pytest tests/backend/test_websocket.py -v`
预期结果：FAIL

- [ ] **步骤 3：编写最小化实现**

```python
# backend/routers/websocket.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

@router.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    await websocket.send_json({"message": "Connected to log stream"})
    try:
        while True: await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# backend/main.py
from backend.routers import websocket
app.include_router(websocket.router)
```

- [ ] **步骤 4：运行测试并验证通过**

运行：`pytest tests/backend/test_websocket.py -v`
预期结果：PASS

- [ ] **步骤 5：提交代码**

```bash
git add backend/routers/websocket.py backend/main.py
git commit -m "feat(backend): implement WebSocket log streaming"
```

### 任务 3：迁移智能重命名逻辑为后端服务

**文件：**
- 创建：`backend/services/rename_service.py`
- 修改：`backend/routers/tasks.py` (增加重命名接口)
- 修改：`backend/schemas.py` (增加 RenameRequest)
- 测试：`tests/backend/test_rename_service.py`

- [ ] **步骤 1：编写失败测试**

```python
# tests/backend/test_rename_service.py
from fastapi.testclient import TestClient
from backend.main import app

def test_trigger_rename_task():
    client = TestClient(app)
    response = client.post("/api/tasks/rename", json={"files": [], "rules": []})
    assert response.status_code == 200
```

- [ ] **步骤 2：运行测试并验证失败**

运行：`pytest tests/backend/test_rename_service.py -v`
预期结果：FAIL 404

- [ ] **步骤 3：编写最小化实现**

```python
# backend/schemas.py
class RenameRequest(BaseModel):
    files: list[dict]
    rules: list[str]
    threads: int = 3

# backend/services/rename_service.py
# 迁移 RenameThread 的逻辑到此处，支持并发

# backend/routers/tasks.py
from backend.schemas import RenameRequest
@router.post("/rename")
async def start_rename(request: RenameRequest, background_tasks: BackgroundTasks):
    # 调用 rename_service
    return {"status": "started"}
```

- [ ] **步骤 4：运行测试并验证通过**

运行：`pytest tests/backend/test_rename_service.py -v`
预期结果：PASS

- [ ] **步骤 5：提交代码**

```bash
git add backend/services/rename_service.py backend/routers/tasks.py backend/schemas.py
git commit -m "feat(backend): migrate intelligent renaming to backend service"
```

### 任务 4：实现后端配置管理 API

**文件：**
- 创建：`backend/routers/settings.py`
- 修改：`backend/main.py`
- 修改：`backend/schemas.py` (增加 Settings 映射)
- 测试：`tests/backend/test_settings.py`

- [ ] **步骤 1：编写失败测试**

```python
# tests/backend/test_settings.py
from fastapi.testclient import TestClient
from backend.main import app

def test_get_settings():
    client = TestClient(app)
    response = client.get("/api/settings")
    assert response.status_code == 200
    assert "sections" in response.json()
```

- [ ] **步骤 2：运行测试并验证失败**

运行：`pytest tests/backend/test_settings.py -v`
预期结果：FAIL

- [ ] **步骤 3：编写最小化实现**

```python
# backend/routers/settings.py
# 实现 GET /api/settings 和 POST /api/settings

# backend/main.py
from backend.routers import settings
app.include_router(settings.router)
```

- [ ] **步骤 4：运行测试并验证通过**

运行：`pytest tests/backend/test_settings.py -v`
预期结果：PASS

- [ ] **步骤 5：提交代码**

```bash
git add backend/routers/settings.py backend/main.py
git commit -m "feat(backend): implement settings management API"
```
