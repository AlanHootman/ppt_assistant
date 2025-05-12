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
        
        # 确保中文冒号被转换为英文冒号
        text = text.replace('：', ': ')
        
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
        
        # 初始化解析状态
        parsing_state = {
            "current_section": None,
            "current_subsection": None,
            "current_subsubsection": None,
            "current_subsubsubsection": None,
            "in_code_block": False,
            "current_code_block": "",
            "code_block_lang": "",
            "found_title": False,
            "found_subtitle": False,
            "subtitle_line": None,
        }
        
        # 逐行解析
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # 跳过空行
            if not line_stripped:
                continue
                
            # 处理代码块
            if self._handle_code_block(line_stripped, parsing_state, content_structure):
                continue
            
            # 如果在代码块内，继续收集代码内容
            if parsing_state["in_code_block"]:
                parsing_state["current_code_block"] += line + "\n"
                continue
            
            # 处理文档标题和副标题
            if self._handle_document_title(i, line_stripped, lines, parsing_state, content_structure):
                continue
                
            # 处理副标题
            if i == parsing_state["subtitle_line"]:
                content_structure["subtitle"] = line_stripped
                parsing_state["found_subtitle"] = True
                logger.debug(f"找到文档副标题: '{content_structure['subtitle']}'")
                continue
            
            # 处理各级标题
            if self._handle_headings(line_stripped, parsing_state, content_structure):
                continue
                
            # 处理列表项、表格、图片和普通段落
            self._handle_content_elements(line_stripped, parsing_state)
        
        # 日志记录解析结果
        self._log_parsing_results(content_structure)
        
        return content_structure
    
    def _handle_code_block(self, line_stripped: str, parsing_state: Dict[str, Any], content_structure: Dict[str, Any]) -> bool:
        """
        处理代码块的开始和结束
        
        Args:
            line_stripped: 当前处理的行（已去除前后空白）
            parsing_state: 当前解析状态
            content_structure: 内容结构
            
        Returns:
            是否处理了代码块标记
        """
        if not line_stripped.startswith("```"):
            return False
            
        parsing_state["in_code_block"] = not parsing_state["in_code_block"]
        
        if parsing_state["in_code_block"]:
            # 提取代码块语言
            parsing_state["code_block_lang"] = line_stripped[3:].strip()
            parsing_state["current_code_block"] = ""
        else:
            # 代码块结束，添加到当前所在的最深层级
            target_section = self._get_target_section(
                parsing_state["current_section"], 
                parsing_state["current_subsection"], 
                parsing_state["current_subsubsection"], 
                parsing_state["current_subsubsubsection"]
            )
            
            if target_section is not None:
                if "code_blocks" not in target_section:
                    target_section["code_blocks"] = []
                
                target_section["code_blocks"].append({
                    "language": parsing_state["code_block_lang"],
                    "code": parsing_state["current_code_block"]
                })
        
        return True
    
    def _handle_document_title(self, line_index: int, line_stripped: str, lines: List[str], 
                             parsing_state: Dict[str, Any], content_structure: Dict[str, Any]) -> bool:
        """
        处理文档标题和检测可能的副标题
        
        Args:
            line_index: 当前行索引
            line_stripped: 当前处理的行（已去除前后空白）
            lines: 所有行
            parsing_state: 当前解析状态
            content_structure: 内容结构
            
        Returns:
            是否处理了文档标题
        """
        if not line_stripped.startswith("# "):
            return False
            
        content_structure["title"] = line_stripped[2:].strip()
        parsing_state["found_title"] = True
        logger.debug(f"找到文档标题: '{content_structure['title']}'")
        
        # 检查下一行是否可能是副标题（非标题格式但紧跟标题）
        self._detect_possible_subtitle(line_index, lines, parsing_state)
        
        return True
    
    def _detect_possible_subtitle(self, line_index: int, lines: List[str], parsing_state: Dict[str, Any]) -> None:
        """
        检测可能的副标题
        
        Args:
            line_index: 当前行索引
            lines: 所有行
            parsing_state: 当前解析状态
        """
        if line_index + 1 < len(lines):
            next_line = lines[line_index+1].strip()
            # 如果下一行不是标题格式且不为空，可能是副标题
            if next_line and not next_line.startswith("#") and not next_line.startswith("```"):
                parsing_state["subtitle_line"] = line_index + 1
            # 如果下一行是空行，检查下下行是否是可能的副标题
            elif not next_line and line_index + 2 < len(lines):
                next_next_line = lines[line_index+2].strip()
                if next_next_line and not next_next_line.startswith("#") and not next_next_line.startswith("```"):
                    parsing_state["subtitle_line"] = line_index + 2
    
    def _handle_headings(self, line_stripped: str, parsing_state: Dict[str, Any], 
                        content_structure: Dict[str, Any]) -> bool:
        """
        处理各级标题（二级到五级）
        
        Args:
            line_stripped: 当前处理的行（已去除前后空白）
            parsing_state: 当前解析状态
            content_structure: 内容结构
            
        Returns:
            是否处理了标题
        """
        # 处理二级标题
        if line_stripped.startswith("## "):
            self._handle_section_heading(line_stripped, parsing_state, content_structure)
            return True
            
        # 处理三级标题
        if line_stripped.startswith("### "):
            self._handle_subsection_heading(line_stripped, parsing_state)
            return True
            
        # 处理四级标题
        if line_stripped.startswith("#### "):
            self._handle_subsubsection_heading(line_stripped, parsing_state)
            return True
            
        # 处理五级标题
        if line_stripped.startswith("##### "):
            self._handle_subsubsubsection_heading(line_stripped, parsing_state)
            return True
            
        return False
    
    def _handle_section_heading(self, line_stripped: str, parsing_state: Dict[str, Any], 
                             content_structure: Dict[str, Any]) -> None:
        """
        处理二级标题（主章节）
        
        Args:
            line_stripped: 当前处理的行（已去除前后空白）
            parsing_state: 当前解析状态
            content_structure: 内容结构
        """
        section_title = line_stripped[3:].strip()
        parsing_state["current_section"] = {
            "title": section_title,
            "content": [],
            "items": [],
            "level": 2,
            "type": "content"  # 默认为内容页类型
        }
        
        # 重置子章节跟踪
        parsing_state["current_subsection"] = None
        parsing_state["current_subsubsection"] = None
        parsing_state["current_subsubsubsection"] = None
        
        # 特殊章节类型识别
        self._identify_special_section_type(section_title, parsing_state, content_structure)
        
        content_structure["sections"].append(parsing_state["current_section"])
    
    def _identify_special_section_type(self, section_title: str, parsing_state: Dict[str, Any], 
                                    content_structure: Dict[str, Any]) -> None:
        """
        识别特殊章节类型
        
        Args:
            section_title: 章节标题
            parsing_state: 当前解析状态
            content_structure: 内容结构
        """
        lower_title = section_title.lower()
        
        # 识别开篇章节
        if any(keyword in lower_title for keyword in ["介绍", "introduction", "概述", "overview"]) and len(content_structure["sections"]) == 0:
            parsing_state["current_section"]["type"] = "opening"
            
        # 识别结束章节
        elif any(keyword in lower_title for keyword in ["总结", "结论", "conclusion", "未来展望", "future work"]):
            parsing_state["current_section"]["type"] = "closing"
    
    def _handle_subsection_heading(self, line_stripped: str, parsing_state: Dict[str, Any]) -> None:
        """
        处理三级标题（子章节）
        
        Args:
            line_stripped: 当前处理的行（已去除前后空白）
            parsing_state: 当前解析状态
        """
        subheading_title = line_stripped[4:].strip()
        
        if parsing_state["current_section"] is not None:
            if "subsections" not in parsing_state["current_section"]:
                parsing_state["current_section"]["subsections"] = []
            
            parsing_state["current_subsection"] = {
                "title": subheading_title,
                "content": [],
                "items": [],
                "level": 3
            }
            
            # 重置更深层级的章节跟踪
            parsing_state["current_subsubsection"] = None
            parsing_state["current_subsubsubsection"] = None
            
            parsing_state["current_section"]["subsections"].append(parsing_state["current_subsection"])
    
    def _handle_subsubsection_heading(self, line_stripped: str, parsing_state: Dict[str, Any]) -> None:
        """
        处理四级标题（子子章节）
        
        Args:
            line_stripped: 当前处理的行（已去除前后空白）
            parsing_state: 当前解析状态
        """
        subsubheading_title = line_stripped[5:].strip()
        
        if parsing_state["current_subsection"] is not None:
            if "subsections" not in parsing_state["current_subsection"]:
                parsing_state["current_subsection"]["subsections"] = []
            
            parsing_state["current_subsubsection"] = {
                "title": subsubheading_title,
                "content": [],
                "items": [],
                "level": 4
            }
            
            # 重置更深层级的章节跟踪
            parsing_state["current_subsubsubsection"] = None
            
            parsing_state["current_subsection"]["subsections"].append(parsing_state["current_subsubsection"])
    
    def _handle_subsubsubsection_heading(self, line_stripped: str, parsing_state: Dict[str, Any]) -> None:
        """
        处理五级标题（子子子章节）
        
        Args:
            line_stripped: 当前处理的行（已去除前后空白）
            parsing_state: 当前解析状态
        """
        subsubsubheading_title = line_stripped[6:].strip()
        
        if parsing_state["current_subsubsection"] is not None:
            if "subsections" not in parsing_state["current_subsubsection"]:
                parsing_state["current_subsubsection"]["subsections"] = []
            
            parsing_state["current_subsubsubsection"] = {
                "title": subsubsubheading_title,
                "content": [],
                "items": [],
                "level": 5
            }
            
            parsing_state["current_subsubsection"]["subsections"].append(parsing_state["current_subsubsubsection"])
    
    def _handle_content_elements(self, line_stripped: str, parsing_state: Dict[str, Any]) -> None:
        """
        处理内容元素（列表项、表格、图片和普通段落）
        
        Args:
            line_stripped: 当前处理的行（已去除前后空白）
            parsing_state: 当前解析状态
        """
        # 获取当前应添加内容的目标章节
        target_section = self._get_target_section(
            parsing_state["current_section"], 
            parsing_state["current_subsection"], 
            parsing_state["current_subsubsection"], 
            parsing_state["current_subsubsubsection"]
        )
        
        if target_section is None:
            return
            
        # 检测加粗文本标题格式（如"**问题引导**："或"**学习任务**："）
        bold_title_match = re.match(r"^\*\*(.*?)\*\*\s*[:：]", line_stripped)
        if bold_title_match or line_stripped.startswith("**") and (":" in line_stripped or "：" in line_stripped):
            # 提取标题部分
            if bold_title_match:
                subtitle = bold_title_match.group(1).strip()
            else:
                # 处理其他可能的加粗标题格式
                subtitle_parts = re.split(r"[:：]", line_stripped.replace("**", ""), 1)
                subtitle = subtitle_parts[0].strip()
            
            # 创建新的子部分
            new_subsection = {
                "title": subtitle,
                "content": [],
                "items": [],
                "level": target_section.get("level", 3) + 1  # 设置为当前部分的下一级
            }
            
            # 获取冒号后的剩余内容（如果有）
            remaining_content = re.sub(r"^\*\*(.*?)\*\*\s*[:：]\s*", "", line_stripped).strip()
            if remaining_content:
                new_subsection["content"].append(remaining_content)
            
            # 将新子部分添加到当前部分
            if "subsections" not in target_section:
                target_section["subsections"] = []
            
            target_section["subsections"].append(new_subsection)
            
            # 更新解析状态以跟踪新创建的子部分
            # 根据当前部分的层级决定更新哪个状态变量
            if target_section == parsing_state["current_section"]:
                parsing_state["current_subsection"] = new_subsection
                parsing_state["current_subsubsection"] = None
                parsing_state["current_subsubsubsection"] = None
            elif target_section == parsing_state["current_subsection"]:
                parsing_state["current_subsubsection"] = new_subsection
                parsing_state["current_subsubsubsection"] = None
            elif target_section == parsing_state["current_subsubsection"]:
                parsing_state["current_subsubsubsection"] = new_subsection
            
            return
        
        # 检测列表项 (- 或 * 项目)
        if line_stripped.startswith("- ") or line_stripped.startswith("* "):
            item_text = line_stripped[2:].strip()
            target_section["items"].append(item_text)
            
        # 检测有序列表项 (1. 项目)
        elif re.match(r"^\d+\.\s", line_stripped):
            item_text = re.sub(r"^\d+\.\s+", "", line_stripped)
            if "ordered_items" not in target_section:
                target_section["ordered_items"] = []
            target_section["ordered_items"].append(item_text)
            
        # 检测表格
        elif "|" in line_stripped:
            self._handle_table(line_stripped, target_section)
            
        # 处理图片链接
        elif re.search(r"!\[.*?\]\(.*?\)", line_stripped):
            self._handle_image(line_stripped, target_section)
            
        # 处理普通段落
        else:
            target_section["content"].append(line_stripped)
    
    def _handle_table(self, line_stripped: str, target_section: Dict[str, Any]) -> None:
        """
        处理表格行
        
        Args:
            line_stripped: 当前处理的行（已去除前后空白）
            target_section: 目标章节
        """
        if "tables" not in target_section:
            target_section["tables"] = []
            target_section["tables"].append([])
        
        # 跳过表格分隔行 (|---|---|)
        if re.search(r"^[\|\s\-:]+$", line_stripped):
            return
            
        target_section["tables"][-1].append(
            [cell.strip() for cell in line_stripped.split("|") if cell.strip()]
        )
    
    def _handle_image(self, line_stripped: str, target_section: Dict[str, Any]) -> None:
        """
        处理图片链接
        
        Args:
            line_stripped: 当前处理的行（已去除前后空白）
            target_section: 目标章节
        """
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
    
    def _count_total_sections(self, content_structure: Dict[str, Any]) -> int:
        """
        递归计算所有层级的章节总数
        
        Args:
            content_structure: 内容结构
            
        Returns:
            章节总数
        """
        total = len(content_structure["sections"])
        
        # 使用辅助函数递归计算子章节数
        def count_subsections(sections):
            count = 0
            for section in sections:
                if "subsections" in section:
                    count += len(section["subsections"])
                    count += count_subsections(section["subsections"])
            return count
        
        total += count_subsections(content_structure["sections"])
        return total
    
    def _log_parsing_results(self, content_structure: Dict[str, Any]) -> None:
        """
        记录解析结果的日志
        
        Args:
            content_structure: 内容结构
        """
        # 计算所有层级的章节总数
        total_sections = self._count_total_sections(content_structure)
        
        # 记录解析的标题和副标题信息
        title_status = "成功" if content_structure["title"] else "未找到"
        subtitle_status = "成功" if content_structure["subtitle"] else "未找到"
        
        logger.info(f"Markdown解析完成，标题: '{content_structure.get('title')}' ({title_status}), 副标题: '{content_structure.get('subtitle')}' ({subtitle_status}), 总层级章节数: {total_sections}")
    
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