#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
工作流模拟功能模块

提供工作流引擎的模拟节点和方法，用于开发和测试阶段
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from core.engine.state import AgentState
from config.settings import settings

logger = logging.getLogger(__name__)

class WorkflowMocks:
    """工作流模拟器"""
    
    @staticmethod
    def mock_ppt_analyzer(state: AgentState) -> None:
        """模拟PPT模板分析实现"""
        logger.info(f"[模拟] 分析PPT模板: {state.ppt_template_path}")
        state.layout_features = {
            "templateName": Path(state.ppt_template_path).stem,
            "slideCount": 10,  # 假设值
            "layouts": ["title", "content", "twoColumns", "image"]
        }
    
    @staticmethod
    def mock_layout_decider(state: AgentState) -> None:
        """模拟布局决策实现"""
        logger.info(f"[模拟] 执行布局决策: 内容结构存在={state.content_structure is not None}, 布局特征存在={state.layout_features is not None}")
        
        # 模拟决策结果
        state.decision_result = {
            "slides": [
                {
                    "type": "title_slide",
                    "content": {
                        "title": state.content_structure.get("title", "演示文稿"),
                        "subtitle": "自动生成的PPT"
                    }
                }
            ]
        }
        
        # 添加内容幻灯片
        sections = state.content_structure.get("sections", [])
        for section in sections:
            section_title = section.get("title", "")
            section_content = section.get("content", [])
            
            slide = {
                "type": "content_slide",
                "content": {
                    "title": section_title,
                    "bullets": section_content
                }
            }
            
            state.decision_result["slides"].append(slide)
        
        logger.info(f"[模拟] 布局决策完成: 生成了{len(state.decision_result.get('slides', []))}张幻灯片")
    
    @staticmethod
    def mock_ppt_generator(state: AgentState) -> None:
        """模拟PPT生成实现"""
        slides = state.decision_result.get("slides", [])
        
        # 检查输出目录设置
        output_dir = getattr(state, 'output_dir', None)
        if output_dir:
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            output_path = Path(output_dir) / f"{state.session_id}.pptx"
        else:
            # 使用默认路径
            output_path = settings.WORKSPACE_DIR / "temp" / f"{state.session_id}.pptx"
            output_path.parent.mkdir(exist_ok=True)
        
        # 生成空文件作为测试
        output_path.parent.mkdir(exist_ok=True)
        
        # 仅做测试记录
        with open(output_path.with_suffix(".json"), "w", encoding="utf-8") as f:
            json.dump(state.decision_result, f, ensure_ascii=False, indent=2)
        
        state.ppt_file_path = str(output_path)
        state.output_ppt_path = str(output_path)  # 添加这个属性以保持一致性
        logger.info(f"[模拟] PPT文件将保存至: {output_path}")
    
    @staticmethod
    def mock_validator(state: AgentState) -> None:
        """模拟验证节点实现"""
        # 直接设置验证尝试次数为1，确保通过验证
        state.validation_attempts = 1
        logger.info(f"[模拟] 验证节点: 设置验证尝试次数为 {state.validation_attempts}")
    
    @staticmethod
    def validate_condition(state: Dict[str, Any]) -> str:
        """
        验证条件函数
        
        Args:
            state: 当前状态字典
            
        Returns:
            下一步分支名称
        """
        # 从字典获取验证尝试次数
        validation_attempts = state.get("validation_attempts", 0)
        session_id = state.get("session_id", "unknown")
        
        # 简化验证逻辑，确保工作流能够终止
        logger.info(f"验证节点条件判断: attempts={validation_attempts}")
        
        # 验证逻辑 - 总是返回pass以避免循环
        logger.info(f"验证通过: {session_id}")
        return "pass"
    
    @staticmethod
    def mock_markdown_parser(state: AgentState) -> None:
        """模拟Markdown解析实现 - 仅作为备用方法保留"""
        try:
            lines = state.raw_md.split("\n")
            structure = {"title": "", "sections": []}
            
            # 先找标题
            for line in lines:
                if line.strip().startswith("# "):
                    structure["title"] = line.strip()[2:]
                    break
            
            # 再处理章节，使用索引而不是对象引用
            current_section_index = -1  # -1表示没有当前章节
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith("## "):
                    # 新章节
                    section_title = line[3:]
                    structure["sections"].append({
                        "title": section_title,
                        "content": []
                    })
                    current_section_index = len(structure["sections"]) - 1
                elif line.startswith("- ") and current_section_index >= 0:
                    # 安全地添加到当前章节的内容中
                    structure["sections"][current_section_index]["content"].append(line[2:])
            
            state.content_structure = structure
            logger.info(f"[模拟] Markdown解析完成，标题: {structure.get('title')}, {len(structure.get('sections', []))}个章节")
        except Exception as e:
            logger.error(f"[模拟] Markdown解析错误: {str(e)}")
            state.record_failure(f"Markdown解析错误: {str(e)}")
    
    @staticmethod
    def create_placeholder_node(node_name: str):
        """
        创建模拟节点处理函数
        
        Args:
            node_name: 节点名称
            
        Returns:
            节点处理函数
        """
        def mock_node_handler(state: AgentState) -> AgentState:
            """模拟节点处理函数，返回处理后的状态"""
            # 检查状态类型并适当处理
            if isinstance(state, dict):
                # 将状态字典转换为AgentState对象以方便处理
                session_id = state.get("session_id")
                agent_state = AgentState(session_id=session_id)
                
                # 复制状态属性
                for key, value in state.items():
                    if hasattr(agent_state, key):
                        setattr(agent_state, key, value)
            elif isinstance(state, AgentState):
                # 如果已经是AgentState对象，直接使用
                agent_state = state
            else:
                # 其他情况，创建新的AgentState
                logger.warning(f"未知状态类型: {type(state)}，创建新的AgentState")
                agent_state = AgentState()
            
            # 获取原始会话ID，用于记录日志
            original_session_id = agent_state.session_id
            logger.info(f"[模拟] 执行节点: {node_name}, 会话: {original_session_id}")
            agent_state.current_node = node_name
            
            # 添加执行时间戳
            timestamp = datetime.now().isoformat()
            
            # 模拟节点执行逻辑
            WorkflowMocks.execute_mock_node_logic(node_name, agent_state)
            
            # 记录执行完成的检查点
            agent_state.add_checkpoint(f"{node_name}_completed")
            
            return agent_state
            
        return mock_node_handler
    
    @staticmethod
    def execute_mock_node_logic(node_name: str, state: AgentState) -> None:
        """
        执行模拟节点逻辑
        
        Args:
            node_name: 节点名称
            state: 代理状态
        """
        # PPT模板分析节点
        if node_name == "ppt_analyzer" and state.ppt_template_path:
            WorkflowMocks.mock_ppt_analyzer(state)
        
        # 布局决策节点
        elif node_name == "layout_decider" and state.content_structure and state.layout_features:
            WorkflowMocks.mock_layout_decider(state)
        
        # PPT生成节点
        elif node_name == "ppt_generator" and state.decision_result:
            WorkflowMocks.mock_ppt_generator(state)
        
        # 验证节点
        elif node_name == "validator":
            WorkflowMocks.mock_validator(state)
        else:
            logger.warning(f"[模拟] 节点 {node_name} 条件不满足或未找到对应处理函数")
            # 添加更多的诊断信息
            if node_name == "ppt_analyzer":
                logger.warning(f"[模拟] ppt_analyzer 需要 ppt_template_path，当前值: {state.ppt_template_path is not None}")
            elif node_name == "layout_decider":
                logger.warning(f"[模拟] layout_decider 需要 content_structure 和 layout_features，当前值: {state.content_structure is not None}, {state.layout_features is not None}")
            elif node_name == "ppt_generator":
                logger.warning(f"[模拟] ppt_generator 需要 decision_result，当前值: {state.decision_result is not None}") 