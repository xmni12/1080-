import os

with open('backend/services/task_manager.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add Helper Method using string find/replace to avoid regex backslash hell
helper_method = '''
    def _get_chromium_options(self, config: dict, port: int = 9222):
        from DrissionPage import ChromiumOptions
        co = ChromiumOptions().set_local_port(port)
        
        browser_path = config.get("browser_path", "").strip()
        if browser_path.lower() == "edge":
            browser_path = r"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"
        elif browser_path.lower() == "chrome":
            browser_path = r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
            
        if browser_path:
            co.set_browser_path(browser_path)
            
        profile_path = os.path.abspath('data/browser_profile')
        co.set_user_data_path(profile_path)
        
        if config.get("hide_browser", False):
            co.set_argument('--window-position=-32000,-32000')
            
        return co
'''

if '_get_chromium_options' not in content:
    content = content.replace('self.current_running_task = None', 'self.current_running_task = None' + helper_method)

# 2. Complete rewrite of sniper_search and run_sniper_task to ensure consistency
def get_method_content(name):
    # This is risky, but let's try a safer string replace for the core options block
    pass

# We'll target the options initialization block specifically in both methods
old_sniper_search_init = '''        config = load_config()
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
            co.set_argument('--window-position=-32000,-32000')
        
        page = None
        tab = None
        results = []
        try:
            page = ChromiumPage(co)
            if hide_browser:
                try: page.set.window.hide()
                except: pass
            # 开启新标签页，绝对不干扰正在运行的其他爬虫任务
            tab = page.new_tab()'''

new_sniper_search_init = '''        config = load_config()
        co = self._get_chromium_options(config)
        
        page = None
        tab = None
        results = []
        try:
            page = ChromiumPage(co)
            if config.get("hide_browser"):
                try: page.set.window.hide()
                except: pass
            tab = page.new_tab()'''

content = content.replace(old_sniper_search_init, new_sniper_search_init)

old_sniper_task_init = '''        config = load_config()
        hide_browser = config.get("hide_browser", False)
        
        co = ChromiumOptions().set_local_port(9222)
        browser_path = config.get("browser_path", "").strip()
        if browser_path.lower() == "edge":
            browser_path = r"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"
        elif browser_path.lower() == "chrome":
            browser_path = r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
            
        if browser_path:
            co.set_browser_path(browser_path)
        profile_path = os.path.abspath('data/browser_profile')
        co.set_user_data_path(profile_path)
        
        if hide_browser: 
            ws_log("已开启无头静默模式运行。")
            co.set_argument('--window-position=-32000,-32000')
            
        try:
            page = ChromiumPage(addr_or_opts=co)
            if hide_browser:
                try: page.set.window.hide()
                except: pass
            
            self.active_pages['sniper'] = page
            tab = page.new_tab()'''

new_sniper_task_init = '''        config = load_config()
        co = self._get_chromium_options(config)
        
        try:
            page = ChromiumPage(co)
            if config.get("hide_browser"):
                try: page.set.window.hide()
                except: pass
            
            self.active_pages['sniper'] = page
            tab = page.new_tab()'''

content = content.replace(old_sniper_task_init, new_sniper_task_init)

# Final check: Ensure run_sniper_task is using sniper_manager
content = content.replace('manager.broadcast_json', 'sniper_manager.broadcast_json')

with open('backend/services/task_manager.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Environment synchronization and log channel fix applied via string replacement.")
