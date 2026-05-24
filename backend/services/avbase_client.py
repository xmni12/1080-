from curl_cffi.requests import AsyncSession as CurlAsyncSession
import re
import asyncio
import random
import logging
from typing import List

logger = logging.getLogger(__name__)

class AvbaseClient:
    def __init__(self):
        self.base_url = "https://avbase.net"

    async def get_actors_by_code(self, code: str) -> List[str]:
        """
        通过番号查询对应的演员列表
        """
        try:
            # 随机延迟，防止触发反爬
            await asyncio.sleep(random.uniform(1.0, 2.5))
            
            async with CurlAsyncSession(impersonate='chrome120', timeout=15.0) as client:
                search_url = f"{self.base_url}/works?q={code}"
                resp = await client.get(search_url)
                
                if resp.status_code != 200:
                    logger.warning(f"AVBase search failed for {code}: HTTP {resp.status_code}")
                    return []

                html_text = resp.text
                
                import urllib.parse
                
                # 匹配整个 <a href="/talents/xxx">...</a> 块
                a_tags = re.findall(r'(<a\s+[^>]*href=["\'][^"\']*/talents/[^"\']+["\'][^>]*>.*?</a>)', html_text)
                
                actors = []
                seen = set()
                for a_tag in a_tags:
                    # 提取名字 (URL编码)
                    name_match = re.search(r'href=["\'][^"\']*/talents/([^"\']+)["\']', a_tag)
                    if not name_match:
                        continue
                    name = urllib.parse.unquote(name_match.group(1)).strip()
                    # 强行截断可能附带的 ?actor_id 等参数
                    if "?" in name:
                        name = name.split("?")[0]

                    if not name or name in seen:
                        continue
                        
                    # 尝试提取头像 URL
                    img_match = re.search(r'src=["\']([^"\']+\.(?:jpg|png|jpeg|webp))["\']', a_tag)
                    avatar_url = img_match.group(1) if img_match else None
                    
                    actors.append({
                        "name": name,
                        "avatar_url": avatar_url
                    })
                    seen.add(name)
                
                return actors

        except Exception as e:
            logger.error(f"AVBase search exception for {code}: {e}")
            return []

    async def get_works_by_talent_url(self, talent_url: str):
        """
        获取演员主页下的所有作品番号及链接 (支持跨越多页的全量抓取)
        """
        try:
            import urllib.parse
            from bs4 import BeautifulSoup
            from core.utils import extract_code
            
            # Extract talent name from URL
            match = re.search(r'/talents/([^/]+)', talent_url)
            actor_name = urllib.parse.unquote(match.group(1)) if match else "未知演员"
            
            works = []
            seen = set()
            max_page = 1
            current_page = 1
            
            async with CurlAsyncSession(impersonate='chrome120', timeout=20.0) as client:
                while current_page <= max_page:
                    await asyncio.sleep(random.uniform(1.0, 2.5))
                    
                    page_url = f"{talent_url}?page={current_page}" if current_page > 1 else talent_url
                    logger.info(f"AVBase fetching {actor_name} works page {current_page} / {max_page}...")
                    
                    resp = await client.get(page_url)
                    
                    if resp.status_code != 200:
                        logger.warning(f"AVBase talent fetch failed for {page_url}: HTTP {resp.status_code}")
                        break

                    html_text = resp.text
                    soup = BeautifulSoup(html_text, 'lxml')
                    
                    # 第一页时，解析底部分页组件，找出最大页码
                    if current_page == 1:
                        pagination_links = soup.find_all('a', href=re.compile(r'page=\d+'))
                        for a in pagination_links:
                            href = a.get('href', '')
                            m = re.search(r'page=(\d+)', href)
                            if m:
                                p_num = int(m.group(1))
                                if p_num > max_page:
                                    max_page = p_num
                    
                    title_links = soup.select('a.text-md.font-bold')
                    
                    page_works_count = 0
                    for a in title_links:
                        href = a.get('href')
                        if href and '/works/' in href:
                            raw_code = href.split('/')[-1]
                            clean_code = extract_code(raw_code)
                            if not clean_code:
                                clean_code = extract_code(raw_code.split(':')[-1]) if ':' in raw_code else raw_code.upper()
                                
                            if clean_code and clean_code not in seen:
                                seen.add(clean_code)
                                works.append({
                                    "code": clean_code,
                                    "avbase_url": f"https://www.avbase.net{href}"
                                })
                                page_works_count += 1
                                
                    # 如果当前页没有解析到任何新作品，可能到底了
                    if page_works_count == 0:
                        break
                        
                    current_page += 1
                    
            return {"actor_name": actor_name, "works": works}

        except Exception as e:
            logger.error(f"AVBase talent fetch exception: {e}")
            return {"actor_name": "未知演员", "works": []}

avbase_client = AvbaseClient()
