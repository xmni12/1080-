import re

with open('backend/services/task_manager.py', 'r', encoding='utf-8') as f:
    content = f.read()

def patch_sniper_options(content):
    old_opts = '''        config = load_config()
        # 强制与主爬虫共用 9222 端口，实现完全的绿卡与指纹共享
        co = ChromiumOptions().set_local_port(9222)
        if config.get("browser_path"):
            co.set_browser_path(config.get("browser_path"))
        
        profile_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'browser_profile')
        co.set_user_data_path(profile_path)
        co.set_argument('--window-position=-32000,-32000')'''
        
    new_opts = '''        config = load_config()
        # 强制与主爬虫共用 9222 端口，实现完全的绿卡与指纹共享
        co = ChromiumOptions().set_local_port(9222)
        browser_path = config.get("browser_path", "").strip()
        if browser_path.lower() == "edge":
            browser_path = r"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"
        elif browser_path.lower() == "chrome":
            browser_path = r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
            
        if browser_path:
            co.set_browser_path(browser_path)
        
        profile_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'browser_profile')
        co.set_user_data_path(profile_path)
        
        hide_browser = config.get("hide_browser", False)
        if hide_browser:
            co.set_argument('--window-position=-32000,-32000')'''
            
    return content.replace(old_opts, new_opts)

def patch_page_hide(content):
    # After page = ChromiumPage(co), if hide_browser is True, do page.set.window.hide() in sniper_search
    # It's better to find `tab = page.new_tab()`
    old_code = '''        try:
            page = ChromiumPage(co)
            # 开启新标签页，绝对不干扰正在运行的其他爬虫任务
            tab = page.new_tab()'''
            
    new_code = '''        try:
            page = ChromiumPage(co)
            if hide_browser:
                try: page.set.window.hide()
                except: pass
            # 开启新标签页，绝对不干扰正在运行的其他爬虫任务
            tab = page.new_tab()'''
    return content.replace(old_code, new_code)

content = patch_sniper_options(content)
content = patch_page_hide(content)

with open('backend/services/task_manager.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Patched successfully')