from fastapi import APIRouter, HTTPException
from backend.schemas import GlobalSettings, SectionSettings
from core.utils import load_config, save_config
from backend.services.scheduler_service import scheduler_service

router = APIRouter(prefix="/api/settings", tags=["settings"])

@router.get("", response_model=GlobalSettings)
async def get_settings():
    """
    获取全局配置
    """
    config = load_config()
    
    sections = {}
    hide_browser = config.get("hide_browser", False)
    spider_threads = config.get("spider_threads", 1)
    browser_path = config.get("browser_path", "")
    
    for key, value in config.items():
        if isinstance(value, dict) and key != "sections":
            sections[key] = SectionSettings(**value)
        elif key == "sections":
            for sub_k, sub_v in value.items():
                sections[sub_k] = SectionSettings(**sub_v)
            
    return GlobalSettings(
        sections=sections,
        hide_browser=hide_browser,
        spider_threads=spider_threads,
        browser_path=browser_path
    )

@router.post("")
async def update_settings(settings: GlobalSettings):
    """
    更新全局配置
    """
    config_data = {"sections": {}}
    
    for section_name, section_data in settings.sections.items():
        config_data["sections"][section_name] = section_data.model_dump()
        
    config_data["hide_browser"] = settings.hide_browser
    config_data["spider_threads"] = settings.spider_threads
    config_data["browser_path"] = settings.browser_path
    
    save_config(config_data)
    
    # 重载定时任务
    scheduler_service.setup_jobs()
    
    return {"status": "success", "message": "Settings updated"}
