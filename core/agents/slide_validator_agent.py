#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
幻灯片验证Agent模块

负责验证生成的幻灯片是否符合质量要求，检测布局问题、内容溢出等。
"""

import logging
import os
import json
from typing import Dict, Any, List, Optional, Tuple

from core.agents.base_agent import BaseAgent
from core.engine.state import AgentState
from core.llm.model_manager import ModelManager

logger = logging.getLogger(__name__)

class SlideValidatorAgent(BaseAgent):
    """幻灯片验证Agent，负责验证生成的幻灯片质量"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化幻灯片验证Agent
        
        Args:
            config: Agent配置
        """
        super().__init__(config)
        # 初始化模型管理器
        self.model_manager = ModelManager()
        
        # 从配置获取模型类型和名称
        self.model_type = config.get("model_type", "vision")
        
        # 初始化模型属性
        model_config = self.model_manager.get_model_config(self.model_type)
        self.vision_model = model_config.get("model")
        self.temperature = model_config.get("temperature", 0.7)
        self.max_tokens = model_config.get("max_tokens", 4000)
        
        logger.info(f"初始化SlideValidatorAgent，使用模型: {self.vision_model}")
    
    async def run(self, state: AgentState) -> AgentState:
        """
        执行幻灯片验证
        
        Args:
            state: 当前工作流状态
            
        Returns:
            更新后的状态
        """
        logger.info("开始验证幻灯片")
        
        # 检查是否有当前幻灯片
        if not hasattr(state, "current_slide") or not state.current_slide:
            error_msg = "没有当前幻灯片可供验证"
            self.record_failure(state, error_msg)
            state.validation_result = False
            return state
        
        try:
            # 获取当前幻灯片信息
            slide_id = state.current_slide.get("slide_id")
            slide_content = state.current_slide.get("content", {})
            
            # 在实际项目中，这里应该使用视觉模型分析幻灯片图像
            # 现在使用基于内容的验证规则进行模拟
            validation_result, issues, suggestions = self._validate_slide_content(slide_content)
            
            # 增加验证次数计数
            if not hasattr(state, "validation_attempts"):
                state.validation_attempts = 0
            state.validation_attempts += 1
            
            # 更新状态
            state.validation_result = validation_result
            state.validation_issues = issues
            state.validation_suggestions = suggestions
            
            # 记录验证信息
            logger.info(f"幻灯片验证结果: {'通过' if validation_result else '不通过'}")
            if issues:
                logger.info(f"验证问题: {issues}")
            
            # 记录检查点
            self.add_checkpoint(state)
            
        except Exception as e:
            error_msg = f"幻灯片验证失败: {str(e)}"
            self.record_failure(state, error_msg)
            state.validation_result = False
        
        return state
    
    def _validate_slide_content(self, slide_content: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """
        验证幻灯片内容
        
        Args:
            slide_content: 幻灯片内容
            
        Returns:
            验证结果、问题列表、改进建议列表
        """
        # 初始化结果
        is_valid = True
        issues = []
        suggestions = []
        
        # 检查标题
        title = slide_content.get("title", "")
        if not title:
            is_valid = False
            issues.append("幻灯片缺少标题")
            suggestions.append("添加明确的幻灯片标题")
        elif len(title) > 100:
            is_valid = False
            issues.append("标题过长")
            suggestions.append("将标题缩短至100字符以内")
        
        # 检查内容量
        bullets = slide_content.get("bullets", [])
        if len(bullets) > 6:
            is_valid = False
            issues.append("列表项过多")
            suggestions.append("减少列表项数量或分割为多张幻灯片")
        
        # 检查段落长度
        paragraphs = slide_content.get("paragraphs", [])
        for i, paragraph in enumerate(paragraphs):
            if len(paragraph) > 300:
                is_valid = False
                issues.append(f"第{i+1}段落过长")
                suggestions.append(f"缩短第{i+1}段落或分割为多张幻灯片")
        
        # 检查双栏布局是否平衡
        left_content = slide_content.get("leftContent", [])
        right_content = slide_content.get("rightContent", [])
        if left_content and right_content:
            if len(left_content) > 2 * len(right_content) or len(right_content) > 2 * len(left_content):
                is_valid = False
                issues.append("双栏内容不平衡")
                suggestions.append("调整左右栏内容使其更加平衡")
        
        # 添加随机因素，使验证结果偶尔失败，以测试重新生成流程
        # 只有在没有其他问题且通过率高时才随机失败
        import random
        if is_valid and random.random() < 0.05:  # 5%的随机失败率
            is_valid = False
            issues.append("布局不够美观")
            suggestions.append("调整内容排版和视觉平衡")
        
        return is_valid, issues, suggestions
    
    async def _analyze_with_vision_model(self, image_path: str) -> Dict[str, Any]:
        """
        使用视觉模型分析幻灯片图像
        
        Args:
            image_path: 幻灯片图像路径
            
        Returns:
            分析结果
        """
        # 检查图像是否存在
        if not os.path.exists(image_path):
            logger.warning(f"图像文件不存在: {image_path}")
            return {"error": "图像文件不存在"}
        
        # 在实际实现中，这里应该调用视觉模型API
        # 当前使用模拟结果
        return {
            "has_issues": False,
            "issues": [],
            "suggestions": []
        } 