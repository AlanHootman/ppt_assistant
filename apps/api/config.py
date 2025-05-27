from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path
import sys
import os

# 添加项目根目录到系统路径，确保能够导入config.settings
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config.settings import settings as core_settings

class APISettings(BaseSettings):
    # 应用配置
    APP_NAME: str = "PPT Assistant API"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # 复用核心配置中的路径设置
    BASE_DIR: Path = core_settings.BASE_DIR
    WORKSPACE_DIR: Path = core_settings.WORKSPACE_DIR
    OUTPUT_DIR: Path = core_settings.OUTPUT_DIR
    TEMP_DIR: Path = core_settings.TEMP_DIR
    SESSION_DIR: Path = core_settings.SESSION_DIR
    LOG_DIR: Path = core_settings.LOG_DIR
    CACHE_DIR: Path = core_settings.CACHE_DIR
    
    # API服务特有的目录配置
    UPLOAD_DIR: Path = WORKSPACE_DIR / "uploads"
    DB_DIR: Path = WORKSPACE_DIR / "db"
    
    # 数据库配置
    DATABASE_URL: str = f"sqlite:///{DB_DIR}/ppt_assistant.db"
    
    # Redis配置
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Celery配置
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # JWT配置
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 文件大小限制
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    
    # WebSocket配置
    WS_HEARTBEAT_INTERVAL: int = 30
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # 确保API特有目录存在
        for dir_path in [
            self.UPLOAD_DIR,
            self.DB_DIR,
            self.CACHE_DIR / "ppt_analysis",
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # 允许额外字段，这样就不会因为环境变量中存在未在类中定义的字段而报错
        extra = "allow"

settings = APISettings() 