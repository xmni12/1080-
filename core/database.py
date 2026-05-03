import sqlite3
import os
import datetime

DB_PATH = "data/spider_data.db"

def get_connection():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化数据库表并支持平滑升级"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. 创建基础表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            section TEXT NOT NULL,
            title TEXT,
            download_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. 检查并添加 post_url 字段 (版本升级)
    cursor.execute("PRAGMA table_info(downloads)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'post_url' not in columns:
        print("Upgrading database: Adding post_url column...")
        cursor.execute('ALTER TABLE downloads ADD COLUMN post_url TEXT')
        
    conn.commit()
    conn.close()

def migrate_from_txt():
    """将旧的 txt 记录迁移到 SQLite"""
    sections = ['4k_hd_shared', 'vr', 'sub', '4k', 'hd']
    conn = get_connection()
    cursor = conn.cursor()
    migrated_count = 0
    
    for section in sections:
        txt_path = f"data/downloaded_{section}.txt"
        if os.path.exists(txt_path):
            with open(txt_path, 'r', encoding='utf-8') as f:
                codes = [line.strip().upper() for line in f if line.strip()]
            
            for code in codes:
                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO downloads (code, section, title)
                        VALUES (?, ?, ?)
                    ''', (code, section, "Migration From TXT"))
                    migrated_count += 1
                except sqlite3.Error: pass
            
            backup_path = f"{txt_path}.bak"
            try:
                if os.path.exists(backup_path): os.remove(backup_path)
                os.rename(txt_path, backup_path)
            except: pass
                
    conn.commit()
    conn.close()

def load_codes_by_section(section):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT code FROM downloads WHERE section = ?', (section,))
    codes = set(row['code'] for row in cursor.fetchall())
    conn.close()
    return codes

def load_all_codes_flat():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT code FROM downloads')
    codes = set(row['code'] for row in cursor.fetchall())
    conn.close()
    return codes

def get_code_section(code):
    """获取番号当前所属的版块"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT section FROM downloads WHERE code = ?', (code.upper(),))
    res = cursor.fetchone()
    conn.close()
    return res['section'] if res else None

def check_code_exists_in_section(section, code):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM downloads WHERE section = ? AND code = ?', (section, code.upper()))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def save_code(section, code, title="", post_url=""):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 使用 REPLACE INTO，这样如果 code 已存在，会更新 section/title/url/time
        cursor.execute('''
            REPLACE INTO downloads (code, section, title, post_url, download_time)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (code.upper(), section, title, post_url))
        conn.commit()
    except sqlite3.Error as e: print(f"DB Save Error: {e}")
    finally: conn.close()

def delete_code(code):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM downloads WHERE code = ?', (code.upper(),))
    conn.commit()
    conn.close()

def get_recent_codes(section, limit=25, search_keyword=""):
    conn = get_connection()
    cursor = conn.cursor()
    query = 'SELECT code FROM downloads WHERE section = ?'
    params = [section]
    if search_keyword:
        query += ' AND code LIKE ?'
        params.append(f"%{search_keyword.upper()}%")
    query += ' ORDER BY download_time DESC'
    if not search_keyword:
        query += f' LIMIT {limit}'
    cursor.execute(query, params)
    codes = [row['code'] for row in cursor.fetchall()]
    cursor.execute('SELECT COUNT(*) as count FROM downloads WHERE section = ?', (section,))
    total = cursor.fetchone()['count']
    conn.close()
    return codes, total

def get_full_record(code):
    """获取番号的完整记录信息"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM downloads WHERE code = ?', (code.upper(),))
    res = cursor.fetchone()
    conn.close()
    return dict(res) if res else None

def search_global(keyword, limit=100):
    """全局搜索番号"""
    conn = get_connection()
    cursor = conn.cursor()
    query = 'SELECT * FROM downloads'
    params = []
    if keyword:
        query += ' WHERE code LIKE ? OR title LIKE ?'
        params = [f"%{keyword.upper()}%", f"%{keyword}%"]
    query += ' ORDER BY download_time DESC LIMIT ?'
    params.append(limit)
    cursor.execute(query, params)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results

init_db()
migrate_from_txt()
