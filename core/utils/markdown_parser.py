#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Markdown解析器模块

负责解析Markdown文本的基础结构，提取标题、段落、列表等内容，为上层Agent提供基础解析服务。
"""

import logging
import re
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class MarkdownParser:
    """Markdown解析器，负责解析Markdown文档的基础结构"""
    
    def __init__(self):
        """初始化Markdown解析器"""
        logger.info("初始化Markdown解析器")
    
    def parse(self, markdown_text: str) -> Dict[str, Any]:
        """
        解析Markdown文本，提取结构化内容
        
        Args:
            markdown_text: Markdown文本
            
        Returns:
            解析后的结构化内容
        """
        if not markdown_text:
            logger.warning("Markdown内容为空")
            return {"title": "", "sections": []}
            
        try:
            return self._parse_structure(markdown_text)
        except Exception as e:
            logger.error(f"Markdown解析出错: {str(e)}")
            return {"title": "", "sections": []}
    
    def _parse_structure(self, markdown_text: str) -> Dict[str, Any]:
        """
        解析Markdown文本的基础结构，包括标题、章节、列表项等
        
        Args:
            markdown_text: Markdown文本
            
        Returns:
            结构化内容字典
        """
        # 初始化结构
        content_structure = {
            "title": "",
            "sections": []
        }
        
        # 按行分割
        lines = markdown_text.split("\n")
        current_section = None
        in_code_block = False
        current_code_block = ""
        code_block_lang = ""
        
        # 逐行解析
        for line in lines:
            line_stripped = line.strip()
            
            # 处理代码块
            if line_stripped.startswith("```"):
                in_code_block = not in_code_block
                if in_code_block:
                    # 提取代码块语言
                    code_block_lang = line_stripped[3:].strip()
                    current_code_block = ""
                else:
                    # 代码块结束，添加到当前章节
                    if current_section and "code_blocks" not in current_section:
                        current_section["code_blocks"] = []
                    
                    if current_section:
                        current_section["code_blocks"].append({
                            "language": code_block_lang,
                            "code": current_code_block
                        })
                continue
            
            # 在代码块内，收集代码内容
            if in_code_block:
                current_code_block += line + "\n"
                continue
            
            # 忽略空行
            if not line_stripped:
                continue
                
            # 检测文档标题 (# 标题)
            if line_stripped.startswith("# "):
                content_structure["title"] = line_stripped[2:].strip()
            
            # 检测章节标题 (## 标题)
            elif line_stripped.startswith("## "):
                section_title = line_stripped[3:].strip()
                current_section = {
                    "title": section_title,
                    "content": [],
                    "items": []
                }
                content_structure["sections"].append(current_section)
            
            # 检测子章节标题 (### 标题)
            elif line_stripped.startswith("### "):
                subheading_text = line_stripped[4:].strip()
                if current_section:
                    if "subheadings" not in current_section:
                        current_section["subheadings"] = []
                    
                    current_section["subheadings"].append({
                        "title": subheading_text,
                        "content": []
                    })
            
            # 检测列表项 (- 或 * 项目)
            elif (line_stripped.startswith("- ") or line_stripped.startswith("* ")) and current_section:
                item_text = line_stripped[2:].strip()
                current_section["items"].append(item_text)
            
            # 检测有序列表项 (1. 项目)
            elif re.match(r"^\d+\.\s", line_stripped) and current_section:
                item_text = re.sub(r"^\d+\.\s+", "", line_stripped)
                if "ordered_items" not in current_section:
                    current_section["ordered_items"] = []
                
                current_section["ordered_items"].append(item_text)
            
            # 检测表格
            elif "|" in line_stripped and current_section:
                if "tables" not in current_section:
                    current_section["tables"] = []
                    current_section["tables"].append([])
                
                # 跳过表格分隔行 (|---|---|)
                if not re.search(r"^[\|\s\-:]+$", line_stripped):
                    current_section["tables"][-1].append(
                        [cell.strip() for cell in line_stripped.split("|") if cell.strip()]
                    )
            
            # 处理图片链接
            elif re.search(r"!\[.*?\]\(.*?\)", line_stripped) and current_section:
                if "images" not in current_section:
                    current_section["images"] = []
                
                # 提取图片描述和URL
                match = re.search(r"!\[(.*?)\]\((.*?)\)", line_stripped)
                if match:
                    alt_text, url = match.groups()
                    current_section["images"].append({
                        "alt": alt_text,
                        "url": url
                    })
            
            # 处理普通段落
            elif current_section:
                current_section["content"].append(line_stripped)
        
        # 日志记录解析结果
        section_count = len(content_structure["sections"])
        logger.info(f"Markdown解析完成，标题: {content_structure.get('title')}, 章节数: {section_count}")
        
        return content_structure
    
    def extract_keywords(self, markdown_text: str) -> List[str]:
        """
        从Markdown文本中提取关键词
        
        Args:
            markdown_text: Markdown文本
            
        Returns:
            关键词列表
        """
        # 基础实现，实际项目中可以使用更复杂的算法
        keywords = set()
        
        # 移除代码块
        text_without_code = re.sub(r"```.*?```", "", markdown_text, flags=re.DOTALL)
        
        # 移除Markdown标记
        clean_text = re.sub(r"[#*_\[\]\(\)`]", " ", text_without_code)
        
        # 分词并统计频率
        words = re.findall(r"\b\w+\b", clean_text.lower())
        word_freq = {}
        
        for word in words:
            if len(word) > 3:  # 忽略短词
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # 按频率排序并返回前20个词
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        keywords = [word for word, freq in sorted_words[:20]]
        
        return list(keywords)
    
    def parse_math_formulas(self, markdown_text: str) -> List[Dict[str, str]]:
        """
        解析Markdown中的数学公式
        
        Args:
            markdown_text: Markdown文本
            
        Returns:
            公式列表，每个公式包含类型和内容
        """
        formulas = []
        
        # 匹配行内公式 $...$，但不匹配空白或者单纯的$符号
        inline_pattern = r"(?<!\$)\$([^\$\n]+?)\$(?!\$)"
        inline_formulas = re.findall(inline_pattern, markdown_text)
        for formula in inline_formulas:
            if formula.strip():  # 确保公式不为空
                formulas.append({
                    "type": "inline",
                    "content": formula.strip()
                })
        
        # 匹配块级公式 $$...$$，使用非贪婪模式更精确匹配
        block_pattern = r"\$\$(.*?)\$\$"
        block_formulas = re.findall(block_pattern, markdown_text, re.DOTALL)
        for formula in block_formulas:
            if formula.strip():  # 确保公式不为空
                formulas.append({
                    "type": "block",
                    "content": formula.strip()
                })
        
        return formulas
    
    def parse_images(self, markdown_text: str) -> List[Dict[str, str]]:
        """
        解析Markdown中的图片
        
        Args:
            markdown_text: Markdown文本
            
        Returns:
            图片列表，每个图片包含描述和URL
        """
        images = []
        
        # 匹配图片标记 ![alt](url)
        pattern = r"!\[(.*?)\]\((.*?)\)"
        matches = re.findall(pattern, markdown_text)
        
        for alt, url in matches:
            images.append({
                "alt": alt,
                "url": url
            })
        
        return images
    
    def get_section_by_title(self, content_structure: Dict[str, Any], title: str) -> Optional[Dict[str, Any]]:
        """
        根据标题查找章节
        
        Args:
            content_structure: 解析后的内容结构
            title: 要查找的章节标题
            
        Returns:
            匹配的章节，如果未找到则返回None
        """
        for section in content_structure.get("sections", []):
            if section.get("title") == title:
                return section
        return None 