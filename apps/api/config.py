from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path

class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "PPT Assistant API"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # 数据库配置
    DATABASE_URL: str = "sqlite:///./ppt_assistant.db"
    
    # Redis配置
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Celery配置
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # JWT配置
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 文件存储配置
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    STATIC_DIR: Path = BASE_DIR / "static"
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    
    # WebSocket配置
    WS_HEARTBEAT_INTERVAL: int = 30
    
    # 工作空间配置
    WORKSPACE_DIR: Path = BASE_DIR / "workspace"
    OUTPUT_DIR: Path = WORKSPACE_DIR / "output"
    TEMP_DIR: Path = WORKSPACE_DIR / "temp"
    SESSION_DIR: Path = WORKSPACE_DIR / "sessions"
    LOG_DIR: Path = WORKSPACE_DIR / "logs"
    CACHE_DIR: Path = WORKSPACE_DIR / "cache"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # 确保目录存在
        for dir_path in [
            self.UPLOAD_DIR, 
            self.STATIC_DIR,
            self.WORKSPACE_DIR,
            self.OUTPUT_DIR,
            self.TEMP_DIR,
            self.SESSION_DIR,
            self.LOG_DIR,
            self.CACHE_DIR,
            self.STATIC_DIR / "templates",
            self.STATIC_DIR / "output"
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings() 