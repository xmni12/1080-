@echo off
:: 1. 强制净化后端端口 (8000)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)

:: 2. 强制净化前端端口 (5173)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)

:: 3. 无痕拉起服务 (使用 start /B 在后台运行，由 VBS 提供隐身护盾)
set PYTHONPATH=%CD%
start /B cmd /c "python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"
start /B cmd /c "cd frontend && npm run dev"
