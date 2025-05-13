#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PPT分析器Agent提示词配置
"""

TEMPLATE_ANALYSIS_PROMPT = """
分析以下PPT模板的布局和设计特点。请识别：
1. 模板名称和整体风格
2. 可用的布局类型及其特点
3. 每种布局适合的内容类型
4. 设计元素和颜色方案

{% if template_info %}
模板信息:
{{ template_info | tojson(indent=2) }}
{% endif %}

{% if has_images %}
下面是模板中的几页幻灯片图像，请仔细分析每一页的布局和设计特点。
每张图像都对应模板中的一个幻灯片，图像文件名包含它在原始PPT中的索引信息。
请特别注意分析每页幻灯片中的文本段落数量、项目符号列表项数量，以及图片的具体内容。
{% endif %}

{% if image_indices %}
图像索引信息:
{{ image_indices | tojson(indent=2) }}
{% endif %}

请按以下要求详细分析并以JSON格式返回分析结果:

1. 明确识别每一页幻灯片的类型和用途(如封面页、目录页、章节页、内容页、结束页等)
2. 对每一页幻灯片进行详细分析，包括布局结构、元素分布和设计特点
3. 具体指出每个布局中文本框、图片框、表格区域的位置和大小特征
4. 分析每种布局适合展示的内容类型和信息量
5. 提供使用建议，包括如何最佳利用每种布局
6. 对文本内容进行细致分析：
   - 对于项目符号列表(bulletPoints)，请通过识别每个项目点前面的符号(如圆点、方块、数字、三角形等)精确计数，不要依赖换行判断。即使一个项目点因内容较长而换行，也应视为一个项目点
   - 对于文本块(textBlock)，请分析有几个段落及其结构特点
7. 对于图片元素，请添加图片内容描述(caption)，详细说明图片中展示的内容
8. 提供幻灯片布局分组和汇总，说明哪几页使用类似布局，哪页是开篇/结束页
9. 对每个幻灯片分析其内容语义类型、关系类型和可视化类型

返回格式示例:
{
  "templateName": "模板名称",
  "style": "整体风格描述",
  "slideLayouts": [
    {
      "slide_index": 0,
      "type": "封面页/标题页", 
      "semantic_type": "introduction",
      "relation_type": "none",
      "visualization": "text_only",
      "layout_description": "页面上部居中有标题文本区域，中部有副标题文本区域，右下角有徽标图片位置。整体采用简洁大方的排版，突出标题，背景使用渐变色彩。"
    },
    {
      "slide_index": 1,
      "type": "内容页", 
      "semantic_type": "feature_list",
      "relation_type": "bullet_list",
      "visualization": "bullet_points",
      "layout_description": "左侧有标题区域，右侧主区域（占80%空间）包含项目符号列表，有4个项目点，每个点前有绿色圆点符号。底部有两段文本：简短介绍段落和详细说明段落。右上角有一个产品示意图，展示了主要功能界面。"
    },
    {
      "slide_index": 2,
      "type": "过程页", 
      "semantic_type": "process_description",
      "relation_type": "timeline",
      "visualization": "process_diagram",
      "layout_description": "顶部居中有标题文本区域，中央区域为四步流程图，四个连续箭头连接的流程步骤，每个步骤有标题和简要描述。整体呈现水平方向的流程走向，使用箭头清晰指示流程方向。"
    },
    {
      "slide_index": 3,
      "type": "对比页", 
      "semantic_type": "comparison",
      "relation_type": "compare_contrast",
      "visualization": "side_by_side",
      "layout_description": "顶部居中有标题文本区域，中央区域是一个3行2列的对比表格，左侧为'优点'，右侧为'局限性'。两侧内容量保持平衡，使用颜色区分两列，表格线条简洁。"
    }
  ],
  "layoutGroups": [
    {
      "groupName": "标题页组",
      "slideIndices": [0],
      "commonFeatures": "醒目标题，副标题位置，品牌元素"
    },
    {
      "groupName": "图文混排内容页组",
      "slideIndices": [2, 3, 4, 5],
      "commonFeatures": "顶部图片，底部文字说明"
    },
    {
      "groupName": "项目符号内容页组",
      "slideIndices": [1, 6, 7],
      "commonFeatures": "左侧标题，项目符号列表"
    },
    {
      "groupName": "结束页组",
      "slideIndices": [8],
      "commonFeatures": "感谢信息，联系方式"
    }
  ],
  "slideSummary": {
    "openingSlides": [0],
    "contentSlides": [1, 2, 3, 4, 5, 6, 7],
    "closingSlides": [8],
    "presentationFlow": "从产品概述开始，展示设计特点，然后介绍功能和特性，最后以联系信息结束"
  },
  "recommendations": {
    "textContent": "文本内容适用性描述，包括字数限制和格式建议",
    "dataVisualization": "数据可视化适用性详细描述，适合哪些类型的图表",
    "imageContent": "图片内容展示适用性详述，哪些页面适合大图片",
    "presentationFlow": "演示流程建议，如何组织各种布局的幻灯片形成流畅叙事"
  }
}

## 内容语义类型(semantic_type)说明
请为每个幻灯片布局分配适当的语义类型，常见类型包括：
1. introduction - 介绍性内容，如标题页、简介页
2. toc - 目录页
3. section_header - 章节标题页
4. bullet_list - 要点列表
5. process_description - 过程或步骤描述
6. data_presentation - 数据展示
7. comparison - 对比内容
8. feature_list - 特性列表
9. summary - 总结内容
10. conclusion - 结论
11. thank_you - 感谢/结束页

## 内容关系类型(relation_type)说明
请分析幻灯片内容元素之间的关系类型，常见类型包括：
1. none - 无特定关系
2. sequence - 顺序关系
3. timeline - 时间线/时序关系
4. hierarchy - 层级关系
5. bullet_list - 并列列表关系
6. compare_contrast - 对比关系
7. cause_effect - 因果关系
8. problem_solution - 问题解决关系
9. spatial - 空间关系

## 可视化类型(visualization)说明
请指明幻灯片主要使用的可视化方式，常见类型包括：
1. text_only - 纯文本
2. bullet_points - 项目符号列表
3. image_with_text - 图文结合
4. chart - 图表(请具体说明是柱状图、饼图等)
5. diagram - 图解
6. table - 表格
7. process_diagram - 流程图
8. timeline - 时间线图
9. side_by_side - 并排对比
10. grid_layout - 网格布局
11. icon_based - 基于图标的可视化

## 布局描述(layout_description)说明
请用一段简明扼要的文字描述幻灯片的布局结构，包含以下内容：
1. 各元素的位置和大小特征（如"左侧标题区，右侧内容区"）
2. 文本区域的数量和用途（如"顶部标题，底部3段文本"）
3. 项目符号列表的数量和特点（如"右侧5个带圆点的项目符号"）
4. 图片区域的位置和内容描述（如"右下角产品图片"）
5. 整体布局风格（如"对称布局"、"不对称布局"）

请确保为每个幻灯片布局的分析都提供以下详细信息：
1. 幻灯片在原始PPT中的索引(slide_index)
2. 内容语义类型(semantic_type)
3. 内容关系类型(relation_type) 
4. 可视化类型(visualization)
5. 布局描述(layout_description)
6. 幻灯片布局分组和汇总信息

只返回JSON数据，不要有其他回复。
"""

