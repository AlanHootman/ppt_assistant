#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
LLM服务模块

提供统一的大语言模型调用接口，支持OpenAI API和兼容的服务。
现在支持从数据库动态加载模型配置。
"""

import os
import time
import logging
from typing import Dict, List, Any, Optional, Union
from openai import OpenAI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

class LLMService:
    """大语言模型服务"""
    
    def __init__(self, model_type: str = "text"):
        """
        初始化LLM服务
        
        Args:
            model_type: 模型类型，支持 text、vision、deepthink
        """
        self.model_type = model_type
        self._client = None
        self._config = None
        self._last_request_time = 0
        
        # 初始化数据库连接
        self._init_database()
        
        # 加载配置
        self._load_config()
    
    def _init_database(self):
        """初始化数据库连接"""
        try:
            from config.settings import settings
            # 构建数据库URL
            db_path = settings.DB_DIR / "app.db"
            db_url = f"sqlite:///{db_path}"
            
            engine = create_engine(db_url)
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            self.db_session = SessionLocal()
        except Exception as e:
            logger.warning(f"无法连接数据库，将使用环境变量配置: {e}")
            self.db_session = None
    
    def _load_config(self):
        """从数据库加载配置"""
        if self.db_session:
            try:
                # 导入ModelConfig模型
                from apps.api.models.database import ModelConfig
                from sqlalchemy import and_
                
                # 查询激活的配置
                config = self.db_session.query(ModelConfig).filter(
                    and_(
                        ModelConfig.model_type == self.model_type,
                        ModelConfig.is_active == True
                    )
                ).first()
                
                if config:
                    self._config = {
                        'api_key': config.api_key,
                        'api_base': config.api_base,
                        'model_name': config.model_name,
                        'max_tokens': config.max_tokens,
                        'temperature': config.temperature
                    }
                    logger.info(f"从数据库加载{self.model_type}模型配置: {config.name}")
                    return
                else:
                    logger.warning(f"数据库中未找到激活的{self.model_type}模型配置")
            except Exception as e:
                logger.warning(f"从数据库加载配置失败: {e}")
        
        # 如果数据库配置不可用，回退到环境变量（兼容性）
        self._load_fallback_config()
    
    def _load_fallback_config(self):
        """从环境变量加载回退配置"""
        logger.info(f"使用环境变量配置{self.model_type}模型")
        
        if self.model_type == "text":
            api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
            api_base = os.environ.get("LLM_API_BASE") or os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")
            model_name = os.environ.get("LLM_MODEL", "gpt-4")
            max_tokens = int(os.environ.get("LLM_MAX_TOKENS", "128000"))
            temperature = float(os.environ.get("LLM_TEMPERATURE", "0.7"))
        elif self.model_type == "vision":
            api_key = os.environ.get("VISION_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
            api_base = os.environ.get("VISION_API_BASE") or os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")
            model_name = os.environ.get("VISION_MODEL", "gpt-4-vision")
            max_tokens = int(os.environ.get("VISION_MAX_TOKENS", "128000"))
            temperature = float(os.environ.get("VISION_TEMPERATURE", "0.7"))
        elif self.model_type == "deepthink":
            api_key = os.environ.get("DEEPTHINK_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
            api_base = os.environ.get("DEEPTHINK_API_BASE") or os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")
            model_name = os.environ.get("DEEPTHINK_MODEL", "o1-preview")
            max_tokens = int(os.environ.get("DEEPTHINK_MAX_TOKENS", "65536"))
            temperature = float(os.environ.get("DEEPTHINK_TEMPERATURE", "1.0"))
        else:
            raise ValueError(f"不支持的模型类型: {self.model_type}")
        
        self._config = {
            'api_key': api_key,
            'api_base': api_base,
            'model_name': model_name,
            'max_tokens': max_tokens,
            'temperature': temperature
        }
    
    def refresh_config(self):
        """刷新配置（当配置更新时调用）"""
        self._client = None  # 重置客户端
        self._load_config()
    
    @property
    def client(self) -> OpenAI:
        """获取OpenAI客户端"""
        if self._client is None:
            if not self._config:
                self._load_config()
            
            self._client = OpenAI(
                api_key=self._config['api_key'],
                base_url=self._config['api_base']
            )
        return self._client
    
    def _rate_limit(self):
        """请求速率限制"""
        from config.settings import settings
        intervals = getattr(settings, 'MODEL_REQUEST_INTERVALS', {})
        interval_ms = intervals.get(self.model_type, 0)
        
        if interval_ms > 0:
            current_time = time.time() * 1000
            time_since_last = current_time - self._last_request_time
            
            if time_since_last < interval_ms:
                sleep_time = (interval_ms - time_since_last) / 1000
                time.sleep(sleep_time)
            
            self._last_request_time = time.time() * 1000
    
    def generate_text(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        生成文本
        
        Args:
            messages: 消息列表
            temperature: 温度参数，不传则使用配置值
            max_tokens: 最大token数，不传则使用配置值
            **kwargs: 其他参数
            
        Returns:
            生成的文本内容
        """
        self._rate_limit()
        
        # 使用传入参数或配置值
        temperature = temperature if temperature is not None else self._config['temperature']
        max_tokens = max_tokens if max_tokens is not None else self._config['max_tokens']
        
        try:
            response = self.client.chat.completions.create(
                model=self._config['model_name'],
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"LLM请求失败: {e}")
            raise
    
    def generate_text_with_images(
        self,
        messages: List[Dict[str, Any]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        带图片的文本生成（视觉模型）
        
        Args:
            messages: 包含图片的消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            **kwargs: 其他参数
            
        Returns:
            生成的文本内容
        """
        if self.model_type != "vision":
            logger.warning(f"当前模型类型为{self.model_type}，建议使用vision类型处理图片")
        
        return self.generate_text(messages, temperature, max_tokens, **kwargs)
    
    def get_current_config(self) -> Dict[str, Any]:
        """获取当前配置信息"""
        if not self._config:
            self._load_config()
        
        # 返回配置信息，但隐藏API密钥
        config_copy = self._config.copy()
        if 'api_key' in config_copy:
            config_copy['api_key'] = f"{config_copy['api_key'][:8]}..."
        
        return config_copy
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, 'db_session') and self.db_session:
            self.db_session.close()


# 全局服务实例
_services = {}

def get_llm_service(model_type: str = "text") -> LLMService:
    """
    获取LLM服务实例（单例模式）
    
    Args:
        model_type: 模型类型
        
    Returns:
        LLMService实例
    """
    if model_type not in _services:
        _services[model_type] = LLMService(model_type)
    return _services[model_type]

def refresh_all_services():
    """刷新所有服务配置"""
    for service in _services.values():
        service.refresh_config() 