import sys
import os
import pyperclip
import datetime
import json
import traceback
import ctypes
import requests
import webbrowser

# 隐藏控制台
if os.name == 'nt':
    try:
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except: pass

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QCheckBox, QGroupBox, QPushButton, 
                             QTextEdit, QLabel, QLineEdit, QFileDialog, 
                             QMessageBox, QTableWidget, QTableWidgetItem, 
                             QAbstractItemView, QTabWidget, QStyle, QHeaderView, 
                             QProgressBar, QMenu, QDialog)
from PySide6.QtCore import Qt, QThread, Signal, Slot, QTimer
from PySide6.QtGui import QColor, QAction, QPixmap, QImage

from core.api_server import start_api_thread
from core.spider import DiscuzSpider
from core.utils import load_config, save_config
from core.database import load_codes_by_section, save_code, delete_code, get_recent_codes, search_global, get_full_record

# --- 封面预览窗口 ---
class ImagePreviewDialog(QDialog):
    def __init__(self, parent, code, img_url):
        super().__init__(parent)
        self.setWindowTitle(f"封面预览: {code}")
        self.setFixedSize(400, 600)
        layout = QVBoxLayout(self)
        self.lbl_img = QLabel("正在加载预览图...")
        self.lbl_img.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_img)
        self.load_image(img_url)

    def load_image(self, url):
        if not url:
            self.lbl_img.setText("未找到封面图")
            return
        try:
            resp = requests.get(url, timeout=10)
            img = QImage.fromData(resp.content)
            pixmap = QPixmap.fromImage(img)
            self.lbl_img.setPixmap(pixmap.scaled(380, 580, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception as e:
            self.lbl_img.setText(f"加载失败: {e}")

# --- 线程包装器 ---
class SpiderThread(QThread):
    log_signal = Signal(str)
    code_signal = Signal(str)
    page_signal = Signal(int)

    def __init__(self, spider, config):
        super().__init__()
        self.spider = spider
        self.config = config
        self.spider.log = lambda t: self.log_signal.emit(t)
        self.spider.update_codes = self.code_signal
        self.spider.report_page = self.page_signal

    def run(self):
        try: self.spider.run_task(self.config)
        except Exception as e: self.log_signal.emit(f"线程崩溃: {e}")

# --- 版块组件 ---
class SectionWidget(QWidget):
    def __init__(self, parent, key, name, url):
        super().__init__()
        self.main = parent
        self.key = key
        self.name = name
        self.url = url
        self.downloaded_codes = load_codes_by_section(key)
        self.init_ui()
        self.spider = DiscuzSpider(None, None, self.downloaded_codes, None, key)

    def init_ui(self):
        layout = QVBoxLayout(self)
        top_group = QGroupBox("版块独立配置")
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("起始页:"))
        self.start_page_input = QLineEdit("1")
        self.start_page_input.setFixedWidth(50)
        top_layout.addWidget(self.start_page_input)
        top_layout.addWidget(QLabel(" [进度]:"))
        self.history_label = QLabel("1")
        self.history_label.setStyleSheet("color: purple; font-weight: bold;")
        top_layout.addWidget(self.history_label)
        top_layout.addWidget(QLabel("  保存路径:"))
        self.path_input = QLineEdit()
        self.path_input.textChanged.connect(lambda _: self.main.save_all_config())
        btn_path = QPushButton("浏览")
        btn_path.clicked.connect(self.choose_path)
        top_layout.addWidget(self.path_input, 1)
        top_layout.addWidget(btn_path)
        top_group.setLayout(top_layout)
        layout.addWidget(top_group)

        timer_group = QGroupBox("拟人化与定时")
        timer_layout = QHBoxLayout()
        self.chk_simulate = QCheckBox("启用拟人化行为 (随机滚动/停顿)")
        self.chk_simulate.setChecked(True)
        timer_layout.addWidget(self.chk_simulate)
        
        self.timer_enabled = QCheckBox("开启定时")
        timer_layout.addWidget(self.timer_enabled)
        self.timer_time = QLineEdit("03:00")
        self.timer_time.setFixedWidth(60)
        timer_layout.addWidget(QLabel("触发时间:"))
        timer_layout.addWidget(self.timer_time)
        self.timer_status = QLabel("状态: 待命")
        timer_layout.addWidget(self.timer_status)
        timer_layout.addStretch()
        timer_group.setLayout(timer_layout)
        layout.addWidget(timer_group)

        mid_layout = QHBoxLayout()
        left = QVBoxLayout()
        h_t = QHBoxLayout()
        h_t.addWidget(QLabel("番号记录:"))
        self.count_lbl = QLabel("(0)")
        h_t.addWidget(self.count_lbl)
        left.addLayout(h_t)
        self.search_in = QLineEdit()
        self.search_in.setPlaceholderText("🔍 搜索本地已下记录...")
        self.search_in.textChanged.connect(self.refresh_table)
        left.addWidget(self.search_in)
        
        man = QHBoxLayout()
        self.man_in = QTextEdit()
        self.man_in.setPlaceholderText("支持批量录入/删除 (一行一个)")
        self.man_in.setMaximumHeight(55)
        btn_v = QVBoxLayout()
        btn_a = QPushButton("录入")
        btn_a.clicked.connect(self.add_manual)
        btn_d = QPushButton("删除")
        btn_d.setStyleSheet("color: red;")
        btn_d.clicked.connect(self.delete_manual)
        btn_v.addWidget(btn_a)
        btn_v.addWidget(btn_d)
        man.addWidget(self.man_in)
        man.addLayout(btn_v)
        left.addLayout(man)
        
        self.table = QTableWidget(0, 1)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setVisible(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        left.addWidget(self.table)
        
        btn_c = QPushButton("复制全部已下番号")
        btn_c.clicked.connect(self.copy_all)
        left.addWidget(btn_c)
        mid_layout.addLayout(left, 1)

        right = QVBoxLayout()
        right.addWidget(QLabel("版块日志:"))
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        right.addWidget(self.log_box)
        mid_layout.addLayout(right, 2)
        layout.addLayout(mid_layout)

        self.btn_start = QPushButton(f"启动爬取任务")
        self.btn_start.setStyleSheet("height: 45px; font-weight: bold; background-color: #4CAF50; color: white;")
        self.btn_start.clicked.connect(self.start_task)
        self.btn_stop = QPushButton("停止")
        self.btn_stop.setStyleSheet("height: 45px; background-color: #f44336; color: white;")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_task)
        
        ctrl = QHBoxLayout()
        ctrl.addWidget(self.btn_start)
        ctrl.addWidget(self.btn_stop)
        layout.addLayout(ctrl)

    def choose_path(self):
        p = QFileDialog.getExistingDirectory(self, "选择路径")
        if p: 
            self.path_input.setText(p)
            self.main.save_all_config()

    def add_log(self, text):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_box.append(f"[{ts}] {text}")

    def refresh_table(self):
        search = self.search_in.text().strip()
        display_codes, total = get_recent_codes(self.key, limit=25, search_keyword=search)
        self.count_lbl.setText(f"({total})")
        if not search and total > 25: 
            display_codes.append(f"... (余 {total-25} 项)")
        self.table.setRowCount(len(display_codes))
        for i, t in enumerate(display_codes):
            self.table.setItem(i, 0, QTableWidgetItem(t))

    def add_manual(self):
        text = self.man_in.toPlainText().strip()
        if not text: return
        added = 0
        for c in [c.strip().upper() for c in text.split('\n') if c.strip()]:
            if c not in self.downloaded_codes:
                save_code(self.key, c, "Manual Entry")
                self.downloaded_codes.add(c)
                added += 1
        if added > 0:
            self.refresh_table()
            self.man_in.clear()
            self.add_log(f"批量录入了 {added} 个番号。")

    def delete_manual(self):
        items = self.table.selectedItems()
        to_del = [i.text() for i in items if not i.text().startswith(".")]
        if not to_del: return
        if QMessageBox.Yes == QMessageBox.question(self, '确认删除', f"确定删除选中的 {len(to_del)} 个番号？"):
            for c in to_del:
                if c in self.downloaded_codes: self.downloaded_codes.remove(c)
                delete_code(c)
            self.refresh_table()
            self.add_log(f"已删除 {len(to_del)} 个记录。")

    def copy_all(self):
        pyperclip.copy("\n".join(sorted(list(self.downloaded_codes))))
        self.add_log("已复制到剪贴板。")

    def show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item or item.text().startswith("."): return
        code = item.text()
        record = get_full_record(code)
        
        menu = QMenu()
        menu.addAction("🌐 在 AVBase 查看详情").triggered.connect(lambda: webbrowser.open(f"https://www.avbase.net/works?q={code}"))
        if record and record.get('post_url'):
            menu.addAction("论坛 在论坛打开帖子").triggered.connect(lambda: webbrowser.open(record['post_url']))
        menu.addAction("📋 复制完整标题").triggered.connect(lambda: record and pyperclip.copy(record.get('title', '')))
        menu.addAction("🖼️ 预览封面 (嗅探)").triggered.connect(lambda: self.main.preview_cover(code))
        menu.exec(self.table.mapToGlobal(pos))

    def start_task(self):
        if not self.main.is_kernel_alive():
            QMessageBox.warning(self, "错误", "浏览器内核未就绪，请点击下方的『初始化浏览器』！")
            return
        conf = {
            'url': self.url,
            'start_page': int(self.start_page_input.text() or 1),
            'save_path': self.path_input.text() or "./downloads",
            'daily_limit': 55,
            'simulate_human': self.chk_simulate.isChecked()
        }
        # HD 关联 4K
        if self.key == 'hd': conf['cross_check_sections'] = ['4k']
        self.spider.set_browser(self.main.shared_page)
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.thread = SpiderThread(self.spider, conf)
        self.thread.log_signal.connect(self.add_log)
        self.thread.code_signal.connect(self.on_code_downloaded)
        self.thread.page_signal.connect(self.on_page_update)
        self.thread.finished.connect(self.on_finished)
        self.thread.start()

    def stop_task(self):
        self.spider.stop()
        self.add_log("正在停止任务...")

    def on_finished(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.add_log("任务已结束。")

    def on_page_update(self, p):
        self.history_label.setText(str(p))
        self.main.save_all_config()

    def on_code_downloaded(self, code):
        if code not in self.downloaded_codes: self.downloaded_codes.add(code)
        self.refresh_table()
        self.main.update_quota(self.key)

# --- 智能重命名组件 ---
class RenameThread(QThread):
    progress = Signal(int, str, str, str)
    status_update = Signal(int, int)
    finished_signal = Signal()
    log = Signal(str)

    def __init__(self, items, rules, page, max_workers):
        super().__init__()
        self.items = items; self.rules = rules; self.page = page; self.max_workers = max_workers
        self.stop_requested = False

    def stop(self): self.stop_requested = True
    def run(self):
        import re
        import concurrent.futures
        from core.avbase_spider import AvbaseSpider
        total = len(self.items)
        completed = 0

        def process_item(item):
            if self.stop_requested: return None
            try:
                tab = self.page.new_tab()
                spider = AvbaseSpider(tab)
                orig_name = item['name']
                search_term = orig_name
                for rule in self.rules:
                    r = rule.strip()
                    if r:
                        try: search_term = re.sub(r, "", search_term, flags=re.IGNORECASE)
                        except: search_term = search_term.replace(r, "")
                search_term, _ = os.path.splitext(search_term)
                self.log.emit(f"开始识别: {orig_name}")
                new_code, img_url, error_msg = spider.search_code(search_term.strip())
                tab.close()
                if new_code: return (item['row'], orig_name, new_code, img_url or "")
                else: return (item['row'], orig_name, f"失败: {error_msg or '未知'}", "")
            except Exception as e:
                return (item['row'], item['name'], f"异常: {str(e)}", "")

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_item = {executor.submit(process_item, item): item for item in self.items}
            for future in concurrent.futures.as_completed(future_to_item):
                if self.stop_requested:
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                try:
                    result = future.result()
                    if result: self.progress.emit(*result)
                except Exception as e:
                    item = future_to_item[future]
                    self.progress.emit(item['row'], item['name'], f"致命异常: {str(e)}", "")
                completed += 1
                self.status_update.emit(completed, total)
        self.finished_signal.emit()
class RenameWidget(QWidget):
    def __init__(self, parent):
        super().__init__(); self.main = parent; self.setAcceptDrops(True); self.init_ui()
    def init_ui(self):
        from PySide6.QtWidgets import QSplitter
        layout = QVBoxLayout(self)
        
        # --- 顶部控制栏 ---
        ctrl_layout = QHBoxLayout()
        
        rule_group = QGroupBox("正则/屏蔽词 (一行一个)")
        rule_layout = QVBoxLayout()
        self.rule_input = QTextEdit()
        self.rule_input.setPlaceholderText("例如: \\[1080P\\]\n广告网址\\.com")
        self.rule_input.setMaximumHeight(60)
        rule_layout.addWidget(self.rule_input)
        rule_group.setLayout(rule_layout)
        ctrl_layout.addWidget(rule_group, 2)
        
        set_group = QGroupBox("控制面板")
        s_lay = QVBoxLayout()
        h_t = QHBoxLayout()
        h_t.addWidget(QLabel("并发线程:"))
        self.thread_count_spin = QLineEdit("3")
        self.thread_count_spin.setFixedWidth(40)
        h_t.addWidget(self.thread_count_spin)
        s_lay.addLayout(h_t)
        
        btn_lay = QHBoxLayout()
        self.btn_search = QPushButton("🚀 开始识别")
        self.btn_search.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        self.btn_search.clicked.connect(self.start_recognition)
        self.btn_stop = QPushButton("⛔ 停止")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_recognition)
        btn_lay.addWidget(self.btn_search)
        btn_lay.addWidget(self.btn_stop)
        s_lay.addLayout(btn_lay)
        set_group.setLayout(s_lay)
        ctrl_layout.addWidget(set_group, 1)

        act_group = QGroupBox("执行操作")
        a_lay = QVBoxLayout()
        self.btn_rename = QPushButton("✅ 一键应用改名")
        self.btn_rename.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.btn_rename.clicked.connect(self.execute_rename)
        self.btn_clear = QPushButton("🗑️ 清空列表")
        self.btn_clear.clicked.connect(self.clear_table)
        a_lay.addWidget(self.btn_rename)
        a_lay.addWidget(self.btn_clear)
        act_group.setLayout(a_lay)
        ctrl_layout.addWidget(act_group, 1)
        
        layout.addLayout(ctrl_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # --- 分割器 (表格与日志) ---
        splitter = QSplitter(Qt.Vertical)
        
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["原文件名", "识别结果", "改名后预览", "路径"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setColumnHidden(3, True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.itemDoubleClicked.connect(self.show_preview)
        splitter.addWidget(self.table)
        
        log_group = QGroupBox("实时日志")
        log_lay = QVBoxLayout()
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        log_lay.addWidget(self.log_box)
        log_group.setLayout(log_lay)
        splitter.addWidget(log_group)
        
        splitter.setSizes([500, 150])
        layout.addWidget(splitter)

    def add_log(self, text):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_box.append(f"[{ts}] {text}")

    def show_preview(self, item):
        if item.column() == 1:
            img_url = item.data(Qt.UserRole)
            if img_url:
                code = item.text()
                ImagePreviewDialog(self.main, code, img_url).exec()

    def dragEnterEvent(self, event): 
        if event.mimeData().hasUrls(): event.accept()
        else: event.ignore()
    def dropEvent(self, event):
        valid_exts = {'.mp4', '.mkv', '.avi', '.ts', '.wmv', '.mov', '.srt', '.ass', '.ssa', '.vtt', '.sub', '.str'}
        for url in event.mimeData().urls():
            p = url.toLocalFile()
            if os.path.isfile(p):
                _, ext = os.path.splitext(p)
                if ext.lower() in valid_exts:
                    row = self.table.rowCount(); self.table.insertRow(row)
                    self.table.setItem(row, 0, QTableWidgetItem(os.path.basename(p)))
                    self.table.setItem(row, 1, QTableWidgetItem("等待中..."))
                    self.table.setItem(row, 3, QTableWidgetItem(p))
    def clear_table(self): self.table.setRowCount(0); self.log_box.clear(); self.progress_bar.setVisible(False)
    def stop_recognition(self):
        if hasattr(self, 'thread'): self.thread.stop(); self.btn_stop.setEnabled(False)
    def start_recognition(self):
        if not self.main.is_kernel_alive(): return
        items = []
        for i in range(self.table.rowCount()):
            status = self.table.item(i, 1).text()
            if status in ["等待中...", "失败:"] or "异常" in status:
                items.append({'row': i, 'name': self.table.item(i, 0).text(), 'path': self.table.item(i, 3).text()})
        if not items: return
        self.btn_search.setEnabled(False); self.btn_stop.setEnabled(True)
        self.progress_bar.setVisible(True); self.progress_bar.setMaximum(len(items)); self.progress_bar.setValue(0)
        
        workers = int(self.thread_count_spin.text() or 3)
        self.thread = RenameThread(items, self.rule_input.toPlainText().split('\n'), self.main.shared_page, workers)
        self.thread.progress.connect(self.update_row)
        self.thread.status_update.connect(lambda c, t: self.progress_bar.setValue(c))
        self.thread.finished_signal.connect(self.on_done)
        self.thread.log.connect(self.add_log)
        self.thread.start()
    def update_row(self, row, name, res, img_url):
        item = QTableWidgetItem(res)
        item.setForeground(QColor("red") if "失败" in res else QColor("green"))
        if img_url: item.setData(Qt.UserRole, img_url)
        self.table.setItem(row, 1, item)
        if "失败" not in res:
            _, ext = os.path.splitext(self.table.item(row, 3).text())
            self.table.setItem(row, 2, QTableWidgetItem(res + ext))
    def on_done(self): self.btn_search.setEnabled(True); self.btn_stop.setEnabled(False); self.progress_bar.setVisible(False)
    def execute_rename(self):
        for i in range(self.table.rowCount()):
            res = self.table.item(i, 1).text()
            if res and "失败" not in res and res != "等待中...":
                path = self.table.item(i, 3).text()
                new_path = os.path.join(os.path.dirname(path), self.table.item(i, 2).text())
                try: os.rename(path, new_path); self.table.setItem(i, 1, QTableWidgetItem("已完成"))
                except: pass

# --- ed2k 提取组件 ---
class Ed2kWidget(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.main = parent
        self.setAcceptDrops(True)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        self.output_name = QLineEdit("ed2k提取结果.txt")
        self.save_path = QLineEdit(os.path.join(os.path.expanduser("~"), "Desktop"))
        top.addWidget(QLabel("导出文件名:")); top.addWidget(self.output_name)
        top.addWidget(QLabel("保存到:")); top.addWidget(self.save_path, 1)
        btn_b = QPushButton("浏览"); btn_b.clicked.connect(self.choose_path); top.addWidget(btn_b)
        layout.addLayout(top)
        btns = QHBoxLayout()
        btn_e = QPushButton("开始提取 (拖入txt)")
        btn_e.clicked.connect(self.extract)
        btn_s = QPushButton("保存为文件")
        btn_s.clicked.connect(self.save)
        btn_c = QPushButton("清空表格")
        btn_c.clicked.connect(self.clear_table)
        btns.addWidget(btn_e)
        btns.addWidget(btn_s)
        btns.addWidget(btn_c)
        layout.addLayout(btns)
        
        self.table = QTableWidget(0, 2); self.table.setHorizontalHeaderLabels(["来源文件", "ed2k链接"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.table); self.pending = []
    def choose_path(self):
        p = QFileDialog.getExistingDirectory(self, "选择保存路径")
        if p: self.save_path.setText(p)
    def dragEnterEvent(self, event): event.accept()
    def dropEvent(self, event):
        for url in event.mimeData().urls():
            p = url.toLocalFile()
            if p.endswith(".txt"): 
                self.pending.append(p)
    def clear_table(self):
        self.table.setRowCount(0)
        self.pending = []
    def extract(self):
        header = "115視頻格式離綫下載地址："; links = set()
        for p in self.pending:
            content = ""; 
            for enc in ['utf-8-sig', 'gbk', 'utf-8']:
                try: 
                    with open(p, 'r', encoding=enc) as f: content = f.read(); break
                except: continue
            if header in content:
                for part in content.split(header)[1:]:
                    for line in part.strip().split('\n'):
                        l = line.strip()
                        if l.lower().startswith("ed2k://") and l not in links:
                            links.add(l); row = self.table.rowCount(); self.table.insertRow(row); self.table.setItem(row, 0, QTableWidgetItem(os.path.basename(p))); self.table.setItem(row, 1, QTableWidgetItem(l))
                        elif not l: continue
                        else: break
        self.pending = []
    def save(self):
        out = os.path.join(self.save_path.text(), self.output_name.text())
        with open(out, 'w', encoding='utf-8') as f:
            for i in range(self.table.rowCount()): f.write(self.table.item(i, 1).text() + '\n')
        QMessageBox.information(self, "完成", f"已成功保存到 {out}")

# --- 全局搜索组件 ---
class GlobalSearchWidget(QWidget):
    def __init__(self, parent): super().__init__(); self.main = parent; self.init_ui()
    def init_ui(self):
        layout = QVBoxLayout(self)
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 跨版块全局搜索番号、标题关键字...")
        self.search_input.textChanged.connect(self.start_search)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["番号", "所属版块", "下载时间", "原始帖子标题"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_menu)
        layout.addWidget(self.table)
        self.status = QLabel("输入关键字开始检索库...")
        layout.addWidget(self.status)
    def start_search(self):
        results = search_global(self.search_input.text().strip()); self.table.setRowCount(len(results))
        for i, row in enumerate(results):
            self.table.setItem(i, 0, QTableWidgetItem(str(row['code']))); self.table.setItem(i, 1, QTableWidgetItem(str(row['section']).upper())); self.table.setItem(i, 2, QTableWidgetItem(str(row['download_time']))); self.table.setItem(i, 3, QTableWidgetItem(str(row['title'])))
        self.status.setText(f"共找到 {len(results)} 条匹配记录")
    def show_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item: return
        row = self.table.currentRow()
        code = self.table.item(row, 0).text()
        record = get_full_record(code)
        menu = QMenu()
        menu.addAction("🌐 在 AVBase 查看详情").triggered.connect(lambda: webbrowser.open(f"https://www.avbase.net/works?q={code}"))
        if record and record.get('post_url'):
            menu.addAction("论坛 在论坛打开帖子").triggered.connect(lambda: webbrowser.open(record['post_url']))
        menu.addAction("🖼️ 预览封面图").triggered.connect(lambda: self.main.preview_cover(code))
        menu.exec(self.table.mapToGlobal(pos))

# --- 主窗口 ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Discuz 论坛自动爬取助手 V5.4 交互旗舰版")
        self.resize(1200, 900)
        self.shared_page = None
        self.config = load_config()
        self.is_loading = True
        self.quotas = {"4k": 0, "vr": 0, "hd": 0, "sub": 0}
        self.last_reset_date = datetime.date.today()
        self.init_ui()
        self.load_all_config()
        self.is_loading = False
        
        # 定时器：主逻辑
        self.master_timer = QTimer(self); self.master_timer.timeout.connect(self.global_tick); self.master_timer.start(30000)
        # 定时器：内核心跳监测
        self.heartbeat_timer = QTimer(self); self.heartbeat_timer.timeout.connect(self.check_kernel_status); self.heartbeat_timer.start(5000)
        # 定时器：登录成功监测
        self.login_monitor_timer = QTimer(self); self.login_monitor_timer.timeout.connect(self.monitor_login_success)

    def init_ui(self):
        main_widget = QWidget(); self.setCentralWidget(main_widget); layout = QVBoxLayout(main_widget)
        q_layout = QHBoxLayout(); self.q_lbls = {}
        for k, n, c in [("4k", "4K超清", "green"), ("vr", "VR視頻", "darkcyan"), ("hd", "高清有碼", "blue"), ("sub", "外掛字幕", "darkred")]:
            lbl = QLabel(f"【{n}: 0/55 】"); lbl.setStyleSheet(f"color: {c}; font-weight: bold;"); q_layout.addWidget(lbl); self.q_lbls[k] = lbl
        layout.addLayout(q_layout)
        
        self.tabs = QTabWidget()
        self.sec_4k = SectionWidget(self, "4k", "4K超清", "https://x999x.me/forum.php?mod=forumdisplay&fid=202&forumdefstyle=no")
        self.sec_vr = SectionWidget(self, "vr", "VR視頻", "https://x999x.me/forum.php?mod=forumdisplay&fid=163")
        self.sec_hd = SectionWidget(self, "hd", "高清有碼", "https://x999x.me/forum.php?mod=forumdisplay&fid=75")
        self.sec_sub = SectionWidget(self, "sub", "外掛字幕", "https://x999x.me/forum.php?mod=forumdisplay&fid=185")
        self.sec_rename = RenameWidget(self); self.sec_ed2k = Ed2kWidget(self); self.sec_search = GlobalSearchWidget(self)
        self.tabs.addTab(self.sec_4k, "4K超清"); self.tabs.addTab(self.sec_vr, "VR視頻"); self.tabs.addTab(self.sec_hd, "高清有碼")
        self.tabs.addTab(self.sec_sub, "外掛字幕"); self.tabs.addTab(self.sec_rename, "✨ 智能重命名"); self.tabs.addTab(self.sec_ed2k, "🔗 ed2k 提取"); self.tabs.addTab(self.sec_search, "🗂️ 全局仓库")
        layout.addWidget(self.tabs)

        bottom = QHBoxLayout()
        self.lbl_kernel_status = QLabel("● 内核离线")
        self.lbl_kernel_status.setStyleSheet("color: gray; font-weight: bold; margin-right: 15px;")
        bottom.addWidget(self.lbl_kernel_status)

        self.btn_init = QPushButton("第一步：初始化浏览器内核并登录")
        self.btn_init.setStyleSheet("height: 50px; background-color: #2196F3; color: white; font-weight: bold;")
        self.btn_init.clicked.connect(self.init_browser); bottom.addWidget(self.btn_init, 1)
        
        self.chk_hide = QCheckBox("静默运行 (极深隐身模式)"); self.chk_hide.setChecked(self.config.get("hide_browser", False))
        self.chk_hide.stateChanged.connect(self.toggle_browser)
        bottom.addWidget(self.chk_hide)
        layout.addLayout(bottom)

    def init_browser(self):
        from DrissionPage import ChromiumPage, ChromiumOptions
        try:
            co = ChromiumOptions()
            co.set_argument('--no-window-focus')
            co.set_argument('--disable-notifications')
            co.set_pref('profile.default_content_settings.popups', 0)
            co.set_pref('download.prompt_for_download', False)
            self.shared_page = ChromiumPage(co)
            self.shared_page.get("https://x999x.me/forum.php")
            self.shared_page.set.window.show()
            self.add_log_to_all("浏览器已启动，请完成登录。成功后窗口将自动进入静默模式。")
            self.login_monitor_timer.start(2000)
        except Exception as e: QMessageBox.critical(self, "错误", str(e))

    def monitor_login_success(self):
        if self.is_kernel_alive():
            try:
                if any(x in self.shared_page.html for x in ["退出", "logout", "mod=logging&action=logout"]):
                    self.login_monitor_timer.stop()
                    self.add_log_to_all("检测到登录成功！正在切换至静默模式...")
                    if self.chk_hide.isChecked():
                        self.shared_page.set.window.hide()
                        self.shared_page.set.window.location(-3000, -3000)
                    QMessageBox.information(self, "登录成功", "已识别登录状态，内核已转入后台隐身运行。")
            except: pass

    def check_kernel_status(self):
        alive = self.is_kernel_alive()
        self.lbl_kernel_status.setText("● 内核在线" if alive else "● 内核离线")
        self.lbl_kernel_status.setStyleSheet(f"color: {'green' if alive else 'red'}; font-weight: bold; margin-right: 15px;")

    def is_kernel_alive(self):
        if not self.shared_page: return False
        try: return self.shared_page.title is not None
        except: return False

    def preview_cover(self, code):
        if not self.is_kernel_alive(): return
        self.add_log_to_all(f"正在嗅探封面: {code}...")
        from core.avbase_spider import AvbaseSpider
        spider = AvbaseSpider(self.shared_page)
        _, img_url, _ = spider.search_code(code)
        if img_url: ImagePreviewDialog(self, code, img_url).exec()
        else: QMessageBox.information(self, "提示", "未能在 AVBase 找到该号码的封面预览。")

    def add_log_to_all(self, text):
        for s in [self.sec_4k, self.sec_vr, self.sec_hd, self.sec_sub]: s.add_log(text)

    def toggle_browser(self):
        if self.is_kernel_alive():
            try:
                if self.chk_hide.isChecked():
                    self.shared_page.set.window.hide()
                    self.shared_page.set.window.location(-3000, -3000)
                else:
                    self.shared_page.set.window.location(100, 100)
                    self.shared_page.set.window.show()
            except: pass
        self.save_all_config()

    def global_tick(self):
        now = datetime.datetime.now()
        if now.date() > self.last_reset_date:
            self.quotas = {"4k": 0, "vr": 0, "hd": 0, "sub": 0}
            for k, lbl in self.q_lbls.items(): lbl.setText(f"【{k.upper()}: 0/55 】")
            self.last_reset_date = now.date()
        hm = now.strftime("%H:%M")
        for s in [self.sec_4k, self.sec_vr, self.sec_hd, self.sec_sub]:
            if s.timer_enabled.isChecked() and s.btn_start.isEnabled():
                s.timer_status.setText(f"定时触发:{s.timer_time.text()}")
                if hm == s.timer_time.text().strip(): s.start_task()

    def update_quota(self, key):
        self.quotas[key] += 1; self.q_lbls[key].setText(f"【{key.upper()}: {self.quotas[key]}/55 】")
        if self.quotas[key] >= 55: getattr(self, f"sec_{key}").stop_task()

    def save_all_config(self):
        if hasattr(self, 'is_loading') and self.is_loading: return
        for s in [self.sec_4k, self.sec_vr, self.sec_hd, self.sec_sub]:
            self.config[s.key] = {
                'start_page': s.start_page_input.text(), 'history_page': s.history_label.text(),
                'save_path': s.path_input.text(), 'timer_enabled': s.timer_enabled.isChecked(),
                'timer_time': s.timer_time.text(), 'simulate_human': s.chk_simulate.isChecked()
            }
        self.config['hide_browser'] = self.chk_hide.isChecked()
        self.config['rename_settings'] = {'rules': self.sec_rename.rule_input.toPlainText(), 'threads': self.sec_rename.thread_count_spin.text()}
        save_config(self.config)

    def load_all_config(self):
        for s in [self.sec_4k, self.sec_vr, self.sec_hd, self.sec_sub]:
            c = self.config.get(s.key, {})
            s.start_page_input.setText(c.get('start_page', "1"))
            s.history_label.setText(c.get('history_page', "1"))
            s.path_input.setText(c.get('save_path', ""))
            s.timer_enabled.setChecked(c.get('timer_enabled', False))
            s.timer_time.setText(c.get('timer_time', "03:00"))
            s.chk_simulate.setChecked(c.get('simulate_human', True))
            s.refresh_table()
        r = self.config.get('rename_settings', {})
        self.sec_rename.rule_input.setPlainText(r.get('rules', ""))
        self.sec_rename.thread_count_spin.setText(r.get('threads', "3"))

    def closeEvent(self, event):
        if QMessageBox.Yes == QMessageBox.question(self, '确认', "退出程序？"):
            self.save_all_config()
            if self.is_kernel_alive():
                try: self.shared_page.quit()
                except: pass
            event.accept()
        else: event.ignore()

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv); window = MainWindow(); window.show(); sys.exit(app.exec())
    except Exception as e: traceback.print_exc()
