import os
import re

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    replacement = '''
        # 动态推断浏览器指纹
        ua = headers.get("User-Agent", "").lower() if isinstance(headers, dict) else (self.page.user_agent.lower() if hasattr(self, 'page') else page.user_agent.lower())
        impersonate_profile = "chrome120"
        if "edg/" in ua or "edge" in ua:
            impersonate_profile = "edge101"
            
        try:
            async with CurlAsyncSession(impersonate=impersonate_profile, cookies=cookies_dict, headers=headers, verify=False, timeout=25.0) as client:'''
            
    # For spider_service.py
    content = re.sub(r'try:\s*# 替换 httpx 为 curl_cffi.*?\n\s*async with CurlAsyncSession\(impersonate=\'chrome120\', cookies=cookies_dict, headers=headers, verify=False, timeout=25\.0\) as client:', replacement, content, flags=re.DOTALL)
    
    # For task_manager.py
    content = re.sub(r'dl_res = \"NO_VALID_DOWNLOAD\"\s+async with CurlAsyncSession\(impersonate=\'chrome120\', cookies=cookies_dict, headers=headers, verify=False, timeout=25\.0\) as client:', '''dl_res = "NO_VALID_DOWNLOAD"
                        ua = page.user_agent.lower()
                        impersonate_profile = "chrome120"
                        if "edg/" in ua or "edge" in ua:
                            impersonate_profile = "edge101"
                        async with CurlAsyncSession(impersonate=impersonate_profile, cookies=cookies_dict, headers=headers, verify=False, timeout=25.0) as client:''', content, flags=re.DOTALL)
                        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

fix_file('backend/services/spider_service.py')
fix_file('backend/services/task_manager.py')
print("Fix applied")
