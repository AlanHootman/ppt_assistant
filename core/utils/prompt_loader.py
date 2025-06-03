#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Prompt加载器模块

提供标准YAML格式prompt的加载和渲染功能。
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from jinja2 import Template

from config.settings import settings

logger = logging.getLogger(__name__)

class PromptLoader:
    """Prompt加载器，用于加载和渲染YAML格式的prompt文件"""
    
    def __init__(self):
        """初始化prompt加载器"""
        self.prompts_dir = settings.CONFIG_DIR / "prompts"
        self._cache = {}  # 缓存已加载的prompt
        
    def load_prompt(self, prompt_name: str) -> Dict[str, Any]:
        """
        加载YAML格式的prompt文件
        
        Args:
            prompt_name: prompt文件名（不含扩展名）
            
        Returns:
            prompt配置字典
        """
        # 检查缓存
        if prompt_name in self._cache:
            return self._cache[prompt_name]
            
        # 构建文件路径
        yaml_file = self.prompts_dir / f"{prompt_name}.yaml"
        
        if not yaml_file.exists():
            raise FileNotFoundError(f"Prompt文件不存在: {yaml_file}")
            
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                prompt_config = yaml.safe_load(f)
                
            # 验证必需字段
            self._validate_prompt_config(prompt_config, prompt_name)
            
            # 缓存结果
            self._cache[prompt_name] = prompt_config
            
            logger.info(f"成功加载prompt配置: {prompt_name}")
            return prompt_config
            
        except Exception as e:
            logger.error(f"加载prompt文件失败: {yaml_file}, 错误: {str(e)}")
            raise
    
    def _validate_prompt_config(self, config: Dict[str, Any], prompt_name: str) -> None:
        """
        验证prompt配置的必需字段
        
        Args:
            config: prompt配置
            prompt_name: prompt名称
        """
        required_fields = ['template', 'jinja_args']
        
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Prompt配置 {prompt_name} 缺少必需字段: {field}")
        
        # 验证jinja_args是列表
        if not isinstance(config['jinja_args'], list):
            raise ValueError(f"Prompt配置 {prompt_name} 的jinja_args必须是列表")
    
    def render_prompt(self, prompt_name: str, context: Dict[str, Any]) -> str:
        """
        渲染prompt模板
        
        Args:
            prompt_name: prompt名称
            context: 模板上下文变量
            
        Returns:
            渲染后的prompt文本
        """
        prompt_config = self.load_prompt(prompt_name)
        
        # 检查必需的jinja参数
        required_args = prompt_config['jinja_args']
        missing_args = [arg for arg in required_args if arg not in context]
        
        if missing_args:
            logger.warning(f"Prompt {prompt_name} 缺少参数: {missing_args}")
        
        try:
            # 获取system_prompt（如果有）
            system_prompt = prompt_config.get('system_prompt', '')
            
            # 渲染模板
            template = Template(prompt_config['template'])
            rendered_template = template.render(**context)
            
            # 如果有system_prompt，将其与template合并
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{rendered_template}"
            else:
                full_prompt = rendered_template
                
            return full_prompt
            
        except Exception as e:
            logger.error(f"渲染prompt模板失败: {prompt_name}, 错误: {str(e)}")
            raise
    
    def get_prompt_config(self, prompt_name: str) -> Dict[str, Any]:
        """
        获取prompt的完整配置信息
        
        Args:
            prompt_name: prompt名称
            
        Returns:
            prompt配置字典
        """
        return self.load_prompt(prompt_name)
    
    def clear_cache(self) -> None:
        """清空prompt缓存"""
        self._cache.clear()
        logger.info("已清空prompt缓存")
    
    def list_available_prompts(self) -> List[str]:
        """
        列出所有可用的prompt文件
        
        Returns:
            prompt名称列表
        """
        prompt_files = []
        
        if self.prompts_dir.exists():
            for file_path in self.prompts_dir.glob("*.yaml"):
                prompt_files.append(file_path.stem)
        
        return sorted(prompt_files)

# 创建全局实例
prompt_loader = PromptLoader() 