#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
布局决策Agent提示词配置
"""

LAYOUT_DECISION_PROMPT = """
基于以下内容结构和PPT模板分析，为每个内容部分选择最合适的布局：

内容结构:
{content_structure}

PPT模板分析:
{template_analysis}

请为每个内容部分选择一个最合适的布局，并解释选择理由。
返回JSON格式，示例:
{
  "slides": [
    {
      "type": "布局类型",
      "content": {
        "title": "幻灯片标题",
        "bullets": ["内容1", "内容2"]
      },
      "reason": "选择此布局的理由"
    }
  ],
  "template": "模板名称"
}

只返回JSON数据，不要有其他回复。
"""

SLIDE_OPTIMIZATION_PROMPT = """
针对以下幻灯片布局方案，请提供优化建议：

当前布局方案:
{current_layout}

请从以下角度进行优化:
1. 内容均衡性：幻灯片内容是否分布均匀
2. 视觉层次：重要内容是否突出显示
3. 信息密度：单张幻灯片信息是否过多或过少
4. 一致性：布局风格是否统一
5. 叙事流畅度：内容叙述是否连贯

返回优化后的布局方案，保持JSON格式，并说明每处优化的理由。
""" 