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
        
        # 处理结果
        self.content_structure = content_structure  # 解析后的内容结构
        self.layout_features = None  # 模板布局特征
        self.decision_result = None  # 布局决策结果
        self.ppt_file_path = None  # 生成的PPT文件路径
        self.output_ppt_path = None  # 输出的PPT文件路径
        
        # 验证信息
        self.validation_attempts = 0  # 验证尝试次数
        self.validation_result = None  # 验证结果

        # 状态跟踪
        self.checkpoints = []  # 检查点列表
        self.failures = []  # 失败记录
        self.current_node = None  # 当前执行节点
        
        self.created_at = datetime.now().isoformat()
        
        logger.debug(f"创建状态: {self.session_id}")
    
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
            "content_structure": self.content_structure,
            "layout_features": self.layout_features,
            "decision_result": self.decision_result,
            "ppt_file_path": self.ppt_file_path,
            "validation_attempts": self.validation_attempts,
            "raw_md": self.raw_md,
            "ppt_template_path": self.ppt_template_path,
            "output_dir": self.output_dir,
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
        
        with open(state_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 创建状态实例
        state = cls(session_id=session_id)
        
        # 复制属性
        state.created_at = data.get("created_at", state.created_at)
        state.current_node = data.get("current_node")
        state.checkpoints = data.get("checkpoints", [])
        state.failures = data.get("failures", [])
        state.content_structure = data.get("content_structure")
        state.layout_features = data.get("layout_features")
        state.decision_result = data.get("decision_result")
        state.ppt_file_path = data.get("ppt_file_path")
        state.validation_attempts = data.get("validation_attempts", 0)
        state.raw_md = data.get("raw_md")
        state.ppt_template_path = data.get("ppt_template_path")
        state.output_dir = data.get("output_dir")
        state.output_ppt_path = data.get("output_ppt_path")
        
        logger.info(f"加载状态: {session_id}")
        return state 

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'AgentState':
        """
        从字典创建状态实例
        
        Args:
            data: 状态字典
            
        Returns:
            AgentState实例
        """
        if not data:
            logger.warning("传入的状态字典为空")
            return AgentState()
        
        # 提取基本信息
        session_id = data.get('session_id')
        raw_md = data.get('raw_md')
        ppt_template_path = data.get('ppt_template_path')
        output_dir = data.get('output_dir')
        
        # 创建新实例
        state = AgentState(
            session_id=session_id,
            raw_md=raw_md,
            ppt_template_path=ppt_template_path,
            output_dir=output_dir
        )
        
        # 复制其他属性
        for key, value in data.items():
            if key not in ['session_id', 'raw_md', 'ppt_template_path', 'output_dir']:
                if hasattr(state, key):
                    setattr(state, key, value)
        
        return state 