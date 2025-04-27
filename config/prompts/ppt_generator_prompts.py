#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PPT生成器Agent提示词配置
"""

CONTENT_FORMATTING_PROMPT = """
根据以下内容和布局信息，生成格式化的PPT内容：

布局决策:
{layout_decision}

请为每张幻灯片生成具体格式化内容，包括：
1. 标题：精简且有吸引力
2. 内容：根据布局类型格式化（项目符号、表格、图表等）
3. 视觉元素：建议添加的图片、图标或图表
4. 注释：演讲者注释

返回JSON格式，示例:
{
  "slides": [
    {
      "type": "布局类型",
      "content": {
        "title": "格式化后的标题",
        "bullets": ["格式化内容1", "格式化内容2"],
        "notes": "演讲者注释"
      },
      "visualElements": ["建议的视觉元素"]
    }
  ]
}

只返回JSON数据，不要有其他回复。
"""

SLIDE_TRANSITION_PROMPT = """
为以下PPT幻灯片序列设计合适的转场效果：

幻灯片序列:
{slides_sequence}

为每个转场位置推荐合适的转场效果，考虑:
1. 内容关联性：相关内容使用相似转场
2. 节奏变化：关键点使用强调性转场
3. 整体一致性：保持风格统一

返回JSON格式，包含每个转场位置的推荐效果和理由。
""" 