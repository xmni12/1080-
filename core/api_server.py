from flask import Flask, jsonify, request
from flask_cors import CORS
import threading
from .database import load_codes_by_section, save_code

app = Flask(__name__)
CORS(app)

class ApiServer:
    def __init__(self, signal_handler=None):
        self.signal_handler = signal_handler
        # 默认从 4k 和 hd 的汇总中获取，或者干脆加载所有
        # 为了简单，API 启动时加载一次，或者动态查询
        pass

    def get_codes(self):
        # 动态从数据库查询所有已下载番号
        from .database import get_connection
        conn = sqlite3_connect_local() # 需要一个局部方法或导入
        # 简化方案：直接导入 database 的方法
        from .database import load_all_codes_flat
        return jsonify(list(load_all_codes_flat()))

    def add_code(self):
        data = request.json
        code = data.get('code', '').upper()
        if code:
            from .database import save_code, load_all_codes_flat
            all_codes = load_all_codes_flat()
            if code not in all_codes:
                # 网页点击下载的，统一归类到 'manual' 或 'web' 版块
                save_code('web_sync', code, "Sync from Tampermonkey")
                if self.signal_handler:
                    self.signal_handler.emit(code)
                return jsonify({"status": "success", "msg": f"Code {code} recorded"}), 200
            else:
                return jsonify({"status": "exists"}), 200
        return jsonify({"status": "error"}), 400

    def run(self, host='127.0.0.1', port=5000):
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        app.run(host=host, port=port, debug=False, use_reloader=False)

# 辅助函数，避免循环引用或复杂的 DB 管理
def sqlite3_connect_local():
    import sqlite3
    conn = sqlite3.connect("data/spider_data.db")
    return conn

@app.route('/api/get_codes', methods=['GET'])
def get_codes_route():
    import sqlite3
    conn = sqlite3.connect("data/spider_data.db")
    cursor = conn.cursor()
    cursor.execute('SELECT code FROM downloads')
    codes = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(codes)

@app.route('/api/add_code', methods=['POST'])
def add_code_route():
    data = request.json
    code = data.get('code', '').upper()
    if not code: return jsonify({"status": "error"}), 400
    
    import sqlite3
    conn = sqlite3.connect("data/spider_data.db")
    cursor = conn.cursor()
    # 检查是否存在
    cursor.execute('SELECT 1 FROM downloads WHERE code = ?', (code,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"status": "exists"}), 200
    
    # 插入
    cursor.execute('INSERT INTO downloads (code, section, title) VALUES (?, ?, ?)', 
                   (code, 'web_sync', 'Sync from Tampermonkey'))
    conn.commit()
    conn.close()
    
    # 注意：这里无法直接访问 Signal，因为路由是全局装饰器定义的
    # 这在 Flask 结合 Qt 时是个麻烦。
    # 暂时通过一个全局变量或者简单的轮询来解决，或者保持之前的类定义方式。
    return jsonify({"status": "success"}), 200

def start_api_thread(unused_file, signal_handler):
    # 这里我们还是用类的方式，方便传递 signal_handler
    server = ApiServer(signal_handler)
    # 重新注册路由以使用 self
    app.add_url_rule('/api/get_codes', 'get_codes', server.get_codes, methods=['GET'], overwrite=True)
    app.add_url_rule('/api/add_code', 'add_code', server.add_code, methods=['POST'], overwrite=True)
    
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return server
