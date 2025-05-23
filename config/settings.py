#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
系统配置模块

提供系统全局配置和环境变量处理。
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Settings:
    """系统配置类"""
    
    def __init__(self):
        """初始化配置"""
        # 获取项目根目录
        self.BASE_DIR = Path(__file__).resolve().parent.parent
        
        # 工作空间目录
        self.WORKSPACE_DIR = self.BASE_DIR / "workspace"
        self.WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
        
        # 输出目录
        self.OUTPUT_DIR = self.WORKSPACE_DIR / "output"
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        # 临时文件目录
        self.TEMP_DIR = self.WORKSPACE_DIR / "temp"
        self.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        
        # 会话目录
        self.SESSION_DIR = self.WORKSPACE_DIR / "sessions"
        self.SESSION_DIR.mkdir(parents=True, exist_ok=True)
        
        # 日志目录
        self.LOG_DIR = self.WORKSPACE_DIR / "logs"
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)
        
        # 配置文件目录
        self.CONFIG_DIR = self.BASE_DIR / "config"
        
        # LLM模型配置
        self.OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
        
        # 模型配置路径
        self.MODEL_CONFIG_PATH = self.CONFIG_DIR / "model_config.yaml"
        
        # 工作流配置
        self.WORKFLOW_CONFIG_DIR = self.CONFIG_DIR / "workflow"
        
        # 幻灯片生成配置
        self.MAX_SLIDE_ITERATIONS = int(os.environ.get("MAX_SLIDE_ITERATIONS", "1"))
        self.MAX_VISION_RETRIES = int(os.environ.get("MAX_VISION_RETRIES", "1"))
        
        # 缓存配置
        self.USE_CACHE = os.environ.get("USE_CACHE", "true").lower() in ("true", "1", "yes")
        
        # 缓存目录 - 统一使用cache_manager进行管理
        self.CACHE_DIR = self.WORKSPACE_DIR / "cache"
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        # 模型默认参数配置 - 统一管理所有Agent使用的默认值
        self.MODEL_DEFAULTS = {
            # 各种类型模型的默认参数
            "text": {
                "temperature": float(os.environ.get("LLM_TEMPERATURE", "0.7")),
                "max_tokens": int(os.environ.get("LLM_MAX_TOKENS", "128000"))
            },
            "vision": {
                "temperature": float(os.environ.get("VISION_TEMPERATURE", "0.7")),
                "max_tokens": int(os.environ.get("VISION_MAX_TOKENS", "128000"))
            },
            "embedding": {
                "dimensions": int(os.environ.get("EMBEDDING_DIMENSIONS", "1536"))
            }
        }
        
        logger.info(f"加载系统配置，项目根目录: {self.BASE_DIR}")
    
    def get_model_defaults(self, model_type: str = "text") -> Dict[str, Any]:
        """
        获取指定类型模型的默认参数
        
        Args:
            model_type: 模型类型，支持 text、vision、embedding
            
        Returns:
            模型默认参数字典
        """
        return self.MODEL_DEFAULTS.get(model_type, self.MODEL_DEFAULTS["text"])
    
    def get_workflow_config_path(self, workflow_name: str) -> Path:
        """
        获取工作流配置文件路径
        
        Args:
            workflow_name: 工作流名称
            
        Returns:
            配置文件路径
        """
        return self.WORKFLOW_CONFIG_DIR / f"{workflow_name}.yaml"

# 创建全局配置实例
settings = Settings()