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

SECTION_EXTRACTION_PROMPT = """
从以下Markdown文本中提取完整的多层级章节结构，包括：
1. 文档标题（一级标题 #）
2. 文档副标题（可能在标题下方的普通文本）
3. 主章节（二级标题 ##）
4. 子章节（三级标题 ###）
5. 子子章节（四级标题 ####）
6. 更深层级（五级标题 #####）

对于每个章节和子章节，请提取：
- 标题内容
- 正文段落
- 列表项（有序和无序）
- 代码块（保留语言信息）
- 表格内容
- 图片引用

{% if markdown_text %}
Markdown文本:
```
{{ markdown_text }}
```
{% endif %}

请将结果以JSON格式返回，格式参考：
{
  "title": "文档标题",
  "subtitle": "文档副标题（如有）",
  "sections": [
    {
      "title": "主章节标题",
      "level": 2,
      "content": ["段落1", "段落2"],
      "items": ["列表项1", "列表项2"],
      "code_blocks": [{"language": "python", "code": "代码内容"}],
      "tables": [[["表头1", "表头2"], ["内容1", "内容2"]]],
      "images": [{"alt": "图片描述", "url": "图片链接"}],
      "subsections": [
        {
          "title": "子章节标题",
          "level": 3,
          "content": ["子章节段落"],
          "items": ["子章节列表项"],
          "subsections": [
            {
              "title": "子子章节标题",
              "level": 4,
              "content": ["更深层级内容"],
              "subsections": []
            }
          ]
        }
      ]
    }
  ]
}

请确保正确保留多层级结构的关系，每个层级都应该有适当的嵌套。只返回JSON数据，不要有其他回复。
""" 