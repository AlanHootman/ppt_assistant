#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
幻灯片生成Agent模块

负责根据内容规划生成具体的幻灯片内容，包括标题、文本、图片等元素。
"""

import logging
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

from core.agents.base_agent import BaseAgent
from core.engine.state import AgentState
from core.llm.model_manager import ModelManager
from config.prompts.slide_generator_prompts import SLIDE_GENERATION_PROMPT

logger = logging.getLogger(__name__)

class SlideGeneratorAgent(BaseAgent):
    """幻灯片生成Agent，负责生成具体的幻灯片内容"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化幻灯片生成Agent
        
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
        self.llm_model = model_config.get("model")
        self.temperature = model_config.get("temperature", 0.7)
        self.max_tokens = model_config.get("max_tokens", 4000)
        
        logger.info(f"初始化SlideGeneratorAgent，使用模型: {self.llm_model}")
    
    async def run(self, state: AgentState) -> AgentState:
        """
        执行幻灯片生成
        
        Args:
            state: 当前工作流状态
            
        Returns:
            更新后的状态
        """
        logger.info("开始生成幻灯片")
        
        # 检查必要的输入
        if not state.decision_result or "slides" not in state.decision_result:
            error_msg = "缺少幻灯片决策结果"
            self.record_failure(state, error_msg)
            return state
        
        try:
            # 获取幻灯片计划
            slides = state.decision_result.get("slides", [])
            
            # 检查当前章节索引
            if state.current_section_index is None:
                state.current_section_index = 0
            
            # 确保章节索引在有效范围内
            if not 0 <= state.current_section_index < len(slides):
                error_msg = f"无效的章节索引: {state.current_section_index}"
                self.record_failure(state, error_msg)
                return state
            
            # 获取当前章节的幻灯片计划
            current_slide_plan = slides[state.current_section_index]
            section = current_slide_plan.get("section", {})
            template = current_slide_plan.get("template", {})
            
            # 使用LLM生成幻灯片内容
            slide_content = await self._generate_slide_content(section, template)
            
            # 生成幻灯片图像（在实际应用中，这里会调用渲染服务）
            slide_image_path = self._generate_slide_image(state.session_id, state.current_section_index)
            
            # 更新当前幻灯片
            state.current_slide = {
                "slide_id": f"slide_{state.current_section_index}",
                "content": slide_content,
                "template": template,
                "image_path": slide_image_path,
                "section_index": state.current_section_index
            }
            
            logger.info(f"幻灯片生成完成: {state.current_slide.get('slide_id')}")
            
            # 记录检查点
            self.add_checkpoint(state)
            
        except Exception as e:
            error_msg = f"幻灯片生成失败: {str(e)}"
            self.record_failure(state, error_msg)
        
        return state
    
    async def _generate_slide_content(self, section: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用LLM生成幻灯片内容
        
        Args:
            section: 章节内容
            template: 布局模板
            
        Returns:
            格式化的幻灯片内容
        """
        # 构建提示词
        prompt = self._build_slide_prompt(section, template)
        
        try:
            # 调用LLM生成内容
            response = await self.model_manager.generate_text(
                model=self.llm_model,
                prompt=prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # 解析LLM响应
            slide_content = self._parse_llm_response(response, section, template)
            logger.info("LLM幻灯片内容生成成功")
            
            return slide_content
            
        except Exception as e:
            logger.error(f"LLM生成幻灯片内容失败: {str(e)}")
            # 如果LLM生成失败，使用简单的内容生成
            return self._fallback_content_generation(section, template)
    
    def _build_slide_prompt(self, section: Dict[str, Any], template: Dict[str, Any]) -> str:
        """
        构建用于幻灯片生成的提示词
        
        Args:
            section: 章节内容
            template: 布局模板
            
        Returns:
            提示词
        """
        # 将section和template转换为格式化的JSON字符串
        section_json = json.dumps(section, ensure_ascii=False, indent=2)
        template_json = json.dumps(template, ensure_ascii=False, indent=2)
        
        # 使用导入的prompt模板并格式化
        return SLIDE_GENERATION_PROMPT.format(
            section_json=section_json,
            template_json=template_json
        )
    
    def _parse_llm_response(self, response: str, section: Dict[str, Any], 
                           template: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析LLM响应，提取幻灯片内容
        
        Args:
            response: LLM响应文本
            section: 原始章节（用于回退）
            template: 布局模板（用于回退）
            
        Returns:
            格式化的幻灯片内容
        """
        try:
            # 清理响应中的markdown格式代码块
            json_text = response
            if "```json" in response or "```" in response:
                # 提取JSON代码块
                import re
                pattern = r"```(?:json)?\s*([\s\S]*?)```"
                matches = re.findall(pattern, response)
                if matches:
                    json_text = matches[0]
            
            # 解析JSON
            slide_content = json.loads(json_text)
            
            # 验证必要的字段
            if "title" not in slide_content:
                logger.warning("LLM响应解析失败，缺少标题")
                return self._fallback_content_generation(section, template)
            
            return slide_content
            
        except Exception as e:
            logger.error(f"解析LLM响应失败: {str(e)}")
            return self._fallback_content_generation(section, template)
    
    def _fallback_content_generation(self, section: Dict[str, Any], 
                                    template: Dict[str, Any]) -> Dict[str, Any]:
        """
        当LLM生成失败时使用的回退内容生成逻辑
        
        Args:
            section: 章节内容
            template: 布局模板
            
        Returns:
            简单的幻灯片内容
        """
        logger.info("使用回退内容生成策略")
        
        # 提取章节标题和内容
        title = section.get("title", "未命名幻灯片")
        content = section.get("content", [])
        items = section.get("items", [])
        
        # 创建基本内容
        slide_content = {
            "title": title,
            "bullets": items[:6] if items else [],  # 限制6个项目符号
            "paragraphs": content[:2] if content else []  # 限制2个段落
        }
        
        # 根据模板类型添加特定内容
        template_name = template.get("name", "").lower()
        
        if "title" in template_name:
            # 标题页
            slide_content["subtitle"] = section.get("subtitle", "")
        elif "two" in template_name or "column" in template_name:
            # 双栏布局
            if items:
                midpoint = len(items) // 2
                slide_content["leftContent"] = items[:midpoint]
                slide_content["rightContent"] = items[midpoint:midpoint*2]
        elif "image" in template_name:
            # 图片布局
            slide_content["imagePath"] = "placeholder_image.jpg"
            slide_content["imageCaption"] = "图片说明"
        
        # 添加演讲者注释
        slide_content["notes"] = "这张幻灯片介绍" + title
        
        return slide_content
    
    def _generate_slide_image(self, session_id: str, slide_index: int) -> str:
        """
        生成幻灯片预览图像（模拟实现）
        
        Args:
            session_id: 会话ID
            slide_index: 幻灯片索引
            
        Returns:
            幻灯片图像路径
        """
        # 在实际项目中，这里会调用渲染服务来生成幻灯片图像
        # 现在仅返回一个预期的路径
        
        # 确保会话目录存在
        session_dir = Path(f"workspace/sessions/{session_id}")
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # 返回预期的图像路径
        return str(session_dir / f"slide_{slide_index}.png") 