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
import atexit
import weakref
import time
from typing import Dict, Any, List, Optional, Union

# 引入OpenAI官方库
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
# 添加Jinja2模板支持
from jinja2 import Template
# 导入全局设置
from config.settings import settings

logger = logging.getLogger(__name__)

# 全局实例注册表，用于跟踪所有ModelManager实例
_model_manager_instances = weakref.WeakSet()

class ModelManager:
    """OpenAI API简化封装"""
    
    def __init__(self):
        """初始化模型管理器"""
        # 全局默认配置 - 仅作为最后的回退
        self.organization = os.environ.get("OPENAI_ORGANIZATION", "")
        
        # 从数据库加载模型配置
        self._load_model_configs_from_db()
        
        # 嵌入模型配置 - 暂时保留环境变量方式，因为数据库中没有配置
        self.embedding_model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-large")
        self.embedding_api_key = os.environ.get("EMBEDDING_API_KEY", "")
        self.embedding_api_base = os.environ.get("EMBEDDING_API_BASE", "https://api.openai.com/v1")
        
        # 客户端缓存
        self._clients = {}
        self._is_closed = False
        
        # 请求间隔控制
        self._last_request_times = {}  # 记录每种模型类型的上次请求时间
        self._request_intervals = settings.MODEL_REQUEST_INTERVALS  # 获取配置的请求间隔
        
        # 注册清理函数
        atexit.register(self._cleanup_clients_sync)
        
        # 注册到全局实例集合
        _model_manager_instances.add(self)
        
        logger.info("初始化大模型管理器")
        logger.info(f"请求间隔配置: {self._request_intervals}")
    
    def _load_model_configs_from_db(self):
        """从数据库加载激活的模型配置"""
        try:
            # 动态导入以避免循环依赖
            from apps.api.dependencies.database import get_db
            from apps.api.services.model_config_service import ModelConfigService
            
            # 获取数据库会话
            db_generator = get_db()
            db = next(db_generator)
            
            try:
                service = ModelConfigService(db)
                active_configs = service.get_active_configs()
                
                # 加载LLM配置
                llm_config = active_configs.get("llm")
                if llm_config:
                    self.text_model = llm_config.model_name
                    self.text_api_key = llm_config.api_key
                    self.text_api_base = llm_config.api_base
                    self.text_max_tokens = llm_config.max_tokens
                    self.text_temperature = llm_config.temperature
                    logger.info(f"加载LLM配置: {llm_config.name} ({llm_config.model_name})")
                else:
                    logger.warning("数据库中未找到激活的LLM配置，使用默认值")
                    self._set_default_text_config()
                
                # 加载Vision配置
                vision_config = active_configs.get("vision")
                if vision_config:
                    self.vision_model = vision_config.model_name
                    self.vision_api_key = vision_config.api_key
                    self.vision_api_base = vision_config.api_base
                    self.vision_max_tokens = vision_config.max_tokens
                    self.vision_temperature = vision_config.temperature
                    logger.info(f"加载Vision配置: {vision_config.name} ({vision_config.model_name})")
                else:
                    logger.warning("数据库中未找到激活的Vision配置，使用默认值")
                    self._set_default_vision_config()
                
                # 加载DeepThink配置
                deepthink_config = active_configs.get("deepthink")
                if deepthink_config:
                    self.deep_thinking_model = deepthink_config.model_name
                    self.deep_thinking_api_key = deepthink_config.api_key
                    self.deep_thinking_api_base = deepthink_config.api_base
                    self.deep_thinking_max_tokens = deepthink_config.max_tokens
                    self.deep_thinking_temperature = deepthink_config.temperature
                    logger.info(f"加载DeepThink配置: {deepthink_config.name} ({deepthink_config.model_name})")
                else:
                    logger.warning("数据库中未找到激活的DeepThink配置，使用默认值")
                    self._set_default_deepthink_config()
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"从数据库加载模型配置失败: {e}")
            logger.info("使用默认配置")
            self._set_default_text_config()
            self._set_default_vision_config()
            self._set_default_deepthink_config()
    
    def _set_default_text_config(self):
        """设置默认的文本模型配置"""
        self.text_model = "gpt-4"
        self.text_api_key = ""
        self.text_api_base = "https://api.openai.com/v1"
        self.text_max_tokens = 4000
        self.text_temperature = 0.7
    
    def _set_default_vision_config(self):
        """设置默认的视觉模型配置"""
        self.vision_model = "gpt-4-vision-preview"
        self.vision_api_key = ""
        self.vision_api_base = "https://api.openai.com/v1"
        self.vision_max_tokens = 4000
        self.vision_temperature = 0.7
    
    def _set_default_deepthink_config(self):
        """设置默认的深度思考模型配置"""
        self.deep_thinking_model = "o1-preview"
        self.deep_thinking_api_key = ""
        self.deep_thinking_api_base = "https://api.openai.com/v1"
        self.deep_thinking_max_tokens = 32768
        self.deep_thinking_temperature = 1.0
    
    def __enter__(self):
        """进入上下文管理器"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文管理器时清理资源"""
        try:
            # 如果有运行中的事件循环，创建清理任务
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.close_clients())
            else:
                # 如果没有运行中的事件循环，尝试运行清理
                loop.run_until_complete(self.close_clients())
        except RuntimeError:
            # 事件循环不可用，只能标记为已关闭
            self._is_closed = True
            self._clients.clear()
    
    async def __aenter__(self):
        """异步上下文管理器进入"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出时清理资源"""
        await self.close_clients()
    
    async def _wait_for_request_interval(self, model_type: str):
        """
        根据配置的间隔等待请求
        
        Args:
            model_type: 模型类型 (text, deep_thinking, vision, embedding)
        """
        interval_ms = self._request_intervals.get(model_type, 0)
        if interval_ms <= 0:
            return  # 没有配置间隔或间隔为0，不需要等待
        
        current_time = time.time() * 1000  # 转换为毫秒
        last_request_time = self._last_request_times.get(model_type, 0)
        
        # 计算需要等待的时间
        elapsed_time = current_time - last_request_time
        wait_time = interval_ms - elapsed_time
        
        if wait_time > 0:
            wait_seconds = wait_time / 1000.0  # 转换为秒
            logger.debug(f"模型类型 {model_type} 需要等待 {wait_time:.1f} 毫秒")
            await asyncio.sleep(wait_seconds)
        
        # 更新上次请求时间
        self._last_request_times[model_type] = time.time() * 1000
    
    def _get_client(self, model_type: str) -> AsyncOpenAI:
        """
        获取指定类型的OpenAI客户端
        
        Args:
            model_type: 模型类型 (text, vision, embedding)
            
        Returns:
            OpenAI客户端实例
        """
        if self._is_closed:
            raise RuntimeError("ModelManager已关闭，无法创建新的客户端")
            
        if model_type in self._clients:
            return self._clients[model_type]
            
        # 根据模型类型选择API配置
        if model_type == "text":
            api_key = self.text_api_key
            api_base = self.text_api_base
        elif model_type == "vision":
            api_key = self.vision_api_key
            api_base = self.vision_api_base
        elif model_type == "deep_thinking":
            api_key = self.deep_thinking_api_key
            api_base = self.deep_thinking_api_base
        elif model_type == "embedding":
            api_key = self.embedding_api_key
            api_base = self.embedding_api_base
        else:
            # 使用文本模型配置作为默认
            api_key = self.text_api_key
            api_base = self.text_api_base
            
        # 验证API密钥
        if not api_key or api_key.strip() == "":
            raise ValueError(f"模型类型 {model_type} 的API密钥未配置或为空")
        
        # 创建客户端
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=api_base,
            organization=self.organization
        )
        
        # 缓存客户端
        self._clients[model_type] = client
        
        return client
    
    async def close_clients(self):
        """
        异步关闭所有客户端连接
        """
        if self._is_closed:
            return
            
        logger.debug("开始关闭异步客户端连接")
        for model_type, client in list(self._clients.items()):
            try:
                await client.close()
                logger.debug(f"已关闭 {model_type} 客户端")
            except Exception as e:
                logger.warning(f"关闭 {model_type} 客户端时出错: {e}")
        
        # 清空客户端缓存
        self._clients.clear()
        self._is_closed = True
        logger.debug("所有异步客户端已关闭")
    
    def _cleanup_clients_sync(self):
        """
        同步清理方法，用于atexit注册
        """
        if self._is_closed or not self._clients:
            return
            
        logger.debug("程序退出时清理异步客户端")
        
        # 检查是否有运行中的事件循环
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果事件循环正在运行，创建任务来清理
                loop.create_task(self.close_clients())
            else:
                # 如果事件循环未运行，运行清理任务
                loop.run_until_complete(self.close_clients())
        except RuntimeError:
            # 如果没有事件循环或事件循环已关闭，直接清理缓存
            logger.warning("事件循环不可用，跳过异步清理")
            self._clients.clear()
            self._is_closed = True
    
    def get_model_config(self, model_type):
        """
        获取指定类型的模型配置
        
        Args:
            model_type: 模型类型 (text, vision, embedding)
            
        Returns:
            模型配置字典
        """
        # 从全局设置中获取模型默认参数
        model_defaults = settings.get_model_defaults(model_type)
        
        # 根据模型类型返回对应的模型名称和配置参数
        if model_type == "text":
            return {
                "model": self.text_model,
                "temperature": getattr(self, 'text_temperature', model_defaults.get("temperature")),
                "max_tokens": getattr(self, 'text_max_tokens', model_defaults.get("max_tokens"))
            }
        elif model_type == "vision":
            return {
                "model": self.vision_model,
                "temperature": getattr(self, 'vision_temperature', model_defaults.get("temperature")),
                "max_tokens": getattr(self, 'vision_max_tokens', model_defaults.get("max_tokens"))
            }
        elif model_type == "deep_thinking":
            return {
                "model": self.deep_thinking_model,
                "temperature": getattr(self, 'deep_thinking_temperature', model_defaults.get("temperature")),
                "max_tokens": getattr(self, 'deep_thinking_max_tokens', model_defaults.get("max_tokens"))
            }
        elif model_type == "embedding":
            return {
                "model": self.embedding_model,
                "dimensions": model_defaults.get("dimensions", 1536)
            }
        else:
            logger.warning(f"未知模型类型: {model_type}，使用text类型")
            return {
                "model": self.text_model,
                "temperature": getattr(self, 'text_temperature', model_defaults.get("temperature")),
                "max_tokens": getattr(self, 'text_max_tokens', model_defaults.get("max_tokens"))
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
        
        client = None
        try:
            # 等待请求间隔
            await self._wait_for_request_interval("text")
            
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
            # 等待请求间隔
            await self._wait_for_request_interval("embedding")
            
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
            # 等待请求间隔
            await self._wait_for_request_interval("vision")
            
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
            # 等待请求间隔
            await self._wait_for_request_interval("vision")
            
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