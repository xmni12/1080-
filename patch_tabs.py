import re

with open('backend/services/task_manager.py', 'r', encoding='utf-8') as f:
    content = f.read()

def fix_task(content, task_name, task_key):
    match = re.search(f'async def {task_name}.*?(?=\\n\\n(?:    async def |task_manager = TaskManager\\(\\)|$))', content, re.DOTALL)
    if not match:
        print(f'Not found: {task_name}')
        return content
        
    code_block = match.group(0)
    
    # Add tab initialization
    code_block = code_block.replace(f"self.active_pages['{task_key}'] = page", f"self.active_pages['{task_key}'] = page\n            tab = page.new_tab()")
    
    # Replace page methods with tab methods ONLY for the download flow
    code_block = code_block.replace('page.get(', 'tab.get(')
    code_block = code_block.replace('page.title', 'tab.title')
    code_block = code_block.replace('page.html', 'tab.html')
    code_block = code_block.replace('page.ele(', 'tab.ele(')
    code_block = code_block.replace('page.cookies(', 'tab.cookies(')
    code_block = code_block.replace('page.user_agent', 'tab.user_agent')
    
    # Change the loud log
    code_block = code_block.replace('ws_log("⏳ 正在执行绿卡预热校验，等待突破 5 秒盾...")', 'ws_log("⏳ 正在接驳底层物理下载引擎...")')
    
    # Replace the finally block
    finally_replacement = f'''        finally:
            if '{task_key}' in self.active_pages:
                del self.active_pages['{task_key}']
            try:
                if 'tab' in locals() and tab:
                    tab.close()
                if not self.active_spiders:
                    page.quit()
            except:
                pass
            ws_log("✅ 执行完毕。独立任务标签页已安全释放。", explicit_level="success")'''
            
    old_finally = re.search(r'        finally:.*?(?=\Z)', code_block, re.DOTALL)
    if old_finally:
        code_block = code_block.replace(old_finally.group(0), finally_replacement)
        
    return content.replace(match.group(0), code_block)

content = fix_task(content, 'run_retry_tasks', 'retry')
content = fix_task(content, 'run_sniper_task', 'sniper')

with open('backend/services/task_manager.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Patch applied successfully')
