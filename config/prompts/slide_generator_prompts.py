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

PPT系统支持的操作类型包括:
1. update_element_content - 替换文本内容
   - 参数:
     - element_id: 要更新的元素ID
     - content: 新的文本内容(字符串)

2. adjust_text_font_size - 调整字体大小
   - 参数:
     - element_id: 要调整字体的元素ID
     - content: 新的字体大小(整数，单位为磅pt)

3. adjust_element_position - 调整元素位置和大小
   - 参数:
     - element_id: 要调整的元素ID
     - content: 包含以下可选字段的对象:
       - left: 左侧位置(数值，单位为磅pt)
       - top: 顶部位置(数值，单位为磅pt)
       - width: 宽度(数值，单位为磅pt)
       - height: 高度(数值，单位为磅pt)
       

请根据元素类型、位置和内容特点，进行智能匹配。特别注意:
- 标题应放在标题区域(title)
- 项目符号列表应放在内容区域(content/body)
- 内容过长时，考虑拆分或调整字体大小
- 表格内容应保持结构
- 图片替换需要确保新图片路径有效

返回格式示例:
```json
{
  "operations": [
    {
      "element_id": "title_1",
      "operation": "update_element_content", 
      "content": "项目进展报告"
    },
    {
      "element_id": "content_1",
      "operation": "update_element_content",
      "content": "• 第一阶段已完成\n• 第二阶段正在进行\n• 第三阶段计划下月启动"
    },
    {
      "element_id": "title_2",
      "operation": "adjust_text_font_size",
      "content": 24
    },
    {
      "element_id": "chart_1",
      "operation": "adjust_element_position",
      "content": {
        "left": 100,
        "top": 200,
        "width": 400,
        "height": 300
      }
    }
  ]
}
```

请确保所有操作的参数都符合要求，并且元素ID必须与幻灯片元素中的ID匹配。只返回JSON格式的操作指令，不要包含其他解释。"""


SLIDE_SELF_VALIDATION_PROMPT = """你是一位专业PPT质量检查与修改专家。请分析提供的幻灯片截图，并评估其质量与内容。

## 章节内容信息
```json
{{ section_json }}
```

## 幻灯片元素信息
```json
{{ slide_elements_json }}
```

请仔细分析幻灯片，重点检查以下方面:
1. 文本溢出或截断：文本是否超出了文本框边界
2. 布局平衡：元素分布是否合理，整体布局是否平衡
3. 可读性：字体大小是否适合，文本是否清晰可读
4. 颜色对比度：文本与背景的对比度是否足够
5. 内容密度：幻灯片内容是否过于拥挤
6. 视觉吸引力：整体设计是否美观，吸引人
7. 内容与章节主题的匹配度：内容是否符合当前章节的主题
8. 图片与文本的协调性：图片是否与相关文本内容协调(如果有图片)
9. 模板残留内容：是否存在模板中的占位文本或多余元素

清理模板残留元素的指导原则:
- 删除包含"点击添加文本"、"点击编辑"等模板指导文本的元素
- 删除重复内容或已被新内容替代但仍然保留的旧元素
- 删除多余的未使用的项目符号点或列表标记
- 删除不包含实际内容的空文本框
- 删除与整体内容不相关的模板示例文本
- 注意：请勿删除背景、品牌元素、装饰图形等不影响内容展示的视觉元素

请以JSON格式回答，包含以下字段：
1. has_issues: 布尔值，表示是否存在问题
2. issues: 问题列表
3. suggestions: 改进建议列表(如果有问题)
4. operations: 具体修改操作列表，每个操作包含以下字段：
   - element_id: 需要修改的元素ID
   - operation: 操作类型，可以是:
     - update_element_content: 更新文本内容
     - adjust_text_font_size: 调整字体大小
     - adjust_element_position: 调整元素位置和大小
     - delete_element: 删除元素
   - content: 根据操作类型提供相应的内容或参数值
   - reason: 修改原因
5. quality_score: 1-10分的质量评分

操作参数要求:
- update_element_content: content应为字符串
- adjust_text_font_size: content应为整数
- adjust_element_position: content应为包含left/top/width/height的对象
- delete_element: 不需要content参数，直接设置操作类型为delete_element即可

关于delete_element:
- 此操作用于删除PPT模板中的残留元素或不必要的元素
- 只删除文本类元素或影响版面的多余元素组
- 不应删除背景图、装饰图形、品牌元素等视觉设计元素
- 删除前应确认该元素确实是模板残留或与当前内容无关
- 建议同时提供删除理由，说明为什么该元素应被删除

输出示例:
```json
{
  "has_issues": true,
  "issues": ["存在模板占位文本", "文本在右下角溢出", "标题与内容颜色对比度不足"],
  "suggestions": ["删除模板占位符", "缩短右下角文本或减小字号", "将标题颜色加深以增加对比度"],
  "operations": [
    {
      "element_id": "text_box_3",
      "operation": "update_element_content",
      "content": "简化后的内容",
      "reason": "原文本过长导致溢出"
    },
    {
      "element_id": "title_1",
      "operation": "adjust_text_font_size",
      "content": 28,
      "reason": "增大字号提高可读性"
    },
    {
      "element_id": "chart_1",
      "operation": "adjust_element_position",
      "content": {
        "width": 450,
        "height": 320
      },
      "reason": "扩大图表尺寸提高可读性"
    },
    {
      "element_id": "placeholder_text_1",
      "operation": "delete_element",
      "reason": "删除包含'点击添加标题'的模板占位符"
    },
    {
      "element_id": "empty_bullet_point_3",
      "operation": "delete_element",
      "reason": "删除多余的未使用项目符号点"
    }
  ],
  "quality_score": 6
}
```

请仅返回JSON格式结果，不要包含其他解释。""" 