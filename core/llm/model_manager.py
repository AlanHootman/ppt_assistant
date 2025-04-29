#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
大模型管理器模块 - 简化版

提供对OpenAI API的简洁封装，支持文本生成、嵌入和多模态能力。
"""

import os
import logging
import json
import asyncio
import base64
from typing import Dict, Any, List, Optional, Union

# 引入OpenAI官方库
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
# 添加Jinja2模板支持
from jinja2 import Template

logger = logging.getLogger(__name__)

class ModelManager:
    """OpenAI API简化封装"""
    
    def __init__(self):
        """初始化模型管理器"""
        # 全局默认配置
        self.default_api_key = os.environ.get("OPENAI_API_KEY", "")
        self.default_api_base = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")
        self.organization = os.environ.get("OPENAI_ORGANIZATION", "")
        
        # 文本模型配置
        self.text_model = os.environ.get("LLM_MODEL", "gpt-4")
        self.text_api_key = os.environ.get("LLM_API_KEY", self.default_api_key)
        self.text_api_base = os.environ.get("LLM_API_BASE", self.default_api_base)
        
        # 视觉模型配置
        self.vision_model = os.environ.get("VISION_MODEL", "gpt-4-vision")
        self.vision_api_key = os.environ.get("VISION_API_KEY", self.default_api_key)
        self.vision_api_base = os.environ.get("VISION_API_BASE", self.default_api_base)
        
        # 嵌入模型配置
        self.embedding_model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-large")
        self.embedding_api_key = os.environ.get("EMBEDDING_API_KEY", self.default_api_key)
        self.embedding_api_base = os.environ.get("EMBEDDING_API_BASE", self.default_api_base)
        
        # 客户端缓存
        self._clients = {}
        
        logger.info("初始化大模型管理器")
    
    def _get_client(self, model_type: str) -> AsyncOpenAI:
        """
        获取指定类型的OpenAI客户端
        
        Args:
            model_type: 模型类型 (text, vision, embedding)
            
        Returns:
            OpenAI客户端实例
        """
        if model_type in self._clients:
            return self._clients[model_type]
            
        # 根据模型类型选择API配置
        if model_type == "text":
            api_key = self.text_api_key
            api_base = self.text_api_base
        elif model_type == "vision":
            api_key = self.vision_api_key
            api_base = self.vision_api_base
        elif model_type == "embedding":
            api_key = self.embedding_api_key
            api_base = self.embedding_api_base
        else:
            # 使用默认配置
            api_key = self.default_api_key
            api_base = self.default_api_base
            
        # 创建客户端
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=api_base,
            organization=self.organization
        )
        
        # 缓存客户端
        self._clients[model_type] = client
        
        return client
    
    def get_model_config(self, model_type):
        """获取指定类型的模型配置"""
        # 根据模型类型返回对应的模型名称和默认参数
        if model_type == "text":
            return {
                "model": self.text_model,
                "temperature": 0.7,
                "max_tokens": 4000
            }
        elif model_type == "vision":
            return {
                "model": self.vision_model,
                "temperature": 0.7,
                "max_tokens": 4000
            }
        elif model_type == "embedding":
            return {
                "model": self.embedding_model,
                "dimensions": 1536
            }
        else:
            logger.warning(f"未知模型类型: {model_type}，使用text类型")
            return {
                "model": self.text_model,
                "temperature": 0.7,
                "max_tokens": 4000
            }
    
    async def generate_text(self, 
                           model: str, 
                           prompt: str, 
                           temperature: float = 0.7, 
                           max_tokens: int = 4000,
                           top_p: float = 1.0,
                           stop: Optional[List[str]] = None) -> str:
        """
        调用OpenAI生成文本
        
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
        logger.info(f"调用OpenAI生成文本: {model}")
        

        try:
            # 获取文本模型客户端
            client = self._get_client("text")
            
            # 创建消息
            messages = [{"role": "user", "content": prompt}]
            
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
        

        try:
            # 获取嵌入模型客户端
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
        
        # 检查图像文件是否存在
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图像文件不存在: {image_path}")
        
        try:
            # 获取视觉模型客户端
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
                max_tokens=4000
            )
            
            # 提取结果
            result = response.choices[0].message.content
            return result or ""
                
        except Exception as e:
            logger.error(f"调用OpenAI视觉API失败: {str(e)}")
            raise
    
    async def generate_vision_response(self, 
                                     model: str, 
                                     prompt: str, 
                                     images: List[Dict[str, Any]], 
                                     temperature: float = 0.7, 
                                     max_tokens: int = 4000) -> str:
        """
        使用视觉模型分析多个图像并生成响应
        
        Args:
            model: 模型名称
            prompt: 提示词
            images: 图像列表，每个图像为包含url和detail键的字典
                   例如：[{"url": "file:///path/to/image.jpg", "detail": "high"}]
            temperature: 温度参数
            max_tokens: 最大生成token数
            
        Returns:
            分析结果文本
        """
        logger.info(f"使用视觉模型分析多图像: {model}, 图像数量: {len(images)}")
        
       
        try:
            # 获取视觉模型客户端
            client = self._get_client("vision")
            
            # 准备消息内容
            content: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
            
            # 添加所有图像到内容中
            for img in images:
                image_url = img.get("url", "")
                detail = img.get("detail", "auto")
                
                # 处理本地文件路径
                if image_url.startswith("file://"):
                    file_path = image_url.replace("file://", "")
                    
                    # 检查文件是否存在
                    if not os.path.exists(file_path):
                        logger.warning(f"图像文件不存在: {file_path}，跳过此图像")
                        continue
                    
                    # 读取图像文件并进行base64编码
                    with open(file_path, "rb") as image_file:
                        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                    
                    # 根据文件扩展名确定MIME类型
                    ext = os.path.splitext(file_path)[1].lower()
                    mime_type = "image/jpeg"  # 默认MIME类型
                    if ext == ".png":
                        mime_type = "image/png"
                    elif ext == ".gif":
                        mime_type = "image/gif"
                    elif ext == ".webp":
                        mime_type = "image/webp"
                    
                    image_content = {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}",
                            "detail": detail
                        }
                    }
                    content.append(image_content)
                else:
                    # 处理网络URL
                    image_content = {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url,
                            "detail": detail
                        }
                    }
                    content.append(image_content)
            
            # 调用OpenAI API
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # 提取结果
            result = response.choices[0].message.content
            return result or ""
                
        except Exception as e:
            logger.error(f"调用OpenAI视觉API失败: {str(e)}")
            raise 
            
    def render_template(self, template_str: str, context: Dict[str, Any]) -> str:
        """
        使用Jinja2渲染模板字符串
        
        Args:
            template_str: Jinja2模板字符串
            context: 模板上下文变量
            
        Returns:
            渲染后的字符串
        """
        try:
            template = Template(template_str)
            return template.render(**context)
        except Exception as e:
            logger.error(f"渲染Jinja2模板失败: {str(e)}")
            # 发生错误时返回原始模板
            return template_str 