#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
配置加载器模块

提供工作流配置的加载和解析功能。
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
import logging

from config.settings import settings

# 配置日志
logger = logging.getLogger(__name__)

class ConfigLoader:
    """配置文件加载器"""
    
    @staticmethod
    def load_yaml(file_path: Path) -> Dict[str, Any]:
        """
        加载YAML配置文件
        
        Args:
            file_path: YAML文件路径
            
        Returns:
            配置字典
        """
        if not file_path.exists():
            logger.warning(f"Config file not found: {file_path}")
            return {}
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded config from {file_path}")
            return config or {}
        except Exception as e:
            logger.error(f"Failed to load config {file_path}: {str(e)}")
            return {}
    
    @classmethod
    def load_model_config(cls) -> Dict[str, Any]:
        """
        加载模型配置
        
        Returns:
            模型配置字典
        """
        return cls.load_yaml(settings.MODEL_CONFIG_PATH)
    
    @classmethod
    def load_workflow_config(cls, workflow_name: str) -> Dict[str, Any]:
        """
        加载工作流配置
        
        Args:
            workflow_name: 工作流名称
            
        Returns:
            工作流配置字典
        """
        # 确保工作流配置目录存在
        settings.WORKFLOW_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        
        # 获取配置文件路径
        config_path = settings.get_workflow_config_path(workflow_name)
                
        # 读取配置文件
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            logger.info(f"加载配置文件: {config_path}")
            return config
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
    
    @classmethod
    def resolve_env_vars(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析配置中的环境变量
        
        Args:
            config: 配置字典
            
        Returns:
            解析后的配置字典
        """
        if not isinstance(config, dict):
            return config
            
        for key, value in config.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                # 解析环境变量
                env_var = value[2:-1]
                if ":" in env_var:
                    env_name, default = env_var.split(":", 1)
                    config[key] = os.getenv(env_name, default)
                else:
                    config[key] = os.getenv(env_var, "")
            elif isinstance(value, dict):
                # 递归处理嵌套字典
                config[key] = cls.resolve_env_vars(value)
            elif isinstance(value, list):
                # 处理列表
                config[key] = [
                    cls.resolve_env_vars(item) if isinstance(item, dict) else item
                    for item in value
                ]
                
        return config 