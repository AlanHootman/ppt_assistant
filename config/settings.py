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
        
        # 上传文件目录
        self.UPLOAD_DIR = self.WORKSPACE_DIR / "uploads"
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        
        # 数据库目录
        self.DB_DIR = self.WORKSPACE_DIR / "db"
        self.DB_DIR.mkdir(parents=True, exist_ok=True)
        
        # 工作流配置
        self.WORKFLOW_CONFIG_DIR = self.CONFIG_DIR / "workflow"
        
        # 幻灯片生成配置
        self.MAX_SLIDE_ITERATIONS = int(os.environ.get("MAX_SLIDE_ITERATIONS", "1"))
        self.MAX_VISION_RETRIES = int(os.environ.get("MAX_VISION_RETRIES", "1"))
        
        # 幻灯片生成并行处理配置
        self.USE_PARALLEL_GENERATION = os.environ.get("USE_PARALLEL_GENERATION", "false").lower() in ("true", "1", "yes")
        self.GENERATION_MAX_WORKERS = int(os.environ.get("GENERATION_MAX_WORKERS", "0")) or None
        
        # 幻灯片验证并行处理配置
        self.USE_PARALLEL_VALIDATION = os.environ.get("USE_PARALLEL_VALIDATION", "false").lower() in ("true", "1", "yes")
        self.VALIDATION_MAX_WORKERS = int(os.environ.get("VALIDATION_MAX_WORKERS", "0")) or None
        
        # PPT分析并行处理配置
        self.USE_PARALLEL_ANALYSIS = os.environ.get("USE_PARALLEL_ANALYSIS", "false").lower() in ("true", "1", "yes")
        self.ANALYSIS_MAX_WORKERS = int(os.environ.get("ANALYSIS_MAX_WORKERS", "0")) or None
        
        # 缓存配置
        self.USE_CACHE = os.environ.get("USE_CACHE", "true").lower() in ("true", "1", "yes")
        
        # 缓存目录 - 统一使用cache_manager进行管理
        self.CACHE_DIR = self.WORKSPACE_DIR / "cache"
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        # 模型请求间隔配置（毫秒）
        self.MODEL_REQUEST_INTERVALS = {
            "text": int(os.environ.get("TEXT_MODEL_REQUEST_INTERVAL", "100")),      # 文本模型请求间隔
            "vision": int(os.environ.get("VISION_MODEL_REQUEST_INTERVAL", "200")), # 视觉模型请求间隔
            "deep_thinking": int(os.environ.get("DEEPTHINK_MODEL_REQUEST_INTERVAL", "150")), # 深度思考模型请求间隔
            "embedding": int(os.environ.get("EMBEDDING_MODEL_REQUEST_INTERVAL", "50"))  # 嵌入模型请求间隔
        }
        
        logger.info(f"加载系统配置，项目根目录: {self.BASE_DIR}")
    
    def get_model_defaults(self, model_type: str) -> Dict[str, Any]:
        """
        获取指定模型类型的默认参数
        
        Args:
            model_type: 模型类型 (text, vision, deep_thinking, embedding)
            
        Returns:
            包含默认参数的字典
        """
        # 根据模型类型返回相应的默认参数
        if model_type == "text":
            return {
                "temperature": float(os.environ.get("LLM_TEMPERATURE", "0.2")),
                "max_tokens": int(os.environ.get("LLM_MAX_TOKENS", "32768"))
            }
        elif model_type == "vision":
            return {
                "temperature": float(os.environ.get("VISION_TEMPERATURE", "0.2")),
                "max_tokens": int(os.environ.get("VISION_MAX_TOKENS", "32768"))
            }
        elif model_type == "deep_thinking":
            return {
                "temperature": float(os.environ.get("DEEPTHINK_TEMPERATURE", "0.2")),
                "max_tokens": int(os.environ.get("DEEPTHINK_MAX_TOKENS", "40960"))
            }
        elif model_type == "embedding":
            return {
                "dimensions": int(os.environ.get("EMBEDDING_DIMENSIONS", "1536"))
            }
        else:
            # 对于未知类型，返回文本模型的默认参数
            logger.warning(f"未知模型类型: {model_type}，使用text类型默认参数")
            return {
                "temperature": float(os.environ.get("LLM_TEMPERATURE", "0.2")),
                "max_tokens": int(os.environ.get("LLM_MAX_TOKENS", "32768"))
            }
    
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