#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Markdown解析器单元测试
"""

import unittest
import os
import sys
from typing import Dict, Any, List

# 添加项目根目录到路径，以便导入模块
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from core.utils.markdown_parser import MarkdownParser

class TestMarkdownParser(unittest.TestCase):
    """Markdown解析器单元测试类"""
    
    def setUp(self):
        """测试前的准备工作"""
        self.parser = MarkdownParser()

    def test_empty_markdown(self):
    """测试解析空的Markdown文本"""
        result = self.parser.parse("")
        self.assertEqual(result, {"title": "", "subtitle": "", "sections": []})

    def test_document_title_and_subtitle(self):
        """测试解析文档标题和副标题"""
        markdown = """# 主标题
副标题

## 第一章节
内容
"""
        result = self.parser.parse(markdown)
        self.assertEqual(result["title"], "主标题")
        self.assertEqual(result["subtitle"], "副标题")

    def test_section_parsing(self):
        """测试章节解析"""
        markdown = """# 文档标题
    
## 第一章节
章节内容

### 子章节1
子章节内容

#### 子子章节
子子章节内容

## 第二章节
另一个章节内容
"""
        result = self.parser.parse(markdown)
        
        # 验证章节数量
        self.assertEqual(len(result["sections"]), 2)
        
        # 验证第一个章节
        first_section = result["sections"][0]
        self.assertEqual(first_section["title"], "第一章节")
        self.assertEqual(first_section["content"], ["章节内容"])
        
        # 验证子章节
        self.assertTrue("subsections" in first_section)
        self.assertEqual(len(first_section["subsections"]), 1)
        self.assertEqual(first_section["subsections"][0]["title"], "子章节1")
        
        # 验证子子章节
        subsection = first_section["subsections"][0]
        self.assertTrue("subsections" in subsection)
        self.assertEqual(len(subsection["subsections"]), 1)
        self.assertEqual(subsection["subsections"][0]["title"], "子子章节")
        
        # 验证第二个章节
        second_section = result["sections"][1]
        self.assertEqual(second_section["title"], "第二章节")
        self.assertEqual(second_section["content"], ["另一个章节内容"])
        
    def test_list_items(self):
        """测试列表项解析"""
        markdown = """## 列表测试
- 项目1
- 项目2
- 项目3

1. 有序项目1
2. 有序项目2
"""
        result = self.parser.parse(markdown)
        section = result["sections"][0]
        
        # 验证无序列表
        self.assertEqual(section["items"], ["项目1", "项目2", "项目3"])
        
        # 验证有序列表
        self.assertEqual(section["ordered_items"], ["有序项目1", "有序项目2"])
        
    def test_code_blocks(self):
        """测试代码块解析"""
        markdown = """## 代码示例

```python
def hello_world():
    print("Hello, World!")
```

一些文字

```javascript
console.log("Hello, World!");
```
"""
        result = self.parser.parse(markdown)
        section = result["sections"][0]
        
        # 验证代码块
        self.assertTrue("code_blocks" in section)
        self.assertEqual(len(section["code_blocks"]), 2)
        
        # 验证第一个代码块
        first_code_block = section["code_blocks"][0]
        self.assertEqual(first_code_block["language"], "python")
        self.assertIn("def hello_world():", first_code_block["code"])
        
        # 验证第二个代码块
        second_code_block = section["code_blocks"][1]
        self.assertEqual(second_code_block["language"], "javascript")
        self.assertIn('console.log("Hello, World!");', second_code_block["code"])
        
    def test_tables(self):
        """测试表格解析"""
        markdown = """## 表格测试

| 标题1 | 标题2 | 标题3 |
| ----- | ----- | ----- |
| 单元格1 | 单元格2 | 单元格3 |
| 单元格4 | 单元格5 | 单元格6 |
"""
        result = self.parser.parse(markdown)
        section = result["sections"][0]
        
        # 验证表格
        self.assertTrue("tables" in section)
        self.assertEqual(len(section["tables"]), 1)  # 一个表格
        
        # 验证表格内容
        table = section["tables"][0]
        self.assertEqual(len(table), 3)  # 三行（包括标题行和两行数据行）
        self.assertEqual(table[0], ["标题1", "标题2", "标题3"])
        self.assertEqual(table[1], ["单元格1", "单元格2", "单元格3"])
        self.assertEqual(table[2], ["单元格4", "单元格5", "单元格6"])
        
    def test_images(self):
        """测试图片解析"""
        markdown = """## 图片测试

![图片描述](https://example.com/image.jpg)

一些文字

![另一张图片](https://example.com/another.png)
"""
        result = self.parser.parse(markdown)
        section = result["sections"][0]
        
        # 验证图片
        self.assertTrue("images" in section)
        self.assertEqual(len(section["images"]), 2)
        
        # 验证第一张图片
        first_image = section["images"][0]
        self.assertEqual(first_image["alt"], "图片描述")
        self.assertEqual(first_image["url"], "https://example.com/image.jpg")
        
        # 验证第二张图片
        second_image = section["images"][1]
        self.assertEqual(second_image["alt"], "另一张图片")
        self.assertEqual(second_image["url"], "https://example.com/another.png")
        
    def test_markdown_formatting_cleaning(self):
        """测试Markdown格式清理"""
        markdown = """## 格式测试

**粗体文字** 和 *斜体文字*

~~删除线~~ 和 `代码`

**引导词**：内容
"""
        result = self.parser.parse(markdown)
        section = result["sections"][0]
        
        # 验证内容中格式被清理
        content = section["content"]
        self.assertIn("粗体文字 和 斜体文字", content)
        self.assertIn("删除线 和 代码", content)
        self.assertIn("引导词: 内容", content)
        
    def test_special_section_types(self):
        """测试特殊章节类型识别"""
        markdown = """# 文档标题

## 介绍
介绍内容

## 主要内容
一些内容

## 结论
结论内容
"""
        result = self.parser.parse(markdown)
        
        # 验证特殊章节类型
        self.assertEqual(result["sections"][0]["type"], "opening")  # 介绍识别为开篇
        self.assertEqual(result["sections"][1]["type"], "content")  # 默认为内容
        self.assertEqual(result["sections"][2]["type"], "closing")  # 结论识别为结束

if __name__ == "__main__":
    unittest.main() 