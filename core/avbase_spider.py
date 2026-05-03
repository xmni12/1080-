import time
import re
import os

CODE_REGEX = r'[a-zA-Z]{2,12}-\d{3,6}'

class AvbaseSpider:
    def __init__(self, page):
        self.page = page

    def search_code(self, keyword):
        """利用 DrissionPage 在 avbase 上搜索正确的番号，返回 (code, img_url, error_msg)"""
        if not keyword:
            return None, None, "关键词为空"
        try:
            self.page.get("https://www.avbase.net/")
            time.sleep(1.0)
            
            search_box = self.page.ele('tag:input')
            if search_box:
                search_box.clear()
                search_box.input(f"{keyword}\n")
                self.page.wait.ele_displayed('css:.movie-box, span.font-bold.text-gray-500', timeout=8)
                time.sleep(0.5) # Allow page to settle
            else:
                return None, None, "未找到搜索框"
            
            # 定位番号和封面
            # 封面通常在 .movie-box 或者详情页的 img
            img_url = None
            movie_img = self.page.ele('css:img.movie-img') or self.page.ele('css:.movie-box img')
            if movie_img:
                img_url = movie_img.attr('src')

            # 策略1: 精准定位
            target_span = self.page.ele('css:span.font-bold.text-gray-500')
            if target_span:
                match = re.search(CODE_REGEX, target_span.text)
                if match:
                    return match.group(0).upper(), img_url, ""
                    
            # 策略2: 标题
            title = self.page.title
            match = re.search(CODE_REGEX, title)
            if match:
                return match.group(0).upper(), img_url, ""
                
            # 策略3: 搜索结果
            first_link = self.page.ele('tag:a@@class:title') or self.page.ele('css:.movie-box')
            if first_link:
                match = re.search(CODE_REGEX, first_link.text)
                if match:
                    # 如果刚才没拿到图，去链接里拿或者重新尝试
                    if not img_url:
                        img_ele = first_link.ele('tag:img')
                        if img_ele: img_url = img_ele.attr('src')
                    return match.group(0).upper(), img_url, ""

            return None, None, "未找到匹配番号"
        except Exception as e:
            return None, None, f"异常: {str(e)}"
