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
        
        logger.info(f"加载系统配置，项目根目录: {self.BASE_DIR}")
    
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