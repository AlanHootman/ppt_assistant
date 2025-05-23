#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
内容规划Agent模块

负责将解析后的结构化内容与PPT模板进行最佳匹配，规划每个章节应使用的幻灯片布局。
"""

import logging
import json
import re
from typing import Dict, Any, List, Optional
import traceback

from core.agents.base_agent import BaseAgent
from core.engine.state import AgentState
from core.llm.model_manager import ModelManager
from config.prompts.content_planning_prompts import CONTENT_PLANNING_PROMPT

logger = logging.getLogger(__name__)

# 导入PPT管理器
try:
    from interfaces.ppt_api import PPTManager
except ImportError:
    logger = logging.getLogger(__name__)
    logger.error("无法导入PPTManager，请确保ppt_manager库已正确安装")
    PPTManager = None

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
        
        # 获取最大重试次数，如果配置中没有，默认为3次
        self.max_retries = int(config.get("max_retries", 3))
        
        # 初始化PPTManager
        try:
            from interfaces.ppt_api import PPTManager
            self.ppt_manager = PPTManager()
            logger.info("成功初始化PPT管理器")
        except ImportError as e:
            logger.error(f"无法导入PPTManager: {str(e)}")
            self.ppt_manager = None
        
        logger.info(f"初始化ContentPlanningAgent，使用模型: {self.llm_model}, 最大重试次数: {self.max_retries}")
    
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
            
            # 获取PPT模板路径
            ppt_template_path = state.ppt_template_path
            
            # 获取母版布局信息
            master_layouts = []
            if self.ppt_manager and ppt_template_path:
                logger.info(f"正在获取PPT母版布局信息: {ppt_template_path}")
                try:
                    # 加载PPT演示文稿
                    presentation = self.ppt_manager.load_presentation(ppt_template_path)
                    # 获取母版布局信息
                    master_layouts = self.ppt_manager.get_layouts_json(presentation)
                    logger.info(f"成功获取母版布局信息，共 {len(master_layouts)} 个布局")
                except Exception as e:
                    logger.warning(f"获取母版布局信息失败: {str(e)}，将使用默认布局")
            else:
                logger.warning("未初始化PPTManager或未提供PPT模板路径，将使用默认布局")
                
            # 使用LLM生成完整PPT内容规划（包括开篇页、内容页和结束页）
            content_plan = await self._generate_content_plan(
                sections, 
                available_layouts, 
                title,
                subtitle,
                ppt_template_path,
                master_layouts
            )
            
            # 检查内容计划是否为空或无效
            if not content_plan or not content_plan.get("slides"):
                error_msg = "内容规划失败，无法获取有效的幻灯片规划"
                self.record_failure(state, error_msg)
                logger.error(error_msg)
                state.planning_failed = True
                return state
            
            slides = content_plan["slides"]

            # 添加内容计划到状态中
            state.content_plan = slides
            total_slides = len(slides)

            # 设置当前章节索引为0，准备开始逐页生成
            state.current_section_index = 0
            
            logger.info(f"内容规划完成，计划生成 {total_slides} 张幻灯片")
            
            # 记录检查点
            self.add_checkpoint(state)
            
        except Exception as e:
            error_msg = f"内容规划失败: {str(e)}"
            self.record_failure(state, error_msg)
            logger.exception("内容规划过程中发生异常")
            state.planning_failed = True
        
        return state
    
    async def _generate_content_plan(
        self, 
        sections: List[Dict[str, Any]], 
        available_layouts: List[Dict[str, Any]],
        title: str,
        subtitle: str,
        ppt_template_path: Optional[str] = None,
        master_layouts: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        生成完整的内容规划，包括开篇页、内容页和结束页
        
        Args:
            sections: 内容章节列表
            available_layouts: 基于视觉分析的可用布局列表
            title: 文档标题
            subtitle: 文档副标题
            ppt_template_path: PPT模板文件路径
            master_layouts: 母版布局信息列表
            
        Returns:
            完整的内容规划
        """
        
        # 构建提示词
        prompt = self._build_planning_prompt(sections, available_layouts, title, subtitle, master_layouts)
        
        # 实现重试机制
        retry_count = 0
        empty_plan = {"slides": [], "slide_count": 0}
        
        while retry_count < self.max_retries:
            try:
                # 调用LLM获取规划结果
                logger.info(f"开始生成内容规划，尝试次数: {retry_count + 1}/{self.max_retries}")
                response = await self.model_manager.generate_text(
                    model=self.llm_model,
                    prompt=prompt,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                
                # 解析LLM响应
                content_plan = self._parse_llm_response(response, sections, available_layouts, title, subtitle)
                
                # 检查规划结果是否有效
                slides_count = len(content_plan.get('slides', []))
                logger.info(f"LLM规划完成，总计规划了 {slides_count} 张幻灯片")
                
                # 如果成功获取到有效的规划结果，直接返回
                if slides_count > 0:
                    return content_plan
                else:
                    logger.warning(f"LLM返回了空的规划结果，将重试 (尝试 {retry_count + 1}/{self.max_retries})")
                    retry_count += 1
                
            except Exception as e:
                logger.error(f"LLM规划失败 (尝试 {retry_count + 1}/{self.max_retries}): {str(e)}")
                logger.error(f"错误详情: {traceback.format_exc()}")
                retry_count += 1
                
                # 如果已达到最大重试次数，抛出异常
                if retry_count >= self.max_retries:
                    logger.error(f"内容规划失败，已达到最大重试次数 ({self.max_retries})")
                    raise ValueError(f"内容规划失败，已重试{self.max_retries}次: {str(e)}")
        
        # 如果所有重试都失败，返回空计划
        logger.error(f"所有重试尝试均失败，返回空计划")
        return empty_plan
    
    def _build_planning_prompt(
        self, 
        sections: List[Dict[str, Any]], 
        layouts: List[Dict[str, Any]],
        title: str,
        subtitle: str,
        master_layouts: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        构建用于内容规划的提示词
        
        Args:
            sections: 内容章节列表
            layouts: 可用布局列表（基于视觉分析）
            title: 文档标题
            subtitle: 文档副标题
            master_layouts: 母版布局信息列表
            
        Returns:
            提示词
        """
        # 将sections和layouts转换为格式化的JSON字符串
        sections_json = json.dumps(sections, ensure_ascii=False, indent=2)
        layouts_json = json.dumps(layouts, ensure_ascii=False, indent=2)
        
        # 构建上下文
        context = {
            "sections_json": sections_json,
            "layouts_json": layouts_json,
            "title": title,
            "subtitle": subtitle
        }
        
        # 如果有母版布局信息，添加到上下文
        if master_layouts:
            master_layouts_json = json.dumps(master_layouts, ensure_ascii=False, indent=2)
            context["master_layouts_json"] = master_layouts_json
            logger.info("已添加母版布局信息到规划提示词")
        
        # 使用ModelManager的render_template方法渲染模板
        return self.model_manager.render_template(CONTENT_PLANNING_PROMPT, context)
    
    def _parse_llm_response(
        self, 
        response: str, 
        sections: List[Dict[str, Any]], 
        layouts: List[Dict[str, Any]],
        title: str,
        subtitle: str
    ) -> Dict[str, Any]:
        """
        解析LLM响应，提取内容规划
        
        Args:
            response: LLM响应文本
            sections: 原始章节列表（用于回退）
            layouts: 可用布局列表（用于回退）
            title: 文档标题（用于回退）
            subtitle: 文档副标题（用于回退）
            
        Returns:
            内容规划字典
        """
        try:
            # 清理响应中的markdown格式代码块
            json_text = response
            if "```" in response:
                # 提取JSON代码块
                pattern = r"```(?:json)?\s*([\s\S]*?)```"
                matches = re.findall(pattern, response)
                if matches:
                    json_text = matches[0].strip()
                    logger.debug(f"提取到JSON代码块: {json_text[:100]}...")
            
            # 解析前检查并修复常见JSON错误
            json_text = self._clean_json_text(json_text)
            
            # 解析JSON
            content_plan = json.loads(json_text)
            
            # 检查内容计划结构
            if isinstance(content_plan, dict) and "slides" in content_plan:
                slides_count = len(content_plan["slides"])
                logger.info(f"LLM响应解析成功，共生成 {slides_count} 张幻灯片")
                return content_plan
            elif isinstance(content_plan, list):
                # 如果返回的是列表，转换为字典格式
                logger.info(f"LLM返回的是slides列表，共 {len(content_plan)} 张幻灯片，转换为标准格式")
                return {
                    "slides": content_plan,
                    "slide_count": len(content_plan)
                }
            else:
                logger.warning("LLM响应格式不符合预期，尝试兼容处理")
                return {
                    "slides": content_plan if isinstance(content_plan, list) else [],
                    "slide_count": len(content_plan) if isinstance(content_plan, list) else 0
                }
                
        except Exception as e:
            logger.error(f"解析LLM响应失败: {str(e)}")
            logger.error(f"响应内容前100字符: {response[:100]}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            # 返回空的内容规划
            return {"slides": [], "slide_count": 0}
    
    def _clean_json_text(self, json_text: str) -> str:
        """
        清理并修复常见的JSON语法错误
        
        Args:
            json_text: 原始JSON文本
            
        Returns:
            清理后的JSON文本
        """
        # 删除注释
        json_text = re.sub(r'//.*?\n', '\n', json_text)
        json_text = re.sub(r'/\*.*?\*/', '', json_text, flags=re.DOTALL)
        
        # 修复尾部逗号
        json_text = re.sub(r',(\s*[\]}])', r'\1', json_text)
        
        # 修复缺少引号的键名
        json_text = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', json_text)
        
        # 修复单引号
        json_text = re.sub(r"'(.*?)'", r'"\1"', json_text)
        
        return json_text
    
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
    
    def add_checkpoint(self, state: AgentState) -> None:
        """
        添加工作流检查点
        
        Args:
            state: 工作流状态
        """
        state.add_checkpoint("content_planner_completed")
        logger.info("添加检查点: content_planner_completed")
    
    def record_failure(self, state: AgentState, error: str) -> None:
        """
        记录失败信息
        
        Args:
            state: 工作流状态
            error: 错误信息
        """
        state.record_failure(error)
        logger.error(f"记录失败: {error}") 