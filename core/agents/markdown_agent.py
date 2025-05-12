#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Markdown解析Agent模块

负责解析Markdown文本，提取标题、段落、列表等结构化内容，并使用大模型对内容进行理解和分析。
"""

import logging
import re
import json
import os
from typing import Dict, Any, List, Optional

from core.agents.base_agent import BaseAgent
from core.engine.state import AgentState
from core.llm.model_manager import ModelManager
from config.prompts.markdown_agent_prompts import ANALYSIS_PROMPT

logger = logging.getLogger(__name__)

class MarkdownAgent(BaseAgent):
    """Markdown解析Agent，负责解析Markdown内容并提取结构"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化Markdown解析Agent
        
        Args:
            config: Agent配置
        """
        super().__init__(config)
        # 初始化模型管理器，让它从环境变量加载配置
        self.model_manager = ModelManager()
        
        # 从配置获取模型类型和名称
        self.model_type = config.get("model_type", "text")        
        self.max_retries = config.get("max_retries", 3)
        
        # 初始化模型属性
        model_config = self.model_manager.get_model_config(self.model_type)
        self.llm_model = model_config.get("model")
        # 直接使用模型配置中的值，不再需要类型转换
        self.temperature = model_config.get("temperature")
        self.max_tokens = model_config.get("max_tokens")
        
        logger.info(f"初始化MarkdownAgent，使用模型: {self.llm_model}")
    
    async def run(self, state: AgentState) -> AgentState:
        """
        执行Markdown解析
        
        Args:
            state: 当前工作流状态
            
        Returns:
            更新后的状态
        """
        logger.info("开始解析Markdown内容")
        
        # 检查是否有原始Markdown内容
        if not state.raw_md:
            error_msg = "没有提供Markdown内容"
            self.record_failure(state, error_msg)
            return state
        
        try:
            # 直接使用大模型解析Markdown内容
            logger.info("直接使用大模型解析Markdown结构")
            enhanced_structure = await self._parse_with_llm(state.raw_md)
            
            # 更新状态
            state.content_structure = enhanced_structure
            logger.info(f"Markdown解析完成，标题: {enhanced_structure.get('title', '无标题')}")
            
            # 记录检查点
            self.add_checkpoint(state)
            
        except Exception as e:
            error_msg = f"Markdown解析失败: {str(e)}"
            self.record_failure(state, error_msg)
        
        return state
    
    async def _parse_with_llm(self, markdown_text: str) -> Dict[str, Any]:
        """
        直接使用大模型解析Markdown文本，不依赖基础解析器
        
        Args:
            markdown_text: 原始Markdown文本
            
        Returns:
            解析后的结构化内容
        """
        logger.info(f"使用大模型({self.llm_model})直接进行Markdown结构解析")
        
        # 构建提示词上下文
        context = {
            "markdown_text": markdown_text,
        }
        
        # 使用模型管理器的模板渲染方法
        prompt = self.model_manager.render_template(ANALYSIS_PROMPT, context)
        
        try:
            # 调用大模型
            response = await self.model_manager.generate_text(
                model=self.llm_model,
                prompt=prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # 解析JSON响应
            structure = self._parse_llm_response(response, {"title": "", "subtitle": "", "sections": []})
            logger.info("大模型解析完成")
            
            # 清理结构中的Markdown格式
            self._clean_markdown_formatting(structure)
            logger.info("清理Markdown格式标记完成")
            
            # 记录生成的文档结构概要
            sections_count = len(structure.get("sections", []))
            logger.info(f"解析结构: 标题: '{structure.get('title')}', 副标题: '{structure.get('subtitle')}', 章节数: {sections_count}")
            
            return structure
            
        except Exception as e:
            logger.error(f"大模型解析失败: {str(e)}")
            # 创建一个基础的空结构作为返回
            return {"title": "", "subtitle": "", "sections": []}
    
    def _parse_llm_response(self, response: str, fallback_structure: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析大模型的响应，提取JSON结构
        
        Args:
            response: 大模型响应
            fallback_structure: 失败时的回退结构
            
        Returns:
            解析后的结构
        """
        try:
            # 提取JSON内容（如果在代码块中）
            json_text = response
            if "```json" in response:
                match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response)
                if match:
                    json_text = match.group(1)
            elif "```" in response:
                match = re.search(r"```\s*([\s\S]*?)```", response)
                if match:
                    json_text = match.group(1)
            
            # 解析JSON
            structure = json.loads(json_text)
            
            # 确保关键字段存在
            structure["title"] = structure.get("title") or fallback_structure.get("title", "")
            structure["subtitle"] = structure.get("subtitle", fallback_structure.get("subtitle", ""))
            
            if not structure.get("sections") or not isinstance(structure["sections"], list):
                structure["sections"] = fallback_structure.get("sections", [])
                logger.warning("响应中没有有效的sections字段，使用基础解析的章节内容")
            else:
                # 确保每个章节都有必需的字段
                for section in structure["sections"]:
                    self._ensure_section_structure(section)
            
            logger.info(f"解析成功 - 标题: '{structure['title']}', 副标题: '{structure['subtitle']}'")
            
            return structure
            
        except Exception as e:
            logger.error(f"解析大模型响应失败: {str(e)}")
            return fallback_structure
    
    def _ensure_section_structure(self, section: Dict[str, Any]) -> None:
        """
        确保章节结构符合预期格式
        
        Args:
            section: 章节结构
        """
        # 确保标题存在
        if "title" not in section:
            section["title"] = "未命名章节"
        
        # 确保content数组存在
        if "content" not in section:
            section["content"] = []
        elif not isinstance(section["content"], list):
            section["content"] = [str(section["content"])]
        
        # 确保语义类型字段存在
        if "semantic_type" not in section:
            section["semantic_type"] = "concept"
        
        # 确保关系类型字段存在
        if "relation_type" not in section:
            section["relation_type"] = "hierarchical"
        
        # 确保可视化建议字段存在
        if "visualization_suggestion" not in section:
            section["visualization_suggestion"] = "bullet_points"
        
        # 递归处理子章节
        if "subsections" in section and isinstance(section["subsections"], list):
            for subsection in section["subsections"]:
                self._ensure_section_structure(subsection)
    
    def add_checkpoint(self, state: AgentState) -> None:
        """
        添加工作流检查点
        
        Args:
            state: 工作流状态
        """
        state.add_checkpoint("markdown_parser_completed")
        logger.info("添加检查点: markdown_parser_completed")
    
    def record_failure(self, state: AgentState, error: str) -> None:
        """
        记录失败信息
        
        Args:
            state: 工作流状态
            error: 错误信息
        """
        state.record_failure(error)
        logger.error(f"记录失败: {error}")
    
    def _clean_markdown_formatting(self, structure: Dict[str, Any]) -> None:
        """
        递归清理结构中的Markdown格式标记，如加粗(**文字**)、斜体(*文字*)等
        
        Args:
            structure: 需要清理的结构
        """
        # 清理标题和副标题
        if "title" in structure:
            structure["title"] = self._clean_md_text(structure["title"])
        if "subtitle" in structure:
            structure["subtitle"] = self._clean_md_text(structure["subtitle"])
        
        # 清理sections
        for section in structure.get("sections", []):
            self._clean_section_markdown(section)
    
    def _clean_section_markdown(self, section: Dict[str, Any]) -> None:
        """
        递归清理章节中的Markdown格式
        
        Args:
            section: 需要清理的章节
        """
        # 清理标题
        if "title" in section:
            section["title"] = self._clean_md_text(section["title"])
        
        # 清理content
        if "content" in section and isinstance(section["content"], list):
            for i, item in enumerate(section["content"]):
                if isinstance(item, str):
                    # 普通文本项
                    section["content"][i] = self._clean_md_text(item)
                elif isinstance(item, dict):
                    # 结构化内容项（如列表）
                    if "type" in item and "items" in item and isinstance(item["items"], list):
                        item["items"] = [self._clean_md_text(list_item) for list_item in item["items"]]
        
        # 递归清理子章节
        if "subsections" in section and isinstance(section["subsections"], list):
            for subsection in section["subsections"]:
                self._clean_section_markdown(subsection)
    
    def _clean_md_text(self, text: str) -> str:
        """
        清理单个文本中的Markdown格式
        
        Args:
            text: 需要清理的文本
            
        Returns:
            清理后的文本
        """
        if not isinstance(text, str):
            return text
        
        # 清理加粗 (**text** 或 __text__)
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'__(.*?)__', r'\1', text)
        
        # 清理斜体 (*text* 或 _text_)
        text = re.sub(r'(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)', r'\1', text)
        text = re.sub(r'(?<!_)_(?!_)(.*?)(?<!_)_(?!_)', r'\1', text)
        
        # 清理行内代码 (`text`)
        text = re.sub(r'`(.*?)`', r'\1', text)
        
        # 清理删除线 (~~text~~)
        text = re.sub(r'~~(.*?)~~', r'\1', text)
        
        # 清理链接 [text](url)
        text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
        
        # 清理图片 ![alt](url)
        text = re.sub(r'!\[(.*?)\]\(.*?\)', r'\1', text)
        
        # 清理HTML标签
        text = re.sub(r'<[^>]*>', '', text)
        
        return text
    