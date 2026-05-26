from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from backend.schemas import GlobalSettings, SectionSettings
from core.utils import load_config, save_config
from backend.services.scheduler_service import scheduler_service
from backend.services.cleanup_service import cleanup_service
import os
import zipfile
import tempfile
import time

router = APIRouter(prefix="/api/settings", tags=["settings"])

@router.post("/cleanup")
async def trigger_cleanup():
    """
    手动触发系统垃圾回收与深度清理
    """
    try:
        results = await cleanup_service.execute_cleanup()
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/backup")
async def backup_data():
    """
    导出配置与数据库备份 (zip)
    """
    try:
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        zip_filename = f"discuz_spider_backup_{timestamp}.zip"
        zip_filepath = os.path.join(tempfile.gettempdir(), zip_filename)
        
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
            if os.path.exists("data/config_v4.json"):
                zipf.write("data/config_v4.json", "config_v4.json")
            if os.path.exists("data/spider_v5.db"):
                zipf.write("data/spider_v5.db", "spider_v5.db")
                
        return FileResponse(
            path=zip_filepath, 
            filename=zip_filename,
            media_type="application/zip",
            background=None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/restore")
async def restore_data(file: UploadFile = File(...)):
    """
    导入配置与数据库备份 (zip)
    """
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="必须上传 .zip 格式的备份文件")
        
    try:
        temp_dir = tempfile.mkdtemp()
        temp_zip_path = os.path.join(temp_dir, "uploaded_backup.zip")
        
        with open(temp_zip_path, "wb") as f:
            content = await file.read()
            f.write(content)
            
        with zipfile.ZipFile(temp_zip_path, 'r') as zipf:
            # 安全检查
            namelist = zipf.namelist()
            if "config_v4.json" not in namelist and "spider_v5.db" not in namelist:
                raise HTTPException(status_code=400, detail="未在压缩包内发现有效的数据文件")
                
            os.makedirs("data", exist_ok=True)
            
            if "config_v4.json" in namelist:
                zipf.extract("config_v4.json", "data/")
            if "spider_v5.db" in namelist:
                # 为了防止数据库锁死，最好不要在运行大任务时恢复。但这里直接覆盖。
                zipf.extract("spider_v5.db", "data/")
                
        # 重新加载定时任务
        scheduler_service.setup_jobs()
        
        return {"status": "success", "message": "数据恢复成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
