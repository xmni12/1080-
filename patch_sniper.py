import re

with open('backend/services/task_manager.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Extract run_retry_tasks
match = re.search(r'(    async def run_retry_tasks.*?(?=\n\n(?:task_manager = TaskManager\(\)|$)))', content, re.DOTALL)
if match:
    retry_code = match.group(1)
    
    # Transform it into run_sniper_task
    sniper_code = retry_code.replace('run_retry_tasks', 'run_sniper_task')
    sniper_code = sniper_code.replace('manager.broadcast_json', 'sniper_manager.broadcast_json')
    sniper_code = sniper_code.replace('死链抢救', '精准狙击')
    sniper_code = sniper_code.replace('"retry"', '"sniper"')
    sniper_code = sniper_code.replace("'retry'", "'sniper'")
    sniper_code = sniper_code.replace('回收站', '狙击目标')
    
    new_content = content.replace('task_manager = TaskManager()', sniper_code + '\n\ntask_manager = TaskManager()')
    
    with open('backend/services/task_manager.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Patch applied successfully.")
else:
    print("Could not find run_retry_tasks")
