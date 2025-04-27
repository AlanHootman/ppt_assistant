#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
大模型管理器模块

提供对各种大模型的统一访问接口，支持文本生成、嵌入和多模态能力。
"""

import os
import logging
import json
import asyncio
import base64
from typing import Dict, Any, List, Optional, Union
import httpx

# 引入OpenAI官方库
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from openai.types.chat import ChatCompletionUserMessageParam

from config.settings import settings

logger = logging.getLogger(__name__)

class ModelManager:
    """大模型统一管理器"""
    
    def __init__(self):
        """初始化模型管理器"""
        # 加载model_config配置
        import yaml
        with open(settings.MODEL_CONFIG_PATH, 'r', encoding='utf-8') as f:
            self.model_config = yaml.safe_load(f)
        
        # 获取各类模型的API配置
        self.default_api_key = os.environ.get("OPENAI_API_KEY", "")
        self.default_base_url = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")
        self.default_organization = os.environ.get("OPENAI_ORGANIZATION", "")
        
        # 各类模型专用配置
        openai_config = self.model_config.get("openai", {})
        
        # LLM配置
        llm_config = openai_config.get("text", {})
        self.llm_api_key = os.environ.get("LLM_API_KEY", self.default_api_key)
        self.llm_base_url = os.environ.get("LLM_API_BASE", self.default_base_url)
        
        # Embedding配置
        embedding_config = openai_config.get("embedding", {})
        self.embedding_api_key = os.environ.get("EMBEDDING_API_KEY", self.default_api_key)
        self.embedding_base_url = os.environ.get("EMBEDDING_API_BASE", self.default_base_url)
        
        # Vision配置
        vision_config = openai_config.get("vision", {})
        self.vision_api_key = os.environ.get("VISION_API_KEY", self.default_api_key)
        self.vision_base_url = os.environ.get("VISION_API_BASE", self.default_base_url)
        
        # 缓存客户端
        self._clients = {}
        
        logger.info("初始化大模型管理器")
    
    def _get_client(self, client_type: str) -> AsyncOpenAI:
        """
        获取或创建指定类型的OpenAI客户端
        
        Args:
            client_type: 客户端类型，支持'llm', 'embedding', 'vision'
            
        Returns:
            对应类型的客户端
        """
        if client_type in self._clients:
            return self._clients[client_type]
        
        # 根据类型选择API密钥和基础URL
        if client_type == "llm":
            api_key = self.llm_api_key
            base_url = self.llm_base_url
        elif client_type == "embedding":
            api_key = self.embedding_api_key
            base_url = self.embedding_base_url
        elif client_type == "vision":
            api_key = self.vision_api_key
            base_url = self.vision_base_url
        else:
            # 默认使用全局配置
            api_key = self.default_api_key
            base_url = self.default_base_url
        
        # 创建客户端
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            organization=self.default_organization
        )
        
        # 缓存客户端
        self._clients[client_type] = client
        
        return client
    
    async def generate_text(self, 
                           model: str, 
                           prompt: str, 
                           temperature: float = 0.7, 
                           max_tokens: int = 1000,
                           top_p: float = 1.0,
                           stop: Optional[List[str]] = None) -> str:
        """
        调用大模型生成文本
        
        Args:
            model: 模型名称
            prompt: 提示词
            temperature: 温度参数
            max_tokens: 最大生成token数
            top_p: Top-p采样参数
            stop: 停止生成的标记
            
        Returns:
            生成的文本
        """
        logger.info(f"调用大模型生成文本: {model}")
        
        # 根据模型名称判断使用哪个提供商的API
        if model.startswith("gpt-"):
            return await self._call_openai_completion(
                model=model, 
                prompt=prompt, 
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                stop=stop
            )
        else:
            # 默认使用OpenAI
            logger.warning(f"未知模型类型: {model}，使用OpenAI API")
            return await self._call_openai_completion(
                model="gpt-3.5-turbo", 
                prompt=prompt, 
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                stop=stop
            )
    
    async def generate_embedding(self, model: str, text: str) -> List[float]:
        """
        生成文本嵌入向量
        
        Args:
            model: 模型名称
            text: 输入文本
            
        Returns:
            嵌入向量
        """
        logger.info(f"生成文本嵌入: {model}")
        
        if model.startswith("text-embedding"):
            return await self._call_openai_embedding(model=model, text=text)
        else:
            # 默认使用OpenAI
            logger.warning(f"未知嵌入模型: {model}，使用OpenAI嵌入模型")
            return await self._call_openai_embedding(model="text-embedding-3-large", text=text)
    
    async def analyze_image(self, model: str, image_path: str, prompt: str) -> str:
        """
        分析图像内容
        
        Args:
            model: 模型名称
            image_path: 图像文件路径
            prompt: 分析提示词
            
        Returns:
            分析结果
        """
        logger.info(f"分析图像: {model}, {image_path}")
        
        if model.startswith("gpt-4-vision"):
            return await self._call_openai_vision(model=model, image_path=image_path, prompt=prompt)
        else:
            # 默认使用OpenAI的vision模型
            logger.warning(f"未知视觉模型: {model}，使用OpenAI视觉模型")
            return await self._call_openai_vision(model="gpt-4-vision", image_path=image_path, prompt=prompt)
    
    async def _call_openai_completion(self, 
                                     model: str, 
                                     prompt: str, 
                                     temperature: float,
                                     max_tokens: int,
                                     top_p: float,
                                     stop: Optional[List[str]]) -> str:
        """
        调用OpenAI文本生成API
        
        Args:
            model: 模型名称
            prompt: 提示词
            temperature: 温度参数
            max_tokens: 最大生成token数
            top_p: Top-p采样参数
            stop: 停止生成的标记
            
        Returns:
            生成的文本
        """
        # 检查API密钥
        if not self.llm_api_key:
            raise ValueError("LLM API密钥未设置")
        
        # 模拟API调用（开发环境）
        if os.environ.get("DEV_ENV") == "true":
            logger.info(f"[DEV] 模拟OpenAI API请求: {model}")
            await asyncio.sleep(1)  # 模拟网络延迟
            return "这是一个模拟的OpenAI API响应"
        
        try:
            # 获取LLM客户端
            client = self._get_client("llm")
            
            # 创建消息
            messages: List[ChatCompletionMessageParam] = [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            # 调用OpenAI API
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                stop=stop
            )
            
            # 提取结果
            result = response.choices[0].message.content
            
            return result or ""
                
        except Exception as e:
            logger.error(f"调用OpenAI API失败: {str(e)}")
            raise
    
    async def _call_openai_embedding(self, model: str, text: str) -> List[float]:
        """
        调用OpenAI嵌入API
        
        Args:
            model: 模型名称
            text: 输入文本
            
        Returns:
            嵌入向量
        """
        # 检查API密钥
        if not self.embedding_api_key:
            raise ValueError("Embedding API密钥未设置")
        
        # 模拟API调用（开发环境）
        if os.environ.get("DEV_ENV") == "true":
            logger.info(f"[DEV] 模拟OpenAI嵌入API请求: {model}")
            await asyncio.sleep(0.5)  # 模拟网络延迟
            return [0.1] * 10  # 返回模拟的嵌入向量
        
        try:
            # 获取Embedding客户端
            client = self._get_client("embedding")
            
            # 调用OpenAI API
            response = await client.embeddings.create(
                model=model,
                input=text
            )
            
            # 提取嵌入向量
            embedding = response.data[0].embedding
            
            return embedding
                
        except Exception as e:
            logger.error(f"调用OpenAI嵌入API失败: {str(e)}")
            raise
    
    async def _call_openai_vision(self, model: str, image_path: str, prompt: str) -> str:
        """
        调用OpenAI视觉API
        
        Args:
            model: 模型名称
            image_path: 图像文件路径
            prompt: 分析提示词
            
        Returns:
            分析结果
        """
        # 检查API密钥
        if not self.vision_api_key:
            raise ValueError("Vision API密钥未设置")
            
        # 检查图像文件是否存在
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图像文件不存在: {image_path}")
        
        # 模拟API调用（开发环境）
        if os.environ.get("DEV_ENV") == "true":
            logger.info(f"[DEV] 模拟OpenAI视觉API请求: {model}")
            await asyncio.sleep(1.5)  # 模拟网络延迟
            return "这是一个模拟的OpenAI视觉API响应，分析了图像内容"
        
        try:
            # 获取Vision客户端
            client = self._get_client("vision")
            
            # 读取图像文件并进行base64编码
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            # 准备消息内容
            content = [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                }
            ]
            
            # 调用OpenAI API
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                max_tokens=1000
            )
            
            # 提取结果
            result = response.choices[0].message.content
            
            return result or ""
                
        except Exception as e:
            logger.error(f"调用OpenAI视觉API失败: {str(e)}")
            raise 