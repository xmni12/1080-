import pytest
from fastapi.testclient import TestClient
from backend.main import app

def test_websocket_logs():
    client = TestClient(app)
    with client.websocket_connect("/ws/logs") as websocket:
        data = websocket.receive_json()
        assert data == {"message": "Connected to log stream"}
