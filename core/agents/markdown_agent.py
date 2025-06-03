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
from core.utils.model_helper import ModelHelper
from core.utils.prompt_loader import PromptLoader
from config.content_types import (
    SEMANTIC_TYPES,
    RELATION_TYPES,
    CONTENT_STRUCTURES,
    SEMANTIC_TYPE_GUIDELINES,
    RELATION_TYPE_GUIDELINES
)

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
        # 初始化模型管理器和辅助工具
        self.model_manager = ModelManager()
        self.model_helper = ModelHelper(self.model_manager)
        self.prompt_loader = PromptLoader()
        
        # 获取模型配置 - 使用深度思考模型
        model_config = self.model_helper.get_model_config(config, "deep_thinking")
        self.llm_model = model_config.get("model")
        self.temperature = model_config.get("temperature")
        self.max_tokens = model_config.get("max_tokens")
        self.max_retries = model_config.get("max_retries", 3)
        self.model_type = "deep_thinking"  # 记录模型类型
        
        logger.info(f"初始化 MarkdownAgent，使用模型: {self.llm_model}，最大重试次数: {self.max_retries}")
    
    async def run(self, state: AgentState) -> AgentState:
        """
        执行Markdown解析
        
        Args:
            state: 当前工作流状态
            
        Returns:
            更新后的状态
        """
        logger.info("开始解析 Markdown 内容")
        
        # 检查是否有原始Markdown内容
        if not state.raw_md:
            error_msg = "没有提供 Markdown 内容"
            self.record_failure(state, error_msg)
            return state
        
        try:
            # 直接使用大模型解析Markdown内容
            logger.info("直接使用大模型解析 Markdown 结构")
            enhanced_structure = await self._parse_with_llm(state.raw_md)
            
            # 更新状态
            state.content_structure = enhanced_structure
            logger.info(f"Markdown 解析完成，标题: {enhanced_structure.get('title', '无标题')}")
            
            # 记录检查点
            self.add_checkpoint(state)
            
        except Exception as e:
            error_msg = f"Markdown 解析失败: {str(e)}"
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
        logger.info(f"使用大模型({self.llm_model})直接进行 Markdown 结构解析")
        
        # 构建提示词上下文
        context = {
            "markdown_text": markdown_text,
            "SEMANTIC_TYPES": SEMANTIC_TYPES,
            "RELATION_TYPES": RELATION_TYPES,
            "CONTENT_STRUCTURES": CONTENT_STRUCTURES,
            "SEMANTIC_TYPE_GUIDELINES": SEMANTIC_TYPE_GUIDELINES,
            "RELATION_TYPE_GUIDELINES": RELATION_TYPE_GUIDELINES
        }
        
        # 使用新的yaml格式prompt
        prompt = self.prompt_loader.render_prompt("markdown_agent_prompts", context)
        
        try:
            # 调用大模型（使用重试机制）
            response = await self.model_helper.generate_text_with_retry(
                model=self.llm_model,
                prompt=prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                max_retries=self.max_retries,
                model_type=self.model_type
            )
            
            # 解析JSON响应
            fallback_structure = {"title": "", "subtitle": "", "sections": []}
            structure = self.model_helper.parse_json_response(response, fallback_structure)
            
            if structure:
                logger.info("大模型解析完成")
                
                # 确保关键字段存在
                self._ensure_structure_fields(structure, fallback_structure)
                
                # 清理结构中的Markdown格式
                self._clean_markdown_formatting(structure)
                logger.info("清理 Markdown 格式标记完成")
                
                # 记录生成的文档结构概要
                sections_count = len(structure.get("sections", []))
                logger.info(f"解析结构: 标题: '{structure.get('title')}', 副标题: '{structure.get('subtitle')}', 章节数: {sections_count}")
            else:
                logger.warning("解析 JSON 失败，使用空结构")
                structure = fallback_structure
            
            return structure
            
        except Exception as e:
            logger.error(f"大模型解析失败: {str(e)}")
            # 失败则不返回内容
            return
    
    def _ensure_structure_fields(self, structure: Dict[str, Any], fallback_structure: Dict[str, Any]) -> None:
        """
        确保结构包含所有必要字段
        
        Args:
            structure: 要检查的结构
            fallback_structure: 回退结构（用于提供默认值）
        """
        # 确保关键字段存在
        structure["title"] = structure.get("title") or fallback_structure.get("title", "")
        structure["subtitle"] = structure.get("subtitle", fallback_structure.get("subtitle", ""))
        
        if not structure.get("sections") or not isinstance(structure["sections"], list):
            structure["sections"] = fallback_structure.get("sections", [])
            logger.warning("响应中没有有效的 sections 字段，使用基础解析的章节内容")
        else:
            # 确保每个章节都有必需的字段
            for section in structure["sections"]:
                self._ensure_section_structure(section)
    
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
        
        # 递归处理子章节
        if "subsections" in section and isinstance(section["subsections"], list):
            for subsection in section["subsections"]:
                self._ensure_section_structure(subsection)
    
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
        # 清理章节标题
        if "title" in section:
            section["title"] = self._clean_md_text(section["title"])
        
        # 清理章节内容
        if "content" in section and isinstance(section["content"], list):
            for i, item in enumerate(section["content"]):
                if isinstance(item, str):
                    section["content"][i] = self._clean_md_text(item)
                elif isinstance(item, dict):
                    # 递归清理内容项中的文本
                    for key, value in item.items():
                        if isinstance(value, str):
                            item[key] = self._clean_md_text(value)
        
        # 递归清理子章节
        if "subsections" in section and isinstance(section["subsections"], list):
            for subsection in section["subsections"]:
                self._clean_section_markdown(subsection)
    
    def _clean_md_text(self, text: str) -> str:
        """
        清理Markdown文本格式
        
        Args:
            text: 需要清理的文本
            
        Returns:
            清理后的文本
        """
        if not text:
            return ""
            
        # 清理加粗
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        # 清理斜体
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        # 清理下划线
        text = re.sub(r'__(.*?)__', r'\1', text)
        # 清理代码块
        text = re.sub(r'`(.*?)`', r'\1', text)
        # 清理链接 [文本](URL)
        text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
        # 清理标题标记 # 或 ##
        text = re.sub(r'^#+\s+', '', text)
        
        return text.strip()
    
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
    