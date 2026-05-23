@echo off
title DiscuzSpider 一键关闭服务
color 0c

echo =======================================================
echo.
echo          正在全网通缉并绞杀所有相关的后台服务...
echo.
echo =======================================================
echo.

echo [1/3] 正在击杀后端引擎 (8000 端口)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
    echo   - 已抹杀 PID: %%a
)

echo [2/3] 正在击杀前端引擎 (5173 端口)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
    echo   - 已抹杀 PID: %%a
)

echo [3/3] 正在清理可能卡死的无头浏览器残留...
taskkill /F /IM msedge.exe /T >nul 2>&1
taskkill /F /IM msedgewebview2.exe /T >nul 2>&1
taskkill /F /IM chrome.exe /T >nul 2>&1

echo.
echo =======================================================
echo.
echo  ✅ 所有服务已彻底关闭，世界清静了。
echo.
echo =======================================================
pause
