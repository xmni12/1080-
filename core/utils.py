import json
import os
import re

CODE_REGEX = r'[a-zA-Z]{2,12}-\d{3,6}'

def extract_code(text):
    if not text: return None
    match = re.search(CODE_REGEX, text, re.IGNORECASE)
    return match.group(0).upper() if match else None

CONFIG_FILE = "data/config_v4.json"

def save_config(config_data):
    os.makedirs("data", exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=4, ensure_ascii=False)

def load_config():
    if not os.path.exists(CONFIG_FILE): return {}
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except: return {}
