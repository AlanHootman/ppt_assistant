#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
幻灯片生成Agent提示词配置
"""

SLIDE_GENERATION_PROMPT = """你是一位专业的PPT设计师，需要为以下内容和布局生成格式化的幻灯片内容。

章节内容：
{% if section_json %}
{{ section_json }}
{% endif %}

幻灯片布局：
{% if template_json %}
{{ template_json }}
{% endif %}

请根据章节内容和布局生成完整的幻灯片内容，包括：
1. 精简且有吸引力的标题
2. 根据布局类型格式化的内容（项目符号、段落、表格等）
3. 视觉元素建议
4. 演讲者注释

布局要求：
- 如果是标题页，创建吸引人的标题和简短的副标题
- 如果是内容页，将长文本拆分为简洁的要点
- 如果是双栏布局，平衡分配左右两栏的内容
- 如果是图片布局，提供图片描述和简短的说明文字

注意：
- 我们将使用已有的布局元素，不会修改布局结构，只替换文本内容
- 图片布局只需提供描述，不要生成图片路径，使用"placeholder_image.jpg"作为路径值

请以JSON格式返回你的设计，格式如下：
```json
{
  "title": "幻灯片标题",
  "bullets": ["要点1", "要点2", "要点3"],
  "paragraphs": ["段落1", "段落2"],
  "leftContent": ["左栏内容1", "左栏内容2"],
  "rightContent": ["右栏内容1", "右栏内容2"],
  "imagePath": "placeholder_image.jpg",
  "imageCaption": "图片说明",
  "notes": "演讲者注释"
}
```

只返回JSON数据，不要包含其他解释。"""

LLM_PPT_ELEMENT_MATCHING_PROMPT = """你是专业的PPT生成AI助手，我需要你将特定内容与幻灯片上的元素进行精确匹配，并生成替换操作。

## 幻灯片信息
```json
{{ slide_elements_json }}
```

## 内容信息
```json
{{ content_json }}
```

请仔细分析幻灯片结构和内容，生成一份详细的操作指令，指示如何将内容恰当地放置到幻灯片模板中。
你需要返回JSON格式的操作列表，用于执行具体的修改。

支持的操作类型包括:
1. replace_text - 替换文本内容
2. adjust_font_size - 调整字体大小
3. replace_image - 替换图片(如有)
4. add_image_caption - 添加图片说明

请根据元素类型、位置和内容特点，进行智能匹配。特别注意:
- 标题应放在标题区域(title)
- 项目符号列表应放在内容区域(content/body)
- 内容过长时，考虑拆分或调整字体大小
- 表格内容应保持结构

返回格式示例:
```json
{
  "operations": [
    {
      "element_id": "元素ID",
      "operation": "replace_text", 
      "content": "新的文本内容"
    },
    {
      "element_id": "另一个元素ID",
      "operation": "adjust_font_size",
      "content": 24
    }
  ]
}
```

只返回JSON格式的操作指令，不要包含其他解释。"""

SLIDE_FIX_OPERATIONS_PROMPT = """你是一位PPT修复专家。幻灯片验证过程发现了一些问题，需要你提供修复操作。

## 幻灯片信息
```json
{{ slide_json }}
```

## 原始操作
```json
{{ original_operations }}
```

## 验证问题
```json
{{ issues }}
```

## 修复建议
```json
{{ suggestions }}
```

请提供修复操作指令，指出要修改哪些元素以及如何修改。格式如下：
```json
{
  "operations": [
    {
      "element_id": "元素ID",
      "operation": "replace_text/adjust_font_size/replace_image/add_image_caption",
      "content": "新内容或数值",
      "reason": "修复原因"
    }
  ]
}
```

只返回JSON数据，不要包含其他解释。""" 