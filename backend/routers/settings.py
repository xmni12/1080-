from fastapi import APIRouter, HTTPException
from backend.schemas import GlobalSettings, SectionSettings, RenameSettings
from core.utils import load_config, save_config

router = APIRouter(prefix="/api/settings", tags=["settings"])

@router.get("", response_model=GlobalSettings)
async def get_settings():
    """
    获取全局配置
    """
    config = load_config()
    
    sections = {}
    rename_settings = RenameSettings()
    hide_browser = config.get("hide_browser", False)
    
    for key, value in config.items():
        if isinstance(value, dict) and key != "rename_settings":
            sections[key] = SectionSettings(**value)
        elif key == "rename_settings":
            rename_settings = RenameSettings(**value)
            
    return GlobalSettings(
        sections=sections,
        hide_browser=hide_browser,
        rename_settings=rename_settings
    )

@router.post("")
async def update_settings(settings: GlobalSettings):
    """
    更新全局配置
    """
    config_data = {}
    
    # 将 sections 重新展开到顶级
    for section_name, section_data in settings.sections.items():
        config_data[section_name] = section_data.model_dump()
        
    config_data["hide_browser"] = settings.hide_browser
    config_data["rename_settings"] = settings.rename_settings.model_dump()
    
    save_config(config_data)
    return {"status": "success", "message": "Settings updated"}
