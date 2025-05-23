#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PPT Agent 辅助工具模块

提供多个 PPT 相关 Agent 共享的功能，减少代码重复，提高可维护性。
"""

import logging
import os
import json
import re
import enum
import uuid
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Type, Tuple

from config.settings import settings

# 初始化日志
logger = logging.getLogger(__name__)

class EnumEncoder(json.JSONEncoder):
    """JSON编码器，支持枚举类型的序列化"""
    def default(self, obj):
        if isinstance(obj, enum.Enum):
            return obj.value if hasattr(obj, 'value') else str(obj)
        return super().default(obj)


class PPTAgentHelper:
    """
    PPT Agent 辅助工具类
    封装多个 PPT 相关 Agent 的共享功能
    """
    
    @staticmethod
    def init_ppt_manager():
        """
        初始化 PPT 管理器
        
        Returns:
            PPTManager 实例，如果导入失败则返回 None
        """
        try:
            from libs.ppt_manager.interfaces.ppt_api import PPTManager
            ppt_manager = PPTManager()
            logger.info("成功初始化PPT管理器")
            return ppt_manager
        except ImportError as e:
            logger.error(f"无法导入PPTManager: {str(e)}")
            return None

    @staticmethod
    def setup_temp_session_dir(session_id: str, subdir: str) -> Path:
        """
        创建临时会话目录
        
        Args:
            session_id: 会话ID
            subdir: 子目录名，如 slide_images, template_images 等
            
        Returns:
            临时目录路径
        """
        # 创建临时目录
        session_dir = Path(f"workspace/sessions/{session_id}/{subdir}")
        session_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"创建临时目录: {session_dir}")
        return session_dir
    
    @staticmethod
    def create_temp_filename(prefix: str = "temp") -> str:
        """
        创建唯一的临时文件名
        
        Args:
            prefix: 文件名前缀
            
        Returns:
            唯一的临时文件名，如 temp_abc123.pptx
        """
        # 生成唯一标识符
        unique_id = uuid.uuid4().hex[:8]
        filename = f"{prefix}_{unique_id}.pptx"
        return filename
    
    @staticmethod
    def extract_json_from_response(response: str) -> str:
        """
        从 LLM 响应中提取 JSON 文本
        
        Args:
            response: 响应文本
            
        Returns:
            提取出的 JSON 文本
        """
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
        解析 LLM 返回的 JSON 响应
        
        Args:
            response: LLM 响应文本
            default_value: 解析失败时返回的默认值
            
        Returns:
            解析后的 JSON 对象，失败则返回默认值
        """
        try:
            # 提取 JSON 文本
            json_text = PPTAgentHelper.extract_json_from_response(response)
            
            # 解析 JSON
            result = json.loads(json_text)
            return result
        except Exception as e:
            logger.error(f"解析 JSON 响应时出错: {str(e)}")
            return default_value
    
    @staticmethod
    def render_slide_to_image(ppt_manager, presentation: Any, slide_index: int, output_dir: Path) -> Optional[str]:
        """
        渲染幻灯片为图片
        
        Args:
            ppt_manager: PPT 管理器实例
            presentation: 演示文稿对象
            slide_index: 幻灯片索引
            output_dir: 输出目录
            
        Returns:
            图片路径，如果渲染失败则返回 None
        """
        try:
            # 创建唯一的临时文件名
            temp_pptx_filename = PPTAgentHelper.create_temp_filename()
            temp_pptx_path = output_dir / temp_pptx_filename
            
            # 临时保存修改后的 presentation 对象为 PPTX 文件
            logger.info(f"临时保存演示文稿到: {temp_pptx_path}")
            ppt_manager.save_presentation(presentation, str(temp_pptx_path))
            
            # 使用临时保存的 PPTX 文件进行渲染
            logger.info(f"渲染幻灯片，索引: {slide_index}")
            image_paths = ppt_manager.render_pptx_file(
                pptx_path=str(temp_pptx_path),
                output_dir=str(output_dir),
                slide_index=slide_index
            )
            
            if not image_paths or len(image_paths) == 0:
                logger.error("渲染幻灯片图像失败")
                return None
                
            logger.info(f"渲染成功: {image_paths[0]}")
            return image_paths[0]
            
        except Exception as e:
            logger.error(f"渲染幻灯片为图片时出错: {str(e)}")
            return None
        finally:
            # 删除临时 PPTX 文件
            if 'temp_pptx_path' in locals() and temp_pptx_path.exists():
                logger.info(f"删除临时 PPTX 文件: {temp_pptx_path}")
                temp_pptx_path.unlink()
    
    @staticmethod
    def get_config_value(config: Dict[str, Any], key: str, settings_key: str, default_value: Any) -> Any:
        """
        获取配置值，优先从配置字典获取，若不存在则从 settings 获取，最后使用默认值
        
        Args:
            config: 配置字典
            key: 配置键
            settings_key: settings 中的键
            default_value: 默认值
            
        Returns:
            配置值
        """
        if key in config:
            return config[key]
        
        if hasattr(settings, settings_key):
            return getattr(settings, settings_key)
            
        return default_value
    
    @staticmethod
    async def execute_with_retry(func, max_retries: int, *args, **kwargs) -> Tuple[Any, bool]:
        """
        使用重试机制执行函数
        
        Args:
            func: 要执行的异步函数
            max_retries: 最大重试次数
            *args, **kwargs: 传递给函数的参数
            
        Returns:
            (结果, 是否成功)
        """
        retry_count = 0
        last_error = None
        
        while retry_count <= max_retries:  # 允许初始尝试 + 重试次数
            try:
                logger.info(f"执行函数 {func.__name__}，尝试 {retry_count+1}/{max_retries+1}")
                result = await func(*args, **kwargs)
                return result, True
            except Exception as e:
                last_error = e
                logger.warning(f"执行 {func.__name__} 时出错 (尝试 {retry_count+1}/{max_retries+1}): {str(e)}")
                retry_count += 1
        
        logger.error(f"执行 {func.__name__} 失败，已达到最大重试次数 ({max_retries}): {str(last_error)}")
        return None, False 