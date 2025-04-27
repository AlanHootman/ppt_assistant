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
from typing import Dict, Any, List, Optional, Union
import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

class ModelManager:
    """大模型统一管理器"""
    
    def __init__(self):
        """初始化模型管理器"""
        self.api_keys = {
            "openai": os.environ.get("OPENAI_API_KEY", settings.OPENAI_API_KEY),
        }
        self.base_urls = {
            "openai": "https://api.openai.com/v1",
        }
        logger.info("初始化大模型管理器")
    
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
        api_key = self.api_keys["openai"]
        if not api_key:
            raise ValueError("OpenAI API密钥未设置")
        
        base_url = self.base_urls["openai"]
        url = f"{base_url}/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # 构建请求参数
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p
        }
        
        if stop:
            payload["stop"] = stop
        
        # 模拟API调用（开发环境）
        if os.environ.get("DEV_ENV") == "true":
            logger.info(f"[DEV] 模拟OpenAI API请求: {model}")
            await asyncio.sleep(1)  # 模拟网络延迟
            return "这是一个模拟的OpenAI API响应"
        
        try:
            # 实际API调用
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                
                if response.status_code != 200:
                    logger.error(f"OpenAI API错误: {response.status_code}, {response.text}")
                    raise Exception(f"OpenAI API错误: {response.status_code}, {response.text}")
                
                response_data = response.json()
                result = response_data["choices"][0]["message"]["content"]
                return result
                
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
        api_key = self.api_keys["openai"]
        if not api_key:
            raise ValueError("OpenAI API密钥未设置")
        
        base_url = self.base_urls["openai"]
        url = f"{base_url}/embeddings"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        payload = {
            "model": model,
            "input": text
        }
        
        # 模拟API调用（开发环境）
        if os.environ.get("DEV_ENV") == "true":
            logger.info(f"[DEV] 模拟OpenAI嵌入API请求: {model}")
            await asyncio.sleep(0.5)  # 模拟网络延迟
            return [0.1] * 10  # 返回模拟的嵌入向量
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                
                if response.status_code != 200:
                    logger.error(f"OpenAI嵌入API错误: {response.status_code}, {response.text}")
                    raise Exception(f"OpenAI嵌入API错误: {response.status_code}, {response.text}")
                
                response_data = response.json()
                embedding = response_data["data"][0]["embedding"]
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
        api_key = self.api_keys["openai"]
        if not api_key:
            raise ValueError("OpenAI API密钥未设置")
        
        base_url = self.base_urls["openai"]
        url = f"{base_url}/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # 读取图片并转为base64
        import base64
        with open(image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
        
        # 构建多模态消息
        content = [
            {
                "type": "text",
                "text": prompt
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{encoded_image}"
                }
            }
        ]
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": content
                }
            ],
            "max_tokens": 1000
        }
        
        # 模拟API调用（开发环境）
        if os.environ.get("DEV_ENV") == "true":
            logger.info(f"[DEV] 模拟OpenAI视觉API请求: {model}")
            await asyncio.sleep(1.5)  # 模拟网络延迟
            return "这是一个模拟的OpenAI视觉API响应，图像分析结果"
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                
                if response.status_code != 200:
                    logger.error(f"OpenAI视觉API错误: {response.status_code}, {response.text}")
                    raise Exception(f"OpenAI视觉API错误: {response.status_code}, {response.text}")
                
                response_data = response.json()
                result = response_data["choices"][0]["message"]["content"]
                return result
                
        except Exception as e:
            logger.error(f"调用OpenAI视觉API失败: {str(e)}")
            raise 