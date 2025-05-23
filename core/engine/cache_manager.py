"""
缓存管理器模块
负责处理各类缓存数据的加载和保存
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
import hashlib

from core.engine.state import AgentState
from config.settings import settings

logger = logging.getLogger(__name__)

class CacheManager:
    """缓存管理器，负责处理各种缓存数据"""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        初始化缓存管理器
        
        Args:
            cache_dir: 缓存目录，如果为None则使用默认设置
        """
        # 使用 WORKSPACE_DIR/cache 作为默认缓存目录
        self.cache_dir = cache_dir or settings.WORKSPACE_DIR / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"初始化缓存管理器，缓存目录: {self.cache_dir}")
    
    def get_cache_path(self, cache_type: str, key: str) -> Path:
        """
        获取缓存文件路径
        
        Args:
            cache_type: 缓存类型 (markdown, ppt_analysis, content_plan)
            key: 缓存键名，通常是经过哈希处理的内容标识
            
        Returns:
            缓存文件路径
        """
        # 确保类型目录存在
        type_dir = self.cache_dir / cache_type
        type_dir.mkdir(parents=True, exist_ok=True)
        
        # 返回完整路径
        return type_dir / f"{key}.json"
    
    def generate_cache_key(self, content: str) -> str:
        """
        为内容生成缓存键
        
        Args:
            content: 需要缓存的内容
            
        Returns:
            缓存键 (MD5哈希值)
        """
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def save_to_cache(self, cache_type: str, key: str, data: Dict[str, Any]) -> Path:
        """
        保存数据到缓存
        
        Args:
            cache_type: 缓存类型
            key: 缓存键
            data: 要缓存的数据
            
        Returns:
            缓存文件路径
        """
        cache_path = self.get_cache_path(cache_type, key)
        
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"已保存缓存: {cache_type}/{key}")
            return cache_path
        except Exception as e:
            logger.error(f"保存缓存失败: {cache_type}/{key} - {str(e)}")
            raise
    
    def load_from_cache(self, cache_type: str, key: str) -> Optional[Dict[str, Any]]:
        """
        从缓存加载数据
        
        Args:
            cache_type: 缓存类型
            key: 缓存键
            
        Returns:
            缓存的数据，如果不存在则返回None
        """
        cache_path = self.get_cache_path(cache_type, key)
        
        if not cache_path.exists():
            logger.debug(f"缓存不存在: {cache_type}/{key}")
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"已加载缓存: {cache_type}/{key}")
            return data
        except Exception as e:
            logger.error(f"加载缓存失败: {cache_type}/{key} - {str(e)}")
            return None
    
    def has_cache(self, cache_type: str, key: str) -> bool:
        """
        检查缓存是否存在
        
        Args:
            cache_type: 缓存类型
            key: 缓存键
            
        Returns:
            是否存在缓存
        """
        cache_path = self.get_cache_path(cache_type, key)
        return cache_path.exists()
    
    def get_markdown_cache(self, raw_md: str) -> Optional[Dict[str, Any]]:
        """
        获取Markdown解析缓存
        
        Args:
            raw_md: 原始Markdown内容
            
        Returns:
            缓存的解析结果，如果不存在则返回None
        """
        # 生成缓存键
        cache_key = self.generate_cache_key(raw_md)
        
        # 从缓存加载
        return self.load_from_cache("markdown", cache_key)
    
    def save_markdown_cache(self, raw_md: str, content_structure: Dict[str, Any]) -> Path:
        """
        保存Markdown解析缓存
        
        Args:
            raw_md: 原始Markdown内容
            content_structure: 解析后的内容结构
            
        Returns:
            缓存文件路径
        """
        # 生成缓存键
        cache_key = self.generate_cache_key(raw_md)
        
        # 保存到缓存
        return self.save_to_cache("markdown", cache_key, content_structure)
    
    def get_ppt_analysis_cache(self, ppt_path: str) -> Optional[Dict[str, Any]]:
        """
        获取PPT分析缓存
        
        Args:
            ppt_path: PPT文件路径
            
        Returns:
            缓存的分析结果，如果不存在则返回None
        """
        # 对文件路径和最后修改时间生成缓存键
        file_path = Path(ppt_path)
        if not file_path.exists():
            return None
            
        file_stats = os.stat(file_path)
        cache_key = self.generate_cache_key(f"{ppt_path}_{file_stats.st_mtime}")
        
        # 从缓存加载
        return self.load_from_cache("ppt_analysis", cache_key)
    
    def save_ppt_analysis_cache(self, ppt_path: str, layout_features: Dict[str, Any]) -> Path:
        """
        保存PPT分析缓存
        
        Args:
            ppt_path: PPT文件路径
            layout_features: 分析出的布局特征
            
        Returns:
            缓存文件路径
        """
        # 对文件路径和最后修改时间生成缓存键
        file_path = Path(ppt_path)
        file_stats = os.stat(file_path)
        cache_key = self.generate_cache_key(f"{ppt_path}_{file_stats.st_mtime}")
        
        # 保存到缓存
        return self.save_to_cache("ppt_analysis", cache_key, layout_features)
    
    def get_content_plan_cache(self, content_structure: Dict[str, Any], layout_features: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        获取内容规划缓存
        
        Args:
            content_structure: 内容结构
            layout_features: 布局特征
            
        Returns:
            缓存的内容规划，如果不存在则返回None
        """
        # 对内容结构和布局特征的组合生成缓存键
        combined = json.dumps({
            "content": content_structure,
            "layout": layout_features
        }, sort_keys=True)
        
        cache_key = self.generate_cache_key(combined)
        
        # 从缓存加载
        return self.load_from_cache("content_plan", cache_key)
    
    def save_content_plan_cache(self, content_structure: Dict[str, Any], layout_features: Dict[str, Any], content_plan: Dict[str, Any]) -> Path:
        """
        保存内容规划缓存
        
        Args:
            content_structure: 内容结构
            layout_features: 布局特征
            content_plan: 内容规划
            
        Returns:
            缓存文件路径
        """
        # 对内容结构和布局特征的组合生成缓存键
        combined = json.dumps({
            "content": content_structure,
            "layout": layout_features
        }, sort_keys=True)
        
        cache_key = self.generate_cache_key(combined)
        
        # 保存到缓存
        return self.save_to_cache("content_plan", cache_key, content_plan) 