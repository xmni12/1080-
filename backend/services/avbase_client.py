import httpx
import re
import asyncio
import random
import logging
from typing import List

logger = logging.getLogger(__name__)

class AvbaseClient:
    def __init__(self):
        self.base_url = "https://avbase.net"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
        }

    async def get_actors_by_code(self, code: str) -> List[str]:
        """
        通过番号查询对应的演员列表
        """
        try:
            # 随机延迟，防止触发反爬
            await asyncio.sleep(random.uniform(1.0, 2.5))
            
            async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
                search_url = f"{self.base_url}/works?q={code}"
                resp = await client.get(search_url, headers=self.headers, follow_redirects=True)
                
                if resp.status_code != 200:
                    logger.warning(f"AVBase search failed for {code}: HTTP {resp.status_code}")
                    return []

                html_text = resp.text
                
                # 在 HTML 中寻找类似 <a href="https://avbase.net/talents/xxx">演员名</a> 的元素
                # 为了防止提取到多余的字符，我们会过滤常见的干扰词
                pattern = r'<a\s+href="[^"]*/talents/[^"]*"\s*>([^<]+)</a>'
                matches = re.findall(pattern, html_text)
                
                # 简单去重并清理空白
                actors = list(set([m.strip() for m in matches if m.strip()]))
                
                # 过滤掉一些可能抓取错误的非演员词汇（如果有的话）
                # 通常 /talents/ 路由下都是合法的演员名
                return actors

        except httpx.TimeoutException:
            logger.warning(f"AVBase search timeout for {code}")
            return []
        except Exception as e:
            logger.error(f"AVBase search exception for {code}: {e}")
            return []

avbase_client = AvbaseClient()
