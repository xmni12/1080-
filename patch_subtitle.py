import re
import os

def patch_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Spider Service replacement
    if 'spider_service.py' in filepath:
        old_block = '''                            # 方案二：穿透检测真实文件魔数 (Magic Number)
                            if content_head.startswith(b'Rar!\\x1a\\x07'):
                                ext = ".rar"
                            elif content_head.startswith(b'PK\\x03\\x04'):
                                ext = ".zip"
                            elif content_head.startswith(b'7z\\xbc\\xaf\\x27\\x1c'):
                                ext = ".7z"
                            elif content_head.startswith(b'd8:announce') or content_head.startswith(b'd4:info') or b':announce' in content_head:
                                ext = ".torrent"
                            else:
                                # 魔数不匹配任何已知压缩包或种子，说明大概率下载到了伪装成 200 的 HTML 报错页
                                debug_file = os.path.join(save_path, f"debug_{code}.html")
                                with open(debug_file, "wb") as f:
                                    f.write(dl_resp.content)
                                logger.error(f"[{code}] Invalid content dumped to {debug_file}")
                                return "INVALID_FILE_CONTENT"'''

        new_block = '''                            # 提取 Content-Disposition 中的真实文件名
                            cd = dl_resp.headers.get("Content-Disposition", "")
                            server_ext = ""
                            if "filename=" in cd:
                                import urllib.parse
                                # 处理可能的 URL 编码文件名
                                filename_raw = cd.split("filename=")[-1].strip('"\\\'')
                                filename_decoded = urllib.parse.unquote(filename_raw)
                                server_ext = os.path.splitext(filename_decoded)[1].lower()

                            # 方案二：穿透检测真实文件魔数 (Magic Number) 与字幕文件放行
                            is_valid = False
                            if content_head.startswith(b'Rar!\\x1a\\x07'):
                                ext = ".rar"
                                is_valid = True
                            elif content_head.startswith(b'PK\\x03\\x04'):
                                ext = ".zip"
                                is_valid = True
                            elif content_head.startswith(b'7z\\xbc\\xaf\\x27\\x1c'):
                                ext = ".7z"
                                is_valid = True
                            elif content_head.startswith(b'd8:announce') or content_head.startswith(b'd4:info') or b':announce' in content_head:
                                ext = ".torrent"
                                is_valid = True
                            elif server_ext in ['.srt', '.ass', '.vtt', '.txt'] and not content_head.strip().startswith(b'<'):
                                # 如果是文本字幕格式，且不以 HTML 标签开头，则放行
                                ext = server_ext
                                is_valid = True
                            
                            if not is_valid:
                                # 魔数不匹配任何已知压缩包或种子，说明大概率下载到了伪装成 200 的 HTML 报错页
                                debug_file = os.path.join(save_path, f"debug_{code}.html")
                                with open(debug_file, "wb") as f:
                                    f.write(dl_resp.content)
                                logger.error(f"[{code}] Invalid content dumped to {debug_file} (server_ext: {server_ext})")
                                return "INVALID_FILE_CONTENT"'''
        content = content.replace(old_block, new_block)

    # Task Manager replacement
    if 'task_manager.py' in filepath:
        old_block_tm = '''                                        if content_head.startswith(b'Rar!\\x1a\\x07'): ext = ".rar"
                                        elif content_head.startswith(b'PK\\x03\\x04'): ext = ".zip"
                                        elif content_head.startswith(b'7z\\xbc\\xaf\\x27\\x1c'): ext = ".7z"
                                        elif content_head.startswith(b'd8:announce') or content_head.startswith(b'd4:info') or b':announce' in content_head: ext = ".torrent"
                                        else:
                                            dl_res = "INVALID_FILE_CONTENT"
                                            continue'''
                                            
        new_block_tm = '''                                        cd = dl_resp.headers.get("Content-Disposition", "")
                                        server_ext = ""
                                        if "filename=" in cd:
                                            import urllib.parse
                                            filename_raw = cd.split("filename=")[-1].strip('"\\\'')
                                            server_ext = os.path.splitext(urllib.parse.unquote(filename_raw))[1].lower()

                                        is_valid = False
                                        if content_head.startswith(b'Rar!\\x1a\\x07'): 
                                            ext = ".rar"
                                            is_valid = True
                                        elif content_head.startswith(b'PK\\x03\\x04'): 
                                            ext = ".zip"
                                            is_valid = True
                                        elif content_head.startswith(b'7z\\xbc\\xaf\\x27\\x1c'): 
                                            ext = ".7z"
                                            is_valid = True
                                        elif content_head.startswith(b'd8:announce') or content_head.startswith(b'd4:info') or b':announce' in content_head: 
                                            ext = ".torrent"
                                            is_valid = True
                                        elif server_ext in ['.srt', '.ass', '.vtt', '.txt'] and not content_head.strip().startswith(b'<'):
                                            ext = server_ext
                                            is_valid = True
                                            
                                        if not is_valid:
                                            dl_res = "INVALID_FILE_CONTENT"
                                            continue'''
        content = content.replace(old_block_tm, new_block_tm)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

patch_file('backend/services/spider_service.py')
patch_file('backend/services/task_manager.py')
print("Subtitle extension patch applied.")
