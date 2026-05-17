import httpx
import logging
import re
from typing import List, Set
from core.utils import extract_code

logger = logging.getLogger(__name__)

class EmbyClient:
    def __init__(self):
        self.base_url = "http://192.168.31.77:8091"
        self.api_key = "6b27a306836f49c3ac7b63af43736a0e"

    async def get_all_movie_codes(self) -> Set[str]:
        """
        获取 Emby 媒体库中所有电影的番号
        """
        owned_codes = set()
        try:
            url = f"{self.base_url}/emby/Items"
            params = {
                "Recursive": "true",
                "IncludeItemTypes": "Movie",
                "api_key": self.api_key,
                "Fields": "Name,OriginalTitle"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    logger.error(f"Emby API failed: {resp.status_code}")
                    return owned_codes
                
                data = resp.json()
                items = data.get("Items", [])
                
                for item in items:
                    name = item.get("Name", "")
                    original_title = item.get("OriginalTitle", "")
                    
                    code = extract_code(name)
                    if not code:
                        code = extract_code(original_title)
                        
                    if code:
                        owned_codes.add(code.upper())
                        
        except Exception as e:
            logger.error(f"Emby get_all_movie_codes exception: {e}")
            
        return owned_codes

emby_client = EmbyClient()
