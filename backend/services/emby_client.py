import httpx
import logging
import re
from typing import List, Set
from core.utils import extract_code, load_config

logger = logging.getLogger(__name__)

class EmbyClient:
    def __init__(self):
        pass

    def _get_config(self):
        config = load_config()
        return config.get('emby', {})

    async def get_all_movie_codes(self) -> Set[str]:
        """
        获取 Emby 媒体库中所有电影的番号
        """
        emby_conf = self._get_config()
        if not emby_conf.get('enabled'):
            logger.info("Emby API is disabled in settings.")
            return set()
            
        base_url = emby_conf.get('server_url', '').rstrip('/')
        api_key = emby_conf.get('api_key', '')
        
        if not base_url or not api_key:
            logger.warning("Emby configuration is incomplete.")
            return set()

        owned_codes = set()
        try:
            url = f"{base_url}/emby/Items"
            params = {
                "Recursive": "true",
                "IncludeItemTypes": "Movie",
                "api_key": api_key,
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
