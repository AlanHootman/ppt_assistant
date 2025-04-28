#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
内容规划Agent模块

负责将解析后的结构化内容与PPT模板进行最佳匹配，规划每个章节应使用的幻灯片布局。
"""

import logging
import json
from typing import Dict, Any, List, Optional

from core.agents.base_agent import BaseAgent
from core.engine.state import AgentState
from core.llm.model_manager import ModelManager
from config.prompts.content_planning_prompts import CONTENT_PLANNING_PROMPT

logger = logging.getLogger(__name__)

class ContentPlanningAgent(BaseAgent):
    """内容规划Agent，负责规划内容与幻灯片模板的匹配"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化内容规划Agent
        
        Args:
            config: Agent配置
        """
        super().__init__(config)
        # 初始化模型管理器
        self.model_manager = ModelManager()
        
        # 从配置获取模型类型和名称
        self.model_type = config.get("model_type", "text")
        
        # 初始化模型属性
        model_config = self.model_manager.get_model_config(self.model_type)
        self.llm_model = model_config.get("model")
        self.temperature = model_config.get("temperature", 0.7)
        self.max_tokens = model_config.get("max_tokens", 4000)
        
        logger.info(f"初始化ContentPlanningAgent，使用模型: {self.llm_model}")
    
    async def run(self, state: AgentState) -> AgentState:
        """
        执行内容规划
        
        Args:
            state: 当前工作流状态
            
        Returns:
            更新后的状态
        """
        logger.info("开始规划内容与模板匹配")
        
        # 检查必要的输入
        if not state.content_structure:
            error_msg = "没有提供内容结构"
            self.record_failure(state, error_msg)
            return state
        
        if not state.layout_features:
            error_msg = "没有提供布局特征"
            self.record_failure(state, error_msg)
            return state
        
        try:
            # 获取内容章节和可用模板
            sections = state.content_structure.get("sections", [])
            title = state.content_structure.get("title", "无标题")
            subtitle = state.content_structure.get("subtitle", "")
            available_layouts = state.layout_features.get("slideLayouts", [])
            
            if not available_layouts and state.layout_features.get("layouts"):
                # 兼容旧版API
                available_layouts = state.layout_features.get("layouts", [])
                
            # 使用LLM生成完整PPT内容规划（包括开篇页、内容页和结束页）
            content_plan = await self._generate_content_plan(
                sections, 
                available_layouts, 
                title,
                subtitle
            )
            
            # 规划slide_index
            for i, slide in enumerate(content_plan):
                slide["slide_index"] = i + 1
            
            # 添加内容计划到状态中
            state.content_plan = content_plan
            
            # 设置当前章节索引为0，准备开始逐页生成
            state.current_section_index = 0
            
            # 向后兼容：添加decision_result（旧版本API）
            state.decision_result = {
                "slides": content_plan,
                "total_slides": len(content_plan),
                "theme": state.layout_features.get("theme", {})
            }
            
            logger.info(f"内容规划完成，计划生成 {len(content_plan)} 张幻灯片")
            
            # 记录检查点
            self.add_checkpoint(state)
            
        except Exception as e:
            error_msg = f"内容规划失败: {str(e)}"
            self.record_failure(state, error_msg)
            logger.exception("内容规划过程中发生异常")
        
        return state
    
    async def _generate_content_plan(
        self, 
        sections: List[Dict[str, Any]], 
        available_layouts: List[Dict[str, Any]],
        title: str,
        subtitle: str
    ) -> List[Dict[str, Any]]:
        """
        生成完整的内容规划，包括开篇页、内容页和结束页
        
        Args:
            sections: 内容章节列表
            available_layouts: 可用布局列表
            title: 文档标题
            subtitle: 文档副标题
            
        Returns:
            完整的内容规划
        """
        # 构建提示词
        prompt = self._build_planning_prompt(sections, available_layouts, title, subtitle)
        
        try:
            # 调用LLM获取规划结果
            response = await self.model_manager.generate_text(
                model=self.llm_model,
                prompt=prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # 解析LLM响应
            content_plan = self._parse_llm_response(response, sections, available_layouts, title, subtitle)
            logger.info(f"LLM规划完成，总计规划了 {len(content_plan)} 张幻灯片")
            
            return content_plan
            
        except Exception as e:
            logger.error(f"LLM规划失败: {str(e)}")
            # 如果LLM规划失败，使用简单规则匹配
            return self._fallback_planning(sections, available_layouts, title, subtitle)
    
    def _build_planning_prompt(
        self, 
        sections: List[Dict[str, Any]], 
        layouts: List[Dict[str, Any]],
        title: str,
        subtitle: str
    ) -> str:
        """
        构建用于内容规划的提示词
        
        Args:
            sections: 内容章节列表
            layouts: 可用布局列表
            title: 文档标题
            subtitle: 文档副标题
            
        Returns:
            提示词
        """
        # 将sections和layouts转换为格式化的JSON字符串
        sections_json = json.dumps(sections, ensure_ascii=False, indent=2)
        layouts_json = json.dumps(layouts, ensure_ascii=False, indent=2)
        
        # 使用Jinja2模板渲染
        context = {
            "sections_json": sections_json,
            "layouts_json": layouts_json,
            "title": title,
            "subtitle": subtitle
        }
        
        # 使用ModelManager的render_template方法渲染模板
        return self.model_manager.render_template(CONTENT_PLANNING_PROMPT, context)
    
    def _parse_llm_response(
        self, 
        response: str, 
        sections: List[Dict[str, Any]], 
        layouts: List[Dict[str, Any]],
        title: str,
        subtitle: str
    ) -> List[Dict[str, Any]]:
        """
        解析LLM响应，提取内容规划
        
        Args:
            response: LLM响应文本
            sections: 原始章节列表（用于回退）
            layouts: 可用布局列表（用于回退）
            title: 文档标题（用于回退）
            subtitle: 文档副标题（用于回退）
            
        Returns:
            内容规划列表
        """
        try:
            # 清理响应中的markdown格式代码块
            json_text = response
            if "```json" in response:
                # 提取JSON代码块
                import re
                pattern = r"```(?:json)?\s*([\s\S]*?)```"
                matches = re.findall(pattern, response)
                if matches:
                    json_text = matches[0]
            
            # 解析JSON
            content_plan = json.loads(json_text)
            
            # 验证解析结果
            if not isinstance(content_plan, list) or len(content_plan) < 3:  # 至少需要开篇页、一个内容页和结束页
                logger.warning("LLM响应解析失败，格式不正确或长度不足")
                return self._fallback_planning(sections, layouts, title, subtitle)
            
            # 验证每个元素包含必要的字段
            for slide in content_plan:
                if "section" not in slide or "template" not in slide:
                    logger.warning("LLM响应解析失败，缺少必要字段")
                    return self._fallback_planning(sections, layouts, title, subtitle)
            
            # 检查是否包含开篇页和结束页
            has_opening = any(slide.get("slide_type") == "opening" for slide in content_plan)
            has_closing = any(slide.get("slide_type") == "closing" for slide in content_plan)
            
            if not has_opening or not has_closing:
                logger.warning("LLM响应解析失败，缺少开篇页或结束页")
                return self._fallback_planning(sections, layouts, title, subtitle)
                
            return content_plan
            
        except Exception as e:
            logger.error(f"解析LLM响应失败: {str(e)}")
            return self._fallback_planning(sections, layouts, title, subtitle)
    
    def _fallback_planning(
        self, 
        sections: List[Dict[str, Any]], 
        layouts: List[Dict[str, Any]],
        title: str,
        subtitle: str
    ) -> List[Dict[str, Any]]:
        """
        当LLM规划失败时使用的回退规划逻辑
        
        Args:
            sections: 内容章节列表
            layouts: 可用布局列表
            title: 文档标题
            subtitle: 文档副标题
            
        Returns:
            基本的内容规划列表，包含开篇页、内容页和结束页
        """
        logger.info("使用回退规划策略")
        content_plan = []
        
        # 查找合适的布局类型
        title_layout = self._find_layout_by_type(layouts, ["封面页", "标题页", "opening", "title"])
        content_layout = self._find_layout_by_type(layouts, ["内容页", "content"])
        ending_layout = self._find_layout_by_type(layouts, ["结束页", "ending", "closing", "thank"])
        
        # 如果找不到特定类型的布局，使用第一个布局
        if not title_layout and layouts:
            title_layout = layouts[0]
        if not content_layout and layouts:
            content_layout = layouts[0]
        if not ending_layout and layouts:
            ending_layout = layouts[0]
        
        # 添加开篇页
        content_plan.append({
            "slide_type": "opening",
            "section": {
                "title": title,
                "subtitle": subtitle,
                "type": "title"
            },
            "template": title_layout or {"name": "默认标题布局"},
            "reasoning": "使用回退策略选择的开篇页布局"
        })
        
        # 循环为每个章节分配模板
        for i, section in enumerate(sections):
            # 确保有可用的布局
            if not layouts:
                template = {"name": "默认内容布局"}
            elif content_layout:
                template = content_layout
            else:
                # 简单规则：轮流使用不同的布局
                layout_index = i % len(layouts)
                template = layouts[layout_index]
            
            content_plan.append({
                "slide_type": "content",
                "section": section,
                "template": template,
                "reasoning": "使用回退策略选择的内容页布局"
            })
        
        # 添加结束页
        content_plan.append({
            "slide_type": "closing",
            "section": {
                "title": "谢谢",
                "type": "ending"
            },
            "template": ending_layout or {"name": "默认结束布局"},
            "reasoning": "使用回退策略选择的结束页布局"
        })
        
        return content_plan
    
    def _find_layout_by_type(self, layouts: List[Dict[str, Any]], type_keywords: List[str]) -> Optional[Dict[str, Any]]:
        """
        根据类型关键词查找合适的布局
        
        Args:
            layouts: 可用布局列表
            type_keywords: 类型关键词列表
            
        Returns:
            找到的布局，如果没有找到返回None
        """
        if not layouts:
            return None
            
        # 首先尝试在type字段中查找
        for layout in layouts:
            layout_type = layout.get("type", "").lower()
            if layout_type and any(keyword.lower() in layout_type for keyword in type_keywords):
                return layout
        
        # 然后尝试在name字段中查找
        for layout in layouts:
            layout_name = layout.get("name", "").lower()
            if layout_name and any(keyword.lower() in layout_name for keyword in type_keywords):
                return layout
        
        # 最后尝试在purpose字段中查找
        for layout in layouts:
            purpose = layout.get("purpose", "").lower()
            if purpose and any(keyword.lower() in purpose for keyword in type_keywords):
                return layout
                
        # 如果都没找到，返回None
        return None 