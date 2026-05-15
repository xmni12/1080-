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

avbase_client = AvbaseClient()
