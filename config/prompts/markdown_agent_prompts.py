#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Markdown Agent提示词配置
"""

ANALYSIS_PROMPT = """
你是一个专业的PPT内容分析专家。请分析以下Markdown文本，并生成适合PPT制作的结构化JSON。
每个部分除了保留原始内容外，还需添加以下分析信息：
1. "semantic_type": 内容的语义类型，如"concept", "process", "comparison", "list", "timeline", "data", "case_study"等
2. "relation_type": 内容之间的关系类型，如"sequence", "cause_effect", "problem_solution", "hierarchical"等
3. "visualization_suggestion": 建议的可视化方式，如"bullet_points", "flowchart", "diagram", "chart", "table", "image"等
4. "key_points": 提取的关键点列表，以便在PPT中突出显示
5. "summary": 总结性描述，简明扼要表达该部分主旨

Markdown文本:
```
{markdown_text}
```

基础解析结果:
```
{basic_structure}
```

请输出完整的增强JSON结构，确保输出是有效的JSON格式。
只返回JSON数据，不要有其他回复。
"""

SECTION_EXTRACTION_PROMPT = """
从以下Markdown文本中提取主要章节结构，包括：
1. 文档标题（一级标题）
2. 章节标题（二级标题）
3. 每个章节下的内容（包括段落、列表项等）

Markdown文本:
```
{markdown_text}
```

请将结果以JSON格式返回，格式参考：
{
  "title": "文档标题",
  "sections": [
    {
      "title": "章节标题",
      "content": ["段落1", "段落2"],
      "items": ["列表项1", "列表项2"]
    }
  ]
}

只返回JSON数据，不要有其他回复。
""" 