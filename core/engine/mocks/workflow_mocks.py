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
        raw_md = getattr(state, 'raw_md', '')
        logger.info(f"[模拟] 解析Markdown文本，长度: {len(raw_md) if raw_md else 0}")
        
        # 解析标题和子标题
        title = "示例PPT"
        subtitle = "自动生成"
        
        if raw_md:
            lines = raw_md.split("\n")
            if lines and lines[0].startswith("# "):
                title = lines[0].replace("# ", "").strip()
                if len(lines) > 1 and lines[1].startswith("## "):
                    subtitle = lines[1].replace("## ", "").strip()
        
        # 创建模拟的内容结构
        state.content_structure = {
            "title": title,
            "subtitle": subtitle,
            "sections": []
        }
        
        # 解析章节内容
        if raw_md:
            current_section = None
            current_content = []
            
            for line in raw_md.split("\n"):
                if line.startswith("## "):
                    # 如果有未完成的章节，保存它
                    if current_section:
                        state.content_structure["sections"].append({
                            "title": current_section,
                            "content": current_content
                    })
                    
                    # 开始新章节
                    current_section = line.replace("## ", "").strip()
                    current_content = []
                elif line.startswith("- ") and current_section:
                    # 添加到当前章节内容
                    current_content.append(line.replace("- ", "").strip())
            
            # 保存最后一个章节
            if current_section:
                state.content_structure["sections"].append({
                    "title": current_section,
                    "content": current_content
                })
        
        logger.info(f"[模拟] Markdown解析完成: 标题='{title}', {len(state.content_structure.get('sections', []))}个章节")
    
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
        根据节点名称执行相应的模拟逻辑
        
        Args:
            node_name: 节点名称
            state: 代理状态
        """
        # 记录开始执行
        logger.info(f"模拟执行节点: {node_name}")
        
        # 根据节点类型选择执行逻辑
        if node_name == "markdown_parser":
            WorkflowMocks.mock_markdown_parser(state)
        elif node_name == "ppt_analyzer":
            WorkflowMocks.mock_ppt_analyzer(state)
        elif node_name == "content_planner":
            WorkflowMocks.mock_content_planner(state)
        elif node_name == "slide_generator":
            # 执行合并后的幻灯片生成和验证功能
            WorkflowMocks.mock_slide_generator_with_validation(state)
        elif node_name == "next_slide_or_end":
            WorkflowMocks.mock_next_slide_or_end(state)
        elif node_name == "ppt_finalizer":
            WorkflowMocks.mock_ppt_generator(state)
        else:
            logger.warning(f"未知节点类型: {node_name}，使用通用模拟执行")
            state.add_checkpoint(f"{node_name}_executed")

    @staticmethod
    def mock_content_planner(state: AgentState) -> None:
        """模拟内容规划节点实现"""
        logger.info("模拟执行内容规划节点")
        # 基于内容结构和布局特征，规划内容与幻灯片匹配
        content_plan = []
        
        if state.content_structure and state.layout_features:
            # 获取章节和模板
            sections = state.content_structure.get("sections", [])
            templates = state.layout_features.get("layouts", [])
            
            # 为每个章节选择合适的模板
            for i, section in enumerate(sections):
                template_index = i % len(templates) if templates else 0
                template = templates[template_index] if templates else {"name": "default"}
                
                content_plan.append({
                    "section": section,
                    "template": template,
                    "slide_index": i + 1
                })
            
            # 创建决策结果
            state.decision_result = {
                "slides": content_plan,
                "total_slides": len(content_plan),
                "theme": state.layout_features.get("theme", {})
            }
            
            # 更新为新的内容规划格式
            state.content_plan = content_plan
            
            logger.info(f"内容规划完成，计划生成 {len(content_plan)} 张幻灯片")
        else:
            logger.warning("无法执行内容规划，缺少内容结构或布局特征")
            state.record_failure("内容规划失败：缺少必要数据")

    @staticmethod
    def mock_slide_generator_with_validation(state: AgentState) -> None:
        """模拟幻灯片生成和验证合并节点实现"""
        logger.info(f"模拟执行幻灯片生成节点(包含验证)，章节索引: {state.current_section_index}")
        
        content_plan = getattr(state, 'content_plan', None)
        if not content_plan and state.decision_result and "slides" in state.decision_result:
            content_plan = state.decision_result.get("slides", [])
            
        if content_plan:
            if state.current_section_index is None:
                state.current_section_index = 0
            
            if 0 <= state.current_section_index < len(content_plan):
                current_slide_plan = content_plan[state.current_section_index]
                
                # 模拟生成幻灯片
                state.current_slide = {
                    "slide_id": f"slide_{state.current_section_index}",
                    "content": current_slide_plan.get("section", {}),
                    "template": current_slide_plan.get("template", {}),
                    "image_path": f"workspace/sessions/{state.session_id}/slide_{state.current_section_index}.png",
                    "operations": [
                        {"element_id": "title_1", "operation": "replace_text", "content": "模拟标题"},
                        {"element_id": "content_1", "operation": "replace_text", "content": "模拟内容项"}
                    ]
                }
                
                # 内置验证功能
                if not hasattr(state, "validation_attempts") or state.validation_attempts is None:
                    state.validation_attempts = 0
                state.validation_attempts += 1
                
                # 设置验证结果(始终为通过，以保持工作流进行)
                state.validation_result = True
                
                logger.info(f"幻灯片生成和验证完成: {state.current_slide.get('slide_id')}, 验证通过: {state.validation_result}")
            else:
                logger.warning(f"无效的章节索引: {state.current_section_index}")
                state.record_failure(f"幻灯片生成失败：无效的章节索引 {state.current_section_index}")
                state.validation_result = False
        else:
            logger.warning("无法生成幻灯片，缺少内容计划或决策结果")
            state.record_failure("幻灯片生成失败：缺少内容计划或决策结果")
            state.validation_result = False

    @staticmethod
    def mock_next_slide_or_end(state: AgentState) -> None:
        """模拟next_slide_or_end节点实现"""
        logger.info("模拟执行下一页或结束判断节点")
        
        content_plan = getattr(state, 'content_plan', None)
        if not content_plan and hasattr(state, 'decision_result'):
            content_plan = state.decision_result.get('slides', [])
        
        total_slides = len(content_plan) if content_plan else 0
        
        # 当前幻灯片已验证通过，将其添加到已生成列表中
        if hasattr(state, 'current_slide') and state.current_slide and getattr(state, 'validation_result', False):
            if not hasattr(state, 'generated_slides') or state.generated_slides is None:
                state.generated_slides = []
            state.generated_slides.append(state.current_slide)
            logger.info(f"添加幻灯片到生成列表: {state.current_slide.get('slide_id')}")
        
            # 更新章节索引
        if state.current_section_index is None:
            state.current_section_index = 0
        else:
            state.current_section_index += 1
        
        # 检查是否还有更多内容需要处理
        state.has_more_content = state.current_section_index < total_slides if total_slides > 0 else False
        
        logger.info(f"章节进度: {state.current_section_index}/{total_slides}, 还有更多内容: {state.has_more_content}")

    @staticmethod
    def mock_ppt_finalizer(state: AgentState) -> None:
        """模拟PPT清理与保存节点实现"""
        logger.info("模拟执行PPT清理与保存节点")
        
        if hasattr(state, "generated_slides") and state.generated_slides:
            # 创建输出目录
            if state.output_dir:
                os.makedirs(state.output_dir, exist_ok=True)
                
                # 模拟保存PPT文件
                output_file = os.path.join(state.output_dir, f"{state.session_id}.pptx")
                state.output_ppt_path = output_file
                state.ppt_file_path = output_file  # 同时设置ppt_file_path以保持一致性
                
                # 实际情况下，这里应该调用PPT管理器保存文件
                # 仅记录一个假的保存操作
                with open(f"{output_file}.log", "w") as f:
                    f.write(f"PPT文件模拟保存于 {datetime.now()}\n")
                    f.write(f"包含 {len(state.generated_slides)} 张幻灯片\n")
                
                logger.info(f"PPT文件已保存: {output_file}")
            else:
                logger.warning("无法保存PPT，未指定输出目录")
                state.record_failure("PPT保存失败：未指定输出目录")
        else:
            logger.warning("无法完成PPT，没有已生成的幻灯片")
            state.record_failure("PPT清理与保存失败：没有已生成的幻灯片") 