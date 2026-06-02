with open('backend/services/task_manager.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix Indentation by removing stray block
content = content.replace('             # Broadcast queue update after completion\n             await self.broadcast_queue_status()', '')

# 2. Ensure broadcast_queue_status uses main manager (queue is part of task center)
content = content.replace('await sniper_manager.broadcast_json({"type": "queue_update"', 'await manager.broadcast_json({"type": "queue_update"')

# 3. Double check sniper_search still uses sniper_manager
# Actually sniper_search doesn't use any manager, it returns results to API.
# run_sniper_task MUST use sniper_manager. 

with open('backend/services/task_manager.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Task manager structural cleanup completed.")