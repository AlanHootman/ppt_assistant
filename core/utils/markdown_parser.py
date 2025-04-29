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
            return {"title": "", "subtitle": "", "sections": []}
            
        try:
            structure = self._parse_structure(markdown_text)
            # 在解析完成后，清理所有内容中的Markdown格式
            self._clean_structure_formatting(structure)
            return structure
        except Exception as e:
            logger.error(f"Markdown解析出错: {str(e)}")
            return {"title": "", "subtitle": "", "sections": []}
    
    def _clean_structure_formatting(self, structure: Dict[str, Any]) -> None:
        """
        递归清理结构中所有内容的Markdown格式标记
        
        Args:
            structure: 需要清理的结构
        """
        # 清理标题和副标题
        if "title" in structure:
            structure["title"] = self._clean_markdown_formatting(structure["title"])
        if "subtitle" in structure:
            structure["subtitle"] = self._clean_markdown_formatting(structure["subtitle"])
        
        # 清理各级章节内容
        if "sections" in structure:
            for section in structure["sections"]:
                self._clean_section_formatting(section)
    
    def _clean_section_formatting(self, section: Dict[str, Any]) -> None:
        """
        递归清理章节及其子章节中的Markdown格式
        
        Args:
            section: 需要清理的章节
        """
        # 清理标题
        if "title" in section:
            section["title"] = self._clean_markdown_formatting(section["title"])
        
        # 清理内容
        if "content" in section:
            section["content"] = [self._clean_markdown_formatting(item) for item in section["content"]]
        
        # 清理列表项
        if "items" in section:
            section["items"] = [self._clean_markdown_formatting(item) for item in section["items"]]
        
        # 清理有序列表项
        if "ordered_items" in section:
            section["ordered_items"] = [self._clean_markdown_formatting(item) for item in section["ordered_items"]]
        
        # 清理表格
        if "tables" in section:
            for i, table in enumerate(section["tables"]):
                for j, row in enumerate(table):
                    section["tables"][i][j] = [self._clean_markdown_formatting(cell) for cell in row]
        
        # 清理图片替代文本
        if "images" in section:
            for image in section["images"]:
                if "alt" in image:
                    image["alt"] = self._clean_markdown_formatting(image["alt"])
        
        # 递归清理子章节
        if "subsections" in section:
            for subsection in section["subsections"]:
                self._clean_section_formatting(subsection)
    
    def _clean_markdown_formatting(self, text: str) -> str:
        """
        清理文本中的Markdown格式标记，如加粗(**文字**)、斜体(*文字*)等
        
        Args:
            text: 需要清理的文本
            
        Returns:
            清理后的文本
        """
        if not text or not isinstance(text, str):
            return text
        
        # 通用格式替换函数
        def replace_format(pattern, text, group_idx=1):
            matches = list(re.finditer(pattern, text))
            # 从后向前替换，避免索引错位
            for match in reversed(matches):
                text = text[:match.start()] + match.group(group_idx) + text[match.end():]
            return text
        
        # 删除加粗标记 **文字** 或 __文字__
        text = replace_format(r'\*\*(.*?)\*\*', text)
        text = replace_format(r'__(.*?)__', text)
        
        # 删除斜体标记 *文字* 或 _文字_
        text = replace_format(r'(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)', text)
        text = replace_format(r'(?<!_)_(?!_)(.*?)(?<!_)_(?!_)', text)
        
        # 删除删除线标记 ~~文字~~
        text = replace_format(r'~~(.*?)~~', text)
        
        # 删除行内代码标记 `文字`
        text = replace_format(r'`(.*?)`', text)
        
        # 提取引用中的实际内容 > 文字
        text = replace_format(r'^>\s?(.*?)$', text)
        
        # 移除HTML标签
        text = re.sub(r'<[^>]*>', '', text)
        
        # 清理特殊标记
        # 处理类似 **引导词**：广阔天地 的格式
        text = re.sub(r'\*\*(.*?)\*\*：', r'\1: ', text)
        text = re.sub(r'__(.*?)__：', r'\1: ', text)
        
        # 处理可能的链接 [文字](链接)
        text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
        
        return text
    
    def _parse_structure(self, markdown_text: str) -> Dict[str, Any]:
        """
        解析Markdown文本的基础结构，支持多层级标题结构
        
        Args:
            markdown_text: Markdown文本
            
        Returns:
            结构化内容字典，保留完整的层级关系
        """
        # 初始化结构
        content_structure = {
            "title": "",
            "subtitle": "",
            "sections": []
        }
        
        # 按行分割
        lines = markdown_text.split("\n")
        current_section = None
        current_subsection = None
        current_subsubsection = None
        current_subsubsubsection = None
        in_code_block = False
        current_code_block = ""
        code_block_lang = ""
        
        # 记录是否找到了文档标题
        found_title = False
        found_subtitle = False
        subtitle_line = None
        
        # 逐行解析
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # 处理代码块
            if line_stripped.startswith("```"):
                in_code_block = not in_code_block
                if in_code_block:
                    # 提取代码块语言
                    code_block_lang = line_stripped[3:].strip()
                    current_code_block = ""
                else:
                    # 代码块结束，添加到当前所在的最深层级
                    target_section = self._get_target_section(
                        current_section, current_subsection, 
                        current_subsubsection, current_subsubsubsection
                    )
                    
                    if target_section is not None:
                        if "code_blocks" not in target_section:
                            target_section["code_blocks"] = []
                        
                        target_section["code_blocks"].append({
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
                found_title = True
                logger.debug(f"找到文档标题: '{content_structure['title']}'")
                
                # 检查下一行是否可能是副标题（非标题格式但紧跟标题）
                if i + 1 < len(lines):
                    next_line = lines[i+1].strip()
                    # 如果下一行不是标题格式且不为空，可能是副标题
                    if next_line and not next_line.startswith("#") and not next_line.startswith("```"):
                        subtitle_line = i + 1
                    # 如果下一行是空行，检查下下行是否是可能的副标题
                    elif not next_line and i + 2 < len(lines):
                        next_next_line = lines[i+2].strip()
                        if next_next_line and not next_next_line.startswith("#") and not next_next_line.startswith("```"):
                            subtitle_line = i + 2
            
            # 检查是否为副标题（紧跟在主标题之后的非空行）
            elif i == subtitle_line:
                content_structure["subtitle"] = line_stripped
                found_subtitle = True
                logger.debug(f"找到文档副标题: '{content_structure['subtitle']}'")
            
            # 检测二级标题 (## 标题) - 主要章节
            elif line_stripped.startswith("## "):
                section_title = line_stripped[3:].strip()
                current_section = {
                    "title": section_title,
                    "content": [],
                    "items": [],
                    "level": 2,
                    "type": "content"  # 默认为内容页类型
                }
                # 重置子章节跟踪
                current_subsection = None
                current_subsubsection = None
                current_subsubsubsection = None
                
                # 特殊章节类型识别
                lower_title = section_title.lower()
                if any(keyword in lower_title for keyword in ["介绍", "introduction", "概述", "overview"]) and len(content_structure["sections"]) == 0:
                    current_section["type"] = "opening"
                elif any(keyword in lower_title for keyword in ["总结", "结论", "conclusion", "未来展望", "future work"]):
                    current_section["type"] = "closing"
                
                content_structure["sections"].append(current_section)
            
            # 检测三级标题 (### 标题) - 子章节
            elif line_stripped.startswith("### "):
                subheading_title = line_stripped[4:].strip()
                
                if current_section is not None:
                    if "subsections" not in current_section:
                        current_section["subsections"] = []
                    
                    current_subsection = {
                        "title": subheading_title,
                        "content": [],
                        "items": [],
                        "level": 3
                    }
                    
                    # 重置更深层级的章节跟踪
                    current_subsubsection = None
                    current_subsubsubsection = None
                    
                    current_section["subsections"].append(current_subsection)
            
            # 检测四级标题 (#### 标题) - 子子章节
            elif line_stripped.startswith("#### "):
                subsubheading_title = line_stripped[5:].strip()
                
                if current_subsection is not None:
                    if "subsections" not in current_subsection:
                        current_subsection["subsections"] = []
                    
                    current_subsubsection = {
                        "title": subsubheading_title,
                        "content": [],
                        "items": [],
                        "level": 4
                    }
                    
                    # 重置更深层级的章节跟踪
                    current_subsubsubsection = None
                    
                    current_subsection["subsections"].append(current_subsubsection)
            
            # 检测五级标题 (##### 标题) - 最深层级
            elif line_stripped.startswith("##### "):
                subsubsubheading_title = line_stripped[6:].strip()
                
                if current_subsubsection is not None:
                    if "subsections" not in current_subsubsection:
                        current_subsubsection["subsections"] = []
                    
                    current_subsubsubsection = {
                        "title": subsubsubheading_title,
                        "content": [],
                        "items": [],
                        "level": 5
                    }
                    
                    current_subsubsection["subsections"].append(current_subsubsubsection)
            
            # 检测列表项 (- 或 * 项目)
            elif line_stripped.startswith("- ") or line_stripped.startswith("* "):
                item_text = line_stripped[2:].strip()
                
                # 确定要将列表项添加到哪个层级
                target_section = self._get_target_section(
                    current_section, current_subsection, 
                    current_subsubsection, current_subsubsubsection
                )
                
                if target_section is not None:
                    target_section["items"].append(item_text)
            
            # 检测有序列表项 (1. 项目)
            elif re.match(r"^\d+\.\s", line_stripped):
                item_text = re.sub(r"^\d+\.\s+", "", line_stripped)
                
                # 确定要将有序列表项添加到哪个层级
                target_section = self._get_target_section(
                    current_section, current_subsection, 
                    current_subsubsection, current_subsubsubsection
                )
                
                if target_section is not None:
                    if "ordered_items" not in target_section:
                        target_section["ordered_items"] = []
                    
                    target_section["ordered_items"].append(item_text)
            
            # 检测表格
            elif "|" in line_stripped:
                # 确定要将表格添加到哪个层级
                target_section = self._get_target_section(
                    current_section, current_subsection, 
                    current_subsubsection, current_subsubsubsection
                )
                
                if target_section is not None:
                    if "tables" not in target_section:
                        target_section["tables"] = []
                        target_section["tables"].append([])
                    
                    # 跳过表格分隔行 (|---|---|)
                    if not re.search(r"^[\|\s\-:]+$", line_stripped):
                        target_section["tables"][-1].append(
                            [cell.strip() for cell in line_stripped.split("|") if cell.strip()]
                        )
            
            # 处理图片链接
            elif re.search(r"!\[.*?\]\(.*?\)", line_stripped):
                # 确定要将图片添加到哪个层级
                target_section = self._get_target_section(
                    current_section, current_subsection, 
                    current_subsubsection, current_subsubsubsection
                )
                
                if target_section is not None:
                    if "images" not in target_section:
                        target_section["images"] = []
                    
                    # 提取图片描述和URL
                    match = re.search(r"!\[(.*?)\]\((.*?)\)", line_stripped)
                    if match:
                        alt_text, url = match.groups()
                        target_section["images"].append({
                            "alt": alt_text,
                            "url": url
                        })
            
            # 处理普通段落
            else:
                # 确定要将内容添加到哪个层级
                target_section = self._get_target_section(
                    current_section, current_subsection, 
                    current_subsubsection, current_subsubsubsection
                )
                
                if target_section is not None:
                    target_section["content"].append(line_stripped)
        
        # 日志记录解析结果
        section_count = len(content_structure["sections"])
        
        # 计算所有层级的章节总数
        total_sections = section_count
        for section in content_structure["sections"]:
            if "subsections" in section:
                total_sections += len(section["subsections"])
                for subsection in section["subsections"]:
                    if "subsections" in subsection:
                        total_sections += len(subsection["subsections"])
                        for subsubsection in subsection["subsections"]:
                            if "subsections" in subsubsection:
                                total_sections += len(subsubsection["subsections"])
        
        # 记录解析的标题和副标题信息
        title_status = "成功" if content_structure["title"] else "未找到"
        subtitle_status = "成功" if content_structure["subtitle"] else "未找到"
        
        logger.info(f"Markdown解析完成，标题: '{content_structure.get('title')}' ({title_status}), 副标题: '{content_structure.get('subtitle')}' ({subtitle_status}), 总层级章节数: {total_sections}")
        
        return content_structure
    
    def _get_target_section(self, section, subsection, subsubsection, subsubsubsection):
        """
        根据当前处理状态确定内容应该添加到哪个层级的章节
        
        Args:
            section: 当前主章节
            subsection: 当前子章节
            subsubsection: 当前子子章节
            subsubsubsection: 当前子子子章节
            
        Returns:
            应该添加内容的目标章节
        """
        if subsubsubsection is not None:
            return subsubsubsection
        elif subsubsection is not None:
            return subsubsection
        elif subsection is not None:
            return subsection
        elif section is not None:
            return section
        return None
    
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