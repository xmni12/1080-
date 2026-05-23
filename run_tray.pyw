import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw
import subprocess
import os
import sys
import webbrowser
import time
import logging

# 启用详细日志记录，确保即使没黑框也能看到报错
logging.basicConfig(
    filename='tray_system.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    encoding='utf-8'
)

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
    logging.info("正在清理端口 8000 和 5173...")
    # 使用更稳健的命令执行方式，避免 os.system 在隐藏窗口下的兼容性问题
    cmd_backend = 'for /f "tokens=5" %a in (\'netstat -ano ^| findstr :8000 ^| findstr LISTENING\') do taskkill /F /PID %a'
    cmd_frontend = 'for /f "tokens=5" %a in (\'netstat -ano ^| findstr :5173 ^| findstr LISTENING\') do taskkill /F /PID %a'
    
    subprocess.run(['cmd', '/c', cmd_backend], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    subprocess.run(['cmd', '/c', cmd_frontend], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)

def start_services():
    global backend_process, frontend_process
    project_dir = os.path.dirname(os.path.abspath(__file__))
    
    logging.info(f"项目根目录: {project_dir}")
    kill_ports()
    
    # 准备启动信息
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    
    env = os.environ.copy()
    env["PYTHONPATH"] = project_dir
    
    # --- 启动后端 (Uvicorn) ---
    logging.info("正在隐默启动后端引擎...")
    try:
        # 使用 sys.executable 确保环境一致
        # 我们将 stdout/stderr 重定向到文件，方便你查看为什么后端没起来
        with open('logs/backend_daemon.log', 'a', encoding='utf-8') as log_file:
            backend_process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"],
                cwd=project_dir,
                env=env,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=log_file,
                stderr=subprocess.STDOUT
            )
        logging.info(f"后端进程已拉起，PID: {backend_process.pid}")
    except Exception as e:
        logging.error(f"后端启动失败: {e}")

    # --- 启动前端 (Vite) ---
    frontend_dir = os.path.join(project_dir, "frontend")
    if os.path.exists(frontend_dir):
        logging.info("正在隐默启动前端引擎...")
        try:
            with open('logs/frontend_daemon.log', 'a', encoding='utf-8') as log_file:
                frontend_process = subprocess.Popen(
                    "npm run dev",
                    cwd=frontend_dir,
                    shell=True,
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    stdout=log_file,
                    stderr=subprocess.STDOUT
                )
            logging.info(f"前端进程已拉起，PID: {frontend_process.pid}")
        except Exception as e:
            logging.error(f"前端启动失败: {e}")
    else:
        logging.warning("未找到 frontend 目录，跳过前端启动。")

def stop_services():
    global backend_process, frontend_process
    logging.info("正在停止所有后台服务...")
    if backend_process:
        backend_process.terminate()
        backend_process = None
    if frontend_process:
        # npm 启动的是 shell，terminate 可能杀不掉子进程，所以还是用端口杀
        frontend_process.terminate()
        frontend_process = None
    
    kill_ports()
    # 强制清理
    os.system('taskkill /F /IM msedge.exe /T >nul 2>&1')
    os.system('taskkill /F /IM msedgewebview2.exe /T >nul 2>&1')
    os.system('taskkill /F /IM chrome.exe /T >nul 2>&1')
    logging.info("服务已彻底停止。")

def on_open_web(icon, item):
    webbrowser.open("http://localhost:5173")

def on_restart(icon, item):
    try:
        icon.notify("正在重启前后端引擎，请稍候...", "DiscuzSpider")
    except: pass
    stop_services()
    time.sleep(2)
    start_services()
    try:
        icon.notify("引擎重启完毕！", "DiscuzSpider")
    except: pass

def on_exit(icon, item):
    try:
        icon.notify("正在安全清理进程并退出系统...", "DiscuzSpider")
    except: pass
    icon.stop()

def setup(icon):
    icon.visible = True
    start_services()
    try:
        icon.notify("DiscuzSpider 已在后台隐默启动，右键点击图标控制。", "启动成功")
    except: pass

if __name__ == '__main__':
    # 改变当前工作目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(current_dir)
    os.makedirs('logs', exist_ok=True)
    
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
