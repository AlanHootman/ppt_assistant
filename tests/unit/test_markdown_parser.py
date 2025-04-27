#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试MarkdownParser类的功能
"""

import pytest
from core.utils.markdown_parser import MarkdownParser

def test_markdown_parser_initialization():
    """测试MarkdownParser的初始化"""
    parser = MarkdownParser()
    assert parser is not None

def test_parse_empty_markdown():
    """测试解析空的Markdown文本"""
    parser = MarkdownParser()
    result = parser.parse("")
    
    assert result is not None
    assert result["title"] == ""
    assert len(result["sections"]) == 0

def test_parse_title_only():
    """测试只解析标题"""
    parser = MarkdownParser()
    markdown_text = "# 测试标题"
    result = parser.parse(markdown_text)
    
    assert result["title"] == "测试标题"
    assert len(result["sections"]) == 0

def test_parse_sections():
    """测试解析章节"""
    parser = MarkdownParser()
    markdown_text = """# 测试文档
    
## 第一章节
这是第一章节的内容。

## 第二章节
这是第二章节的内容。
- 列表项1
- 列表项2
"""
    result = parser.parse(markdown_text)
    
    assert result["title"] == "测试文档"
    assert len(result["sections"]) == 2
    assert result["sections"][0]["title"] == "第一章节"
    assert result["sections"][1]["title"] == "第二章节"
    assert len(result["sections"][1]["items"]) == 2

def test_parse_code_blocks():
    """测试解析代码块"""
    parser = MarkdownParser()
    markdown_text = """# 测试文档
    
## 代码示例
以下是一个Python代码示例：

```python
def hello_world():
    print("Hello, World!")
```
"""
    result = parser.parse(markdown_text)
    
    assert result["title"] == "测试文档"
    assert len(result["sections"]) == 1
    assert "code_blocks" in result["sections"][0]
    assert len(result["sections"][0]["code_blocks"]) == 1
    assert result["sections"][0]["code_blocks"][0]["language"] == "python"

def test_extract_keywords():
    """测试提取关键词"""
    parser = MarkdownParser()
    markdown_text = """# 人工智能与机器学习简介
    
## 什么是人工智能
人工智能是计算机科学的一个分支，旨在开发能够模拟人类智能的机器。

## 机器学习算法
机器学习是人工智能的一个子领域，专注于让系统能够从数据中学习。
常见的算法包括：
- 监督学习
- 无监督学习
- 强化学习
"""
    keywords = parser.extract_keywords(markdown_text)
    
    assert len(keywords) > 0
    # 检查是否包含相关关键词
    all_keywords = " ".join(keywords).lower()
    assert "智能" in all_keywords or "机器" in all_keywords or "学习" in all_keywords

def test_parse_math_formulas():
    """测试解析数学公式"""
    parser = MarkdownParser()
    markdown_text = """# 数学公式示例
    
## 线性代数
行内公式示例: $y = mx + b$

块级公式示例:
$$
\\begin{pmatrix}
a & b \\\\
c & d
\\end{pmatrix}
$$
"""
    formulas = parser.parse_math_formulas(markdown_text)
    
    assert len(formulas) == 2
    assert formulas[0]["type"] == "inline"
    assert formulas[0]["content"] == "y = mx + b"
    assert formulas[1]["type"] == "block"

def test_parse_images():
    """测试解析图片"""
    parser = MarkdownParser()
    markdown_text = """# 图片示例
    
## 示例图片
这是一个图片： ![示例图片](example.jpg)

另一个图片： ![第二张图片](second.png)
"""
    images = parser.parse_images(markdown_text)
    
    assert len(images) == 2
    assert images[0]["alt"] == "示例图片"
    assert images[0]["url"] == "example.jpg"
    assert images[1]["alt"] == "第二张图片"
    assert images[1]["url"] == "second.png"

def test_get_section_by_title():
    """测试通过标题查找章节"""
    parser = MarkdownParser()
    markdown_text = """# 测试文档
    
## 第一章节
这是第一章节的内容。

## 第二章节
这是第二章节的内容。
"""
    result = parser.parse(markdown_text)
    
    section = parser.get_section_by_title(result, "第二章节")
    assert section is not None
    assert section["title"] == "第二章节"
    
    section = parser.get_section_by_title(result, "不存在的章节")
    assert section is None 