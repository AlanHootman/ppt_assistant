"""
应用全局配置模块
"""
import os
from pathlib import Path
from typing import Dict, Any

class Settings:
    """全局配置类"""
    
    # 项目基础路径
    BASE_DIR: Path = Path(__file__).parent.parent.resolve()
    
    # 工作空间
    WORKSPACE_DIR: Path = BASE_DIR / "workspace"
    
    # 配置文件路径
    CONFIG_DIR: Path = BASE_DIR / "config"
    
    # 日志配置
    LOG_DIR: Path = WORKSPACE_DIR / "logs"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # 工作流配置
    WORKFLOW_CONFIG_DIR: Path = CONFIG_DIR / "workflow_config"
    
    # 模型配置
    MODEL_CONFIG_PATH: Path = CONFIG_DIR / "model_config.yaml"
    
    # 会话存储
    SESSION_DIR: Path = WORKSPACE_DIR / "sessions"
    
    def __init__(self):
        """初始化时创建必要目录"""
        self._create_directories()
    
    def _create_directories(self):
        """创建必要的目录结构"""
        for path in [self.WORKSPACE_DIR, self.LOG_DIR, 
                    self.SESSION_DIR, self.WORKFLOW_CONFIG_DIR]:
            path.mkdir(parents=True, exist_ok=True)

# 全局配置实例
settings = Settings() 