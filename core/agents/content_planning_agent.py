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
        # 直接使用模型配置中的值，不再需要类型转换
        self.temperature = model_config.get("temperature")
        self.max_tokens = model_config.get("max_tokens")
        
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
            
            # 检查是否有PPT模板路径
            ppt_template_path = state.ppt_template_path
            if not ppt_template_path:
                logger.warning("没有提供PPT模板路径，将不使用presentation信息")
                
            # 使用LLM生成完整PPT内容规划（包括开篇页、内容页和结束页）
            content_plan = await self._generate_content_plan(
                sections, 
                available_layouts, 
                title,
                subtitle,
                ppt_template_path
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
        subtitle: str,
        ppt_template_path: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        生成完整的内容规划，包括开篇页、内容页和结束页
        
        Args:
            sections: 内容章节列表
            available_layouts: 可用布局列表
            title: 文档标题
            subtitle: 文档副标题
            ppt_template_path: PPT模板文件路径
            
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
    
    def _build_planning_prompt(
        self, 
        sections: List[Dict[str, Any]], 
        layouts: List[Dict[str, Any]],
        title: str,
        subtitle: str,
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
            
            logger.info(f"LLM响应解析成功，共生成{len(content_plan)}张幻灯片")
            return content_plan
            
        except Exception as e:
            logger.error(f"解析LLM响应失败: {str(e)}")
    
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