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
    
    def __init__(self, session_id: Optional[str] = None):
        """
        初始化状态
        
        Args:
            session_id: 会话ID，如果不提供则自动生成
        """
        self.session_id = session_id or str(uuid.uuid4())
        self.created_at = datetime.now().isoformat()
        self.current_node = None
        self.checkpoints = []
        self.failures = []
        
        # Markdown解析结果
        self.raw_md = None
        self.content_structure = None
        
        # PPT模板分析结果
        self.ppt_template_path = None
        self.layout_features = None
        
        # 布局决策结果
        self.decision_result = None
        
        # PPT生成结果
        self.ppt_file_path = None
        self.validation_attempts = 0
        
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
            "timestamp": datetime.now().isoformat(),
            "error": error
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
            "validation_attempts": self.validation_attempts
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
        
        logger.info(f"加载状态: {session_id}")
        return state 