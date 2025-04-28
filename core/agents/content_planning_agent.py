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
            available_layouts = state.layout_features.get("layouts", [])
            
            # 准备内容计划
            content_plan = []
            
            # 首先添加标题页
            title = state.content_structure.get("title", "无标题")
            subtitle = state.content_structure.get("subtitle", "")
            
            # 找到标题页模板
            title_layout = next((l for l in available_layouts if l.get("name") == "title"), 
                                available_layouts[0] if available_layouts else {"name": "default"})
            
            # 添加标题页计划
            content_plan.append({
                "section": {
                    "title": title,
                    "subtitle": subtitle,
                    "type": "title"
                },
                "template": title_layout,
                "slide_index": 1
            })
            
            # 使用LLM优化匹配各章节与布局
            section_plans = await self._plan_with_llm(sections, available_layouts)
            
            # 将章节计划添加到内容计划中
            for i, section_plan in enumerate(section_plans):
                content_plan.append({
                    "section": section_plan["section"],
                    "template": section_plan["template"],
                    "slide_index": i + 2  # +2因为标题页是第1页
                })
            
            # 更新状态
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
        
        return state
    
    async def _plan_with_llm(self, sections: List[Dict[str, Any]], 
                           available_layouts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        使用LLM为内容章节选择最合适的模板
        
        Args:
            sections: 内容章节列表
            available_layouts: 可用布局列表
            
        Returns:
            章节与模板的匹配计划
        """
        # 如果没有章节或布局，返回空列表
        if not sections or not available_layouts:
            return []
        
        # 构建提示词
        prompt = self._build_planning_prompt(sections, available_layouts)
        
        try:
            # 调用LLM获取规划结果
            response = await self.model_manager.generate_text(
                model=self.llm_model,
                prompt=prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # 解析LLM响应
            section_plans = self._parse_llm_response(response, sections, available_layouts)
            logger.info(f"LLM规划完成，规划了 {len(section_plans)} 个章节")
            
            return section_plans
            
        except Exception as e:
            logger.error(f"LLM规划失败: {str(e)}")
            # 如果LLM规划失败，使用简单规则匹配
            return self._fallback_planning(sections, available_layouts)
    
    def _build_planning_prompt(self, sections: List[Dict[str, Any]], 
                              layouts: List[Dict[str, Any]]) -> str:
        """
        构建用于内容规划的提示词
        
        Args:
            sections: 内容章节列表
            layouts: 可用布局列表
            
        Returns:
            提示词
        """
        # 将sections和layouts转换为格式化的JSON字符串
        sections_json = json.dumps(sections, ensure_ascii=False, indent=2)
        layouts_json = json.dumps(layouts, ensure_ascii=False, indent=2)
        
        # 使用导入的prompt模板并格式化
        return CONTENT_PLANNING_PROMPT.format(
            sections_json=sections_json,
            layouts_json=layouts_json
        )
    
    def _parse_llm_response(self, response: str, sections: List[Dict[str, Any]], 
                           layouts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        解析LLM响应，提取章节规划
        
        Args:
            response: LLM响应文本
            sections: 原始章节列表（用于回退）
            layouts: 可用布局列表（用于回退）
            
        Returns:
            章节规划列表
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
            section_plans = json.loads(json_text)
            
            # 验证解析结果
            if not isinstance(section_plans, list):
                logger.warning("LLM响应解析失败，不是列表格式")
                return self._fallback_planning(sections, layouts)
            
            # 验证每个元素包含必要的字段
            for plan in section_plans:
                if "section" not in plan or "template" not in plan:
                    logger.warning("LLM响应解析失败，缺少必要字段")
                    return self._fallback_planning(sections, layouts)
            
            return section_plans
            
        except Exception as e:
            logger.error(f"解析LLM响应失败: {str(e)}")
            return self._fallback_planning(sections, layouts)
    
    def _fallback_planning(self, sections: List[Dict[str, Any]], 
                          layouts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        当LLM规划失败时使用的回退规划逻辑
        
        Args:
            sections: 内容章节列表
            layouts: 可用布局列表
            
        Returns:
            简单的章节规划列表
        """
        logger.info("使用回退规划策略")
        section_plans = []
        
        # 循环为每个章节分配模板
        for i, section in enumerate(sections):
            # 简单规则：轮流使用不同的布局
            layout_index = i % len(layouts)
            template = layouts[layout_index]
            
            section_plans.append({
                "section": section,
                "template": template,
                "reasoning": "基于简单轮换规则选择"
            })
        
        return section_plans 