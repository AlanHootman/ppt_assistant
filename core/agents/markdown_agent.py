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
from config.prompts.markdown_agent_prompts import ANALYSIS_PROMPT, SECTION_EXTRACTION_PROMPT

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
        # 配置LLM模型
        self.llm_model = config.get("llm_model", "gpt-4")
        self.model_manager = ModelManager()
        self.temperature = config.get("temperature", 0.2)  # 低温度以获得更确定性的输出
        self.max_tokens = config.get("max_tokens", 4000)   # 足够长的输出以容纳完整结构
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
            # 首先使用基础解析获取基本结构
            basic_structure = self._parse_markdown(state.raw_md)
            
            # 使用大模型对内容进行深度理解
            enhanced_structure = await self._enhance_with_llm(state.raw_md, basic_structure)
            
            # 更新状态
            state.content_structure = enhanced_structure
            logger.info(f"Markdown解析完成，标题: {enhanced_structure.get('title', '无标题')}")
            
            # 记录检查点
            self.add_checkpoint(state)
            
        except Exception as e:
            error_msg = f"Markdown解析失败: {str(e)}"
            self.record_failure(state, error_msg)
        
        return state
    
    def _parse_markdown(self, markdown_text: str) -> Dict[str, Any]:
        """
        基础解析Markdown文本，提取基本结构
        
        Args:
            markdown_text: Markdown文本
            
        Returns:
            解析后的基本结构化内容
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
                    "items": [],
                    "code_blocks": []
                })
                current_section_index = len(structure["sections"]) - 1
                
            # 处理三级标题（子章节）
            elif line.startswith("### ") and current_section_index >= 0:
                if "subsections" not in structure["sections"][current_section_index]:
                    structure["sections"][current_section_index]["subsections"] = []
                
                structure["sections"][current_section_index]["subsections"].append({
                    "title": line[4:].strip(),
                    "content": [],
                    "items": []
                })
                
            # 处理列表项
            elif line.startswith("- ") and current_section_index >= 0:
                # 将列表项添加到当前章节
                structure["sections"][current_section_index]["items"].append(line[2:].strip())
                
            # 处理普通段落
            elif current_section_index >= 0:
                # 将段落添加到当前章节
                structure["sections"][current_section_index]["content"].append(line)
        
        logger.debug(f"基础解析结果: 标题={structure['title']}, 章节数={len(structure['sections'])}")
        return structure
    
    async def _enhance_with_llm(self, markdown_text: str, basic_structure: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用大模型增强Markdown解析结果，添加语义理解和关系分析
        
        Args:
            markdown_text: 原始Markdown文本
            basic_structure: 基础解析结果
            
        Returns:
            增强后的结构化内容
        """
        logger.info(f"使用大模型({self.llm_model})进行内容增强分析")
        
        # 构建提示词
        prompt = ANALYSIS_PROMPT.format(
            markdown_text=markdown_text,
            basic_structure=json.dumps(basic_structure, ensure_ascii=False, indent=2)
        )
        
        try:
            # 调用大模型
            response = await self.model_manager.generate_text(
                model=self.llm_model,
                prompt=prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # 解析JSON响应
            enhanced_structure = self._parse_llm_response(response, basic_structure)
            logger.info("大模型增强分析完成")
            return enhanced_structure
            
        except Exception as e:
            logger.error(f"大模型分析失败: {str(e)}")
            # 如果大模型分析失败，返回基础结构
            return basic_structure
    
    def _parse_llm_response(self, response: str, fallback_structure: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析大模型的响应，提取JSON结构
        
        Args:
            response: 大模型响应
            fallback_structure: 失败时的回退结构
            
        Returns:
            解析后的结构
        """
        # 尝试从响应中提取JSON
        try:
            # 清理响应中的markdown格式代码块
            json_text = response
            if "```json" in response:
                # 提取JSON代码块
                pattern = r"```(?:json)?\s*([\s\S]*?)```"
                matches = re.findall(pattern, response)
                if matches:
                    json_text = matches[0]
            
            # 解析JSON
            enhanced_structure = json.loads(json_text)
            return enhanced_structure
            
        except Exception as e:
            logger.error(f"解析大模型响应失败: {str(e)}")
            return fallback_structure
    
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