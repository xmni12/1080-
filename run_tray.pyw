import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw
import subprocess
import threading
import os
import sys
import webbrowser
import time

backend_process = None
frontend_process = None

def create_image():
    # 生成一个 64x64 的图标：黑底紫色爬虫/雷达示意图
    image = Image.new('RGB', (64, 64), color=(20, 20, 25))
    draw = ImageDraw.Draw(image)
    # 画一个紫色的外圈
    draw.ellipse((8, 8, 56, 56), outline=(168, 85, 247), width=4)
    # 画一个内圈
    draw.ellipse((20, 20, 44, 44), fill=(168, 85, 247))
    return image

def kill_ports():
    # 强制清理占用 8000 和 5173 的进程
    os.system('for /f "tokens=5" %a in (\'netstat -ano ^| findstr :8000 ^| findstr LISTENING\') do taskkill /F /PID %a >nul 2>&1')
    os.system('for /f "tokens=5" %a in (\'netstat -ano ^| findstr :5173 ^| findstr LISTENING\') do taskkill /F /PID %a >nul 2>&1')

def start_services():
    global backend_process, frontend_process
    kill_ports()
    
    # 获取项目根目录
    project_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 启动后端 (隐藏窗口)
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    
    env = os.environ.copy()
    env["PYTHONPATH"] = project_dir
    
    backend_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=project_dir,
        env=env,
        startupinfo=startupinfo,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    
    # 启动前端 (隐藏窗口)
    frontend_dir = os.path.join(project_dir, "frontend")
    if os.path.exists(frontend_dir):
        # On Windows, npm is a cmd script, so we need shell=True or to call npm.cmd
        frontend_process = subprocess.Popen(
            "npm run dev",
            cwd=frontend_dir,
            shell=True,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

def stop_services():
    global backend_process, frontend_process
    if backend_process:
        backend_process.terminate()
        backend_process = None
    if frontend_process:
        frontend_process.terminate()
        frontend_process = None
    kill_ports()
    # 清理卡死的无头浏览器
    os.system('taskkill /F /IM msedge.exe /T >nul 2>&1')
    os.system('taskkill /F /IM msedgewebview2.exe /T >nul 2>&1')
    os.system('taskkill /F /IM chrome.exe /T >nul 2>&1')

def on_open_web(icon, item):
    webbrowser.open("http://localhost:5173")

def on_restart(icon, item):
    icon.notify("正在重启前后端引擎，请稍候...", "DiscuzSpider")
    stop_services()
    time.sleep(2)
    start_services()
    icon.notify("引擎重启完毕！", "DiscuzSpider")

def on_exit(icon, item):
    icon.notify("正在安全清理进程并退出系统...", "DiscuzSpider")
    icon.stop()

def setup(icon):
    icon.visible = True
    start_services()
    icon.notify("DiscuzSpider 已在后台隐默启动，右键点击图标控制。", "启动成功")

if __name__ == '__main__':
    # 改变当前工作目录为脚本所在目录
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    menu = pystray.Menu(
        item('🌐 打开控制大盘 (Web UI)', on_open_web, default=True),
        pystray.Menu.SEPARATOR,
        item('🔄 重启强杀双引擎 (Restart)', on_restart),
        pystray.Menu.SEPARATOR,
        item('🛑 安全退出系统 (Exit)', on_exit)
    )
    
    icon = pystray.Icon("DiscuzSpider", create_image(), "Discuz 爬虫中心", menu)
    
    try:
        icon.run(setup)
    finally:
        stop_services()
