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

{% if markdown_text %}
Markdown文本:
```
{{ markdown_text }}
```
{% endif %}

{% if basic_structure %}
基础解析结果:
```
{{ basic_structure | tojson(indent=2) }}
```
{% endif %}

【重要要求】：
1. 必须保留原始解析结果中的"title"和"subtitle"字段，它们代表整个文档的标题和副标题
2. 如果原始解析结果中没有标题或副标题，但你在Markdown文本中找到了，请添加到输出中
3. 请确保在增强后的输出中，顶层JSON包含"title"和"subtitle"字段，这对于后续PPT生成至关重要

请输出完整的增强JSON结构，确保输出是有效的JSON格式，并且包含文档标题和副标题。
输出的JSON结构必须包含以下顶级字段：
- "title": 文档的主标题
- "subtitle": 文档的副标题(如有)
- "sections": 包含所有章节的数组

只返回JSON数据，不要有其他回复。
"""