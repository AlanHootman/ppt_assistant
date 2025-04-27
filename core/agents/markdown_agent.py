#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Markdown解析Agent模块

负责解析Markdown文本，提取标题、段落、列表等结构化内容。
"""

import logging
import re
from typing import Dict, Any, List, Optional

from core.agents.base_agent import BaseAgent
from core.engine.state import AgentState

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
        # 配置LLM模型，实际项目中会加载OpenAI等模型
        self.llm_model = config.get("llm_model", "gpt-4")
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
            # 使用本地解析方法解析Markdown
            content_structure = self._parse_markdown(state.raw_md)
            
            # 更新状态
            state.content_structure = content_structure
            logger.info(f"Markdown解析完成，标题: {content_structure.get('title', '无标题')}")
            
            # 记录检查点
            self.add_checkpoint(state)
            
        except Exception as e:
            error_msg = f"Markdown解析失败: {str(e)}"
            self.record_failure(state, error_msg)
        
        return state
    
    def _parse_markdown(self, markdown_text: str) -> Dict[str, Any]:
        """
        解析Markdown文本
        
        Args:
            markdown_text: Markdown文本
            
        Returns:
            解析后的结构化内容
        """
        # 初始化结构
        structure = {
            "title": "",
            "sections": []
        }
        
        # 按行分割
        lines = markdown_text.split("\n")
        
        # 存储当前处理的章节索引
        current_section_index = -1
        
        # 处理每一行
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 处理一级标题（文档标题）
            if line.startswith("# "):
                structure["title"] = line[2:].strip()
                
            # 处理二级标题（章节标题）
            elif line.startswith("## "):
                structure["sections"].append({
                    "title": line[3:].strip(),
                    "content": [],
                    "items": []
                })
                current_section_index = len(structure["sections"]) - 1
                
            # 处理列表项
            elif line.startswith("- ") and current_section_index >= 0:
                # 将列表项添加到当前章节
                structure["sections"][current_section_index]["items"].append(line[2:].strip())
                
            # 处理普通段落
            elif current_section_index >= 0:
                # 将段落添加到当前章节
                structure["sections"][current_section_index]["content"].append(line)
        
        logger.debug(f"解析结果: 标题={structure['title']}, 章节数={len(structure['sections'])}")
        return structure
    
    def _extract_sections_with_llm(self, markdown_text: str) -> Dict[str, Any]:
        """
        使用LLM提取Markdown结构（示例实现，实际项目中会集成OpenAI等）
        
        Args:
            markdown_text: Markdown文本
            
        Returns:
            LLM解析的结构化内容
        """
        # 此为示例实现，实际项目中会调用OpenAI等LLM
        logger.info(f"使用LLM({self.llm_model})解析Markdown")
        
        # 模拟LLM解析结果
        return {
            "title": "示例文档标题",
            "sections": [
                {
                    "title": "示例章节1",
                    "content": ["这是章节1的内容"],
                    "items": ["列表项1", "列表项2"]
                },
                {
                    "title": "示例章节2",
                    "content": ["这是章节2的内容"],
                    "items": ["列表项A", "列表项B"]
                }
            ]
        } 