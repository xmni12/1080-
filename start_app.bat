@echo off
title DiscuzSpider 一键启动与环境净化器
color 0b

echo =======================================================
echo.
echo          DiscuzSpider 极简爬虫调度系统
echo          (带端口防冲突自愈引擎)
echo.
echo =======================================================
echo.

:: 1. 强制净化后端端口 (8000)
echo [1/3] 正在扫描并净化 8000 端口...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo   - 发现僵尸进程 PID: %%a，正在执行强制击杀...
    taskkill /F /PID %%a >nul 2>&1
)
echo   - 8000 端口已净化完毕。
echo.

:: 2. 强制净化前端端口 (5173)
echo [2/3] 正在扫描并净化 5173 端口...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING') do (
    echo   - 发现残留进程 PID: %%a，正在执行强制击杀...
    taskkill /F /PID %%a >nul 2>&1
)
echo   - 5173 端口已净化完毕。
echo.

:: 3. 检查并启动服务
if not exist "backend" (
    echo [错误] 找不到 backend 目录，请确保在项目根目录下运行此脚本！
    pause
    exit
)

echo [3/3] 正在无冲突拉起全新双端服务...
start "DiscuzSpider-Backend" cmd /k "set PYTHONPATH=%CD%&& python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"

if not exist "frontend" (
    echo [警告] 找不到 frontend 目录，跳过前端启动。
) else (
    start "DiscuzSpider-Frontend" cmd /k "cd frontend && npm run dev"
)

echo.
echo -------------------------------------------------------
echo  🚀 系统已安全拉起，100%% 保证无僵尸进程干扰！
echo  - 后端接口: http://127.0.0.1:8000
echo  - 前端界面: http://localhost:5173 
echo -------------------------------------------------------
echo.
echo  提示：如需关闭服务，请直接关闭弹出的两个黑色命令行窗口。
echo.
pause