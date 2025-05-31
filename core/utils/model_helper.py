#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
模型调用辅助工具模块

提供与大模型调用相关的辅助功能，包括重试逻辑、结果解析等
"""

import logging
import json
import re
import asyncio
from typing import Dict, Any, Optional, List, Tuple, Callable, Union

from config.settings import settings
from core.llm.model_manager import ModelManager

# 初始化日志
logger = logging.getLogger(__name__)

class ModelHelper:
    """
    模型调用辅助工具类
    封装大模型调用相关的通用功能
    """
    
    def __init__(self, model_manager: Optional[ModelManager] = None):
        """
        初始化模型辅助工具
        
        Args:
            model_manager: 模型管理器实例，如不提供则自动创建
        """
        self.model_manager = model_manager or ModelManager()
        self._owns_model_manager = model_manager is None  # 记录是否拥有ModelManager实例
    
    async def cleanup(self):
        """
        清理资源
        """
        if self._owns_model_manager and self.model_manager:
            try:
                await self.model_manager.close_clients()
            except Exception as e:
                logger.warning(f"清理ModelManager时出错: {e}")
    
    async def __aenter__(self):
        """异步上下文管理器进入"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.cleanup()
    
    def get_model_config(self, config: Dict[str, Any], model_type: str = "text") -> Dict[str, Any]:
        """
        获取模型配置
        
        Args:
            config: Agent 配置
            model_type: 模型类型，默认为 "text"
            
        Returns:
            模型配置字典，包含模型名称、温度和最大 token 数等
        """
        # 从配置获取模型类型和名称
        model_type = config.get("model_type", model_type)
        
        # 获取模型配置
        model_config = self.model_manager.get_model_config(model_type)
        
        # 从配置获取最大重试次数
        max_retries = int(config.get("max_retries", settings.MAX_RETRIES if hasattr(settings, "MAX_RETRIES") else 3))
        
        # 补充重试配置
        model_config["max_retries"] = max_retries
        
        return model_config
    
    async def generate_text_with_retry(self, model: str, prompt: str, 
                                     temperature: Optional[float] = None, 
                                     max_tokens: Optional[int] = None,
                                     max_retries: int = 3,
                                     model_type: str = "text") -> str:
        """
        使用重试机制生成文本
        
        Args:
            model: 模型名称
            prompt: 提示词
            temperature: 温度参数
            max_tokens: 最大 token 数
            max_retries: 最大重试次数
            model_type: 模型类型，用于选择正确的客户端
            
        Returns:
            生成的文本
        """
        retry_count = 0
        last_error = None
        
        # 允许初始尝试 + 重试
        while retry_count <= max_retries:
            try:
                logger.info(f"调用模型 {model} 生成文本，尝试 {retry_count+1}/{max_retries+1}")
                
                # 等待请求间隔
                await self.model_manager._wait_for_request_interval(model_type)
                
                # 根据模型类型选择适当的客户端
                if model_type == "deep_thinking":
                    client = self.model_manager._get_client("deep_thinking")
                else:
                    client = self.model_manager._get_client("text")
                
                # 创建消息
                messages = [{"role": "user", "content": prompt}]
                
                # 调用OpenAI API
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                # 提取结果
                result = response.choices[0].message.content
                return result or ""
                
            except Exception as e:
                last_error = e
                logger.warning(f"调用模型 {model} 生成文本时出错 (尝试 {retry_count+1}/{max_retries+1}): {str(e)}")
                retry_count += 1
                
                # 在重试之间添加短暂延迟
                if retry_count <= max_retries:
                    await asyncio.sleep(min(2 ** retry_count, 10))  # 指数退避，最大10秒
        
        # 如果所有重试都失败，抛出最后一个异常
        error_msg = f"调用模型 {model} 生成文本失败，已重试 {max_retries} 次: {str(last_error)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    async def analyze_image_with_retry(self, model: str, prompt: str, image_path: str,
                                     max_retries: int = 3) -> str:
        """
        使用重试机制分析图像
        
        Args:
            model: 模型名称
            prompt: 提示词
            image_path: 图像路径
            max_retries: 最大重试次数
            
        Returns:
            分析结果文本
        """
        retry_count = 0
        last_error = None
        
        # 允许初始尝试 + 重试
        while retry_count <= max_retries:
            try:
                logger.info(f"使用模型 {model} 分析图像 {image_path}，尝试 {retry_count+1}/{max_retries+1}")
                
                response = await self.model_manager.analyze_image(
                    model=model,
                    prompt=prompt,
                    image_path=image_path
                )
                
                return response
                
            except Exception as e:
                last_error = e
                logger.warning(f"使用模型 {model} 分析图像时出错 (尝试 {retry_count+1}/{max_retries+1}): {str(e)}")
                retry_count += 1
                
                # 在重试之间添加短暂延迟
                if retry_count <= max_retries:
                    await asyncio.sleep(min(2 ** retry_count, 10))  # 指数退避，最大10秒
        
        # 如果所有重试都失败，抛出最后一个异常
        error_msg = f"使用模型 {model} 分析图像失败，已重试 {max_retries} 次: {str(last_error)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    @staticmethod
    def extract_json_from_response(response: str) -> str:
        """
        从响应中提取 JSON 文本
        
        Args:
            response: 响应文本
            
        Returns:
            提取的 JSON 文本
        """
        # 尝试直接解析 JSON 响应
        json_text = response
        
        # 如果响应包含 JSON 代码块，提取它
        if "```json" in response or "```" in response:
            pattern = r"```(?:json)?\s*([\s\S]*?)```"
            matches = re.findall(pattern, response)
            if matches:
                json_text = matches[0].strip()
                
        return json_text
    
    @staticmethod
    def parse_json_response(response: str, default_value: Any = None) -> Any:
        """
        解析 JSON 响应
        
        Args:
            response: 响应文本
            default_value: 解析失败时返回的默认值
            
        Returns:
            解析后的 JSON 对象
        """
        try:
            # 提取 JSON 文本
            json_text = ModelHelper.extract_json_from_response(response)
            
            # 解析 JSON
            return json.loads(json_text)
            
        except Exception as e:
            logger.error(f"解析 JSON 响应失败: {str(e)}")
            return default_value
    
    @staticmethod
    def parse_vision_response(response: str, default_fields: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        解析视觉模型响应，确保结果包含所需字段
        
        Args:
            response: 响应文本
            default_fields: 默认字段值，如 {"has_issues": False, "issues": []}
            
        Returns:
            解析后的结果字典
        """
        try:
            # 提取 JSON 文本
            json_text = ModelHelper.extract_json_from_response(response)
            
            # 解析 JSON
            result = json.loads(json_text)
            
            # 确保结果是字典
            if not isinstance(result, dict):
                raise ValueError("响应不是有效的 JSON 对象")
            
            # 添加默认字段
            if default_fields:
                for key, value in default_fields.items():
                    result.setdefault(key, value)
            
            return result
            
        except Exception as e:
            logger.error(f"解析视觉模型响应时出错: {str(e)}")
            # 返回默认字段或空字典
            return default_fields or {} 