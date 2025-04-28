#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
工作流状态管理模块

提供工作流状态的定义和持久化功能。
"""

import os
import uuid
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class AgentState:
    """工作流状态类"""
    
    def __init__(self, session_id=None, raw_md=None, ppt_template_path=None, output_dir=None, content_structure=None):
        """
        初始化代理状态
        
        Args:
            session_id (str, optional): 会话ID，默认自动生成
            raw_md (str, optional): 原始Markdown内容
            ppt_template_path (str, optional): PPT模板路径
            output_dir (str, optional): 输出目录路径
            content_structure (dict, optional): 内容结构
        """
        # 如果没有提供会话ID，自动生成一个
        if not session_id:
            self.session_id = str(uuid.uuid4())
        else:
            self.session_id = session_id
        
        # 基本属性
        self.raw_md = raw_md  # 原始Markdown内容
        self.ppt_template_path = ppt_template_path  # PPT模板路径
        self.output_dir = output_dir  # 输出目录
        
        # Markdown解析结果
        self.content_structure = content_structure  # 解析后的内容结构
        
        # PPT分析结果
        self.layout_features = None  # 模板布局特征
        
        # 内容规划结果
        self.content_plan = None  # 完整的内容规划（包括开篇页、内容页和结束页）
        self.decision_result = None  # 内容-布局匹配结果（向后兼容）
        
        # 幻灯片生成状态
        self.current_section_index = None  # 当前处理的章节索引
        self.has_more_content = False  # 是否还有更多内容需要处理
        self.current_slide = None  # 当前生成的幻灯片
        self.generated_slides = []  # 已生成的幻灯片列表
        self.presentation = None  # PPTX对象
        
        # 验证信息
        self.validation_result = None  # 验证结果
        self.validation_attempts = 0  # 验证尝试次数
        self.validation_issues = []  # 验证发现的问题
        self.validation_suggestions = []  # 改进建议
        
        # 最终输出
        self.output_ppt_path = None  # 最终PPT文件路径
        
        # 状态跟踪
        self.checkpoints = []  # 检查点列表
        self.failures = []  # 失败记录
        self.current_node = None  # 当前执行节点
        
        self.created_at = datetime.now().isoformat()
        
        logger.debug(f"创建状态: {self.session_id}")
    
    # 添加ppt_file_path属性，兼容旧代码
    @property
    def ppt_file_path(self):
        """兼容性属性，返回output_ppt_path的值"""
        return self.output_ppt_path
    
    @ppt_file_path.setter
    def ppt_file_path(self, value):
        """设置ppt_file_path时同时设置output_ppt_path"""
        self.output_ppt_path = value
    
    def add_checkpoint(self, checkpoint: str) -> None:
        """
        添加检查点
        
        Args:
            checkpoint: 检查点名称
        """
        if checkpoint not in self.checkpoints:
            self.checkpoints.append(checkpoint)
            logger.debug(f"添加检查点: {checkpoint}")
    
    def has_checkpoint(self, checkpoint: str) -> bool:
        """
        检查是否有特定检查点
        
        Args:
            checkpoint: 检查点名称
            
        Returns:
            是否存在该检查点
        """
        return checkpoint in self.checkpoints
    
    def record_failure(self, error: str) -> None:
        """
        记录错误
        
        Args:
            error: 错误信息
        """
        self.failures.append({
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
        logger.error(f"记录错误: {error}")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将状态转换为字典
        
        Returns:
            状态字典
        """
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "current_node": self.current_node,
            "checkpoints": self.checkpoints,
            "failures": self.failures,
            
            # 基本属性
            "raw_md": self.raw_md,
            "ppt_template_path": self.ppt_template_path,
            "output_dir": self.output_dir,
            
            # Markdown解析结果
            "content_structure": self.content_structure,
            
            # PPT分析结果
            "layout_features": self.layout_features,
            
            # 内容规划结果
            "content_plan": self.content_plan,
            "decision_result": self.decision_result,
            
            # 幻灯片生成状态
            "current_section_index": self.current_section_index,
            "has_more_content": self.has_more_content,
            "current_slide": self.current_slide,
            "generated_slides": self.generated_slides,
            
            # 验证信息
            "validation_result": self.validation_result,
            "validation_attempts": self.validation_attempts,
            "validation_issues": self.validation_issues,
            "validation_suggestions": self.validation_suggestions,
            
            # 最终输出
            "output_ppt_path": self.output_ppt_path
        }
    
    def save(self) -> None:
        """保存状态到文件"""
        from config.settings import settings
        
        # 确保目录存在
        session_dir = settings.WORKSPACE_DIR / "sessions" / self.session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存状态文件
        state_file = session_dir / "state.json"
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        
        logger.info(f"保存状态: {state_file}")
    
    @classmethod
    def load(cls, session_id: str) -> 'AgentState':
        """
        从文件加载状态
        
        Args:
            session_id: 会话ID
            
        Returns:
            加载的状态
        """
        from config.settings import settings
        
        state_file = settings.WORKSPACE_DIR / "sessions" / session_id / "state.json"
        
        if not state_file.exists():
            raise FileNotFoundError(f"状态文件不存在: {state_file}")
        
        # 读取状态文件
        with open(state_file, 'r', encoding='utf-8') as f:
            state_dict = json.load(f)
        
        # 恢复状态
        return cls.from_dict(state_dict)
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'AgentState':
        """
        从字典恢复状态
        
        Args:
            data: 状态字典
            
        Returns:
            恢复的状态对象
        """
        # 创建基本状态对象
        state = AgentState(
            session_id=data.get("session_id"),
            raw_md=data.get("raw_md"),
            ppt_template_path=data.get("ppt_template_path"),
            output_dir=data.get("output_dir"),
            content_structure=data.get("content_structure")
        )
        
        # 恢复其他属性
        state.created_at = data.get("created_at", datetime.now().isoformat())
        state.current_node = data.get("current_node")
        state.checkpoints = data.get("checkpoints", [])
        state.failures = data.get("failures", [])
        
        # 内容规划结果
        state.content_plan = data.get("content_plan")
        state.decision_result = data.get("decision_result")
        
        # 分析结果
        state.layout_features = data.get("layout_features")
        
        # 幻灯片生成状态
        state.current_section_index = data.get("current_section_index")
        state.has_more_content = data.get("has_more_content", False)
        state.current_slide = data.get("current_slide")
        state.generated_slides = data.get("generated_slides", [])
        
        # 验证信息
        state.validation_result = data.get("validation_result")
        state.validation_attempts = data.get("validation_attempts", 0)
        state.validation_issues = data.get("validation_issues", [])
        state.validation_suggestions = data.get("validation_suggestions", [])
        
        # 最终输出
        state.output_ppt_path = data.get("output_ppt_path")
        
        return state 