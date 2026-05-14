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
                # 提取 /talents/ 后面的 URL 编码的演员名称，无视 A 标签内部复杂的嵌套结构
                pattern = r'href=["\'][^"\']*/talents/([^"\']+)["\']'
                matches = re.findall(pattern, html_text)
                
                # 解码、去重并清理空白
                actors = list(set([urllib.parse.unquote(m).strip() for m in matches if m.strip()]))
                
                return actors

        except Exception as e:
            logger.error(f"AVBase search exception for {code}: {e}")
            return []

avbase_client = AvbaseClient()
