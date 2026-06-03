import re

with open('backend/services/task_manager.py', 'r', encoding='utf-8') as f:
    content = f.read()

# First, blindly revert ALL sniper_manager.broadcast_json to manager.broadcast_json
content = content.replace('sniper_manager.broadcast_json', 'manager.broadcast_json')

# Now, we ONLY want sniper_manager.broadcast_json inside run_sniper_task!
# run_sniper_task starts at `async def run_sniper_task` and goes to the end of the file.
match = re.search(r'(async def run_sniper_task.*?)(?=\Z)', content, re.DOTALL)
if match:
    sniper_block = match.group(1)
    # Replace ONLY inside this block
    fixed_sniper_block = sniper_block.replace('manager.broadcast_json', 'sniper_manager.broadcast_json')
    content = content.replace(sniper_block, fixed_sniper_block)

with open('backend/services/task_manager.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Log channels correctly isolated!")