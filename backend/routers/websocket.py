from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import json
import os
from collections import deque

router = APIRouter()
os.makedirs("data", exist_ok=True)

class ConnectionManager:
    def __init__(self, log_file: str):
        self.log_file = log_file
        self.active_connections: List[WebSocket] = []
        self.log_history = deque(maxlen=200)
        self._load_history()

    def _load_history(self):
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in lines[-200:]:
                        if line.strip():
                            self.log_history.append(json.loads(line.strip()))
            except: pass

    def _save_log(self, data: dict):
        self.log_history.append(data)
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
        except: pass

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        data = {"message": message, "level": "info"}
        self._save_log(data)
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except: pass

    async def broadcast_json(self, data: dict):
        self._save_log(data)
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except: pass

manager = ConnectionManager("data/spider_latest.log")
sniper_manager = ConnectionManager("data/sniper_latest.log")

@router.get("/api/ws/history")
async def get_ws_history():
    return list(manager.log_history)

@router.get("/api/ws/sniper_history")
async def get_sniper_ws_history():
    return list(sniper_manager.log_history)

@router.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await websocket.send_json({"message": "Connected to Main log stream", "level": "info"})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

@router.websocket("/ws/sniper_logs")
async def sniper_websocket_endpoint(websocket: WebSocket):
    await sniper_manager.connect(websocket)
    try:
        await websocket.send_json({"message": "Connected to Sniper log stream", "level": "info"})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        sniper_manager.disconnect(websocket)
    except Exception:
        sniper_manager.disconnect(websocket)
