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
5. 字体和排版特点

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

返回格式示例:
{
  "templateName": "模板名称",
  "style": "整体风格描述",
  "visualFeatures": {
    "colorScheme": "颜色方案详细描述",
    "designStyle": "设计风格详细描述",
    "layoutComplexity": "布局复杂度评估",
    "textDensity": "文本密度评估"
  },
  "slideLayouts": [
    {
      "slideIndex": 0,
      "type": "封面页/标题页", 
      "purpose": "演示开始页面",
      "structure": {
        "titleLocation": "页面顶部居中",
        "subtitleLocation": "页面中部",
        "logoPosition": "右下角",
        "backgroundFeature": "渐变蓝色背景"
      },
      "elements": [
        {
          "type": "titleText",
          "position": "上部居中",
          "size": "大",
          "fontStyle": "粗体"
        },
        {
          "type": "subtitleText",
          "position": "中部居中",
          "size": "中"
        },
        {
          "type": "logoImage",
          "position": "右下角",
          "size": "小",
          "caption": "公司徽标，蓝色和绿色渐变设计"
        }
      ],
      "suitableContent": ["演示标题", "副标题", "公司名称或标志"],
      "bestPractices": "标题简洁明了，副标题可提供更多上下文"
    },
    {
      "slideIndex": 1,
      "type": "内容页", 
      "purpose": "展示具体内容",
      "structure": "左侧标题，右侧内容区块",
      "elements": [
        {
          "type": "titleText",
          "position": "左侧栏",
          "size": "中"
        },
        {
          "type": "bulletPoints",
          "position": "右侧主区域",
          "size": "占右侧80%空间",
          "bulletCount": 4,
          "bulletSymbol": "绿色圆点",
          "bulletDescription": "每个要点前有明显的绿色圆点符号标识，部分要点内容较长需要换行显示"
        },
        {
          "type": "textBlock",
          "position": "底部",
          "size": "小",
          "paragraphCount": 2,
          "paragraphDescription": "第一段为简短介绍，第二段为详细说明"
        },
        {
          "type": "image",
          "position": "右上角",
          "size": "小",
          "caption": "产品示意图，展示了主要功能界面"
        }
      ],
      "suitableContent": ["关键要点", "产品特性", "服务说明"],
      "bestPractices": "每页限制4-6个要点，保持简洁"
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

请确保为每个幻灯片布局的分析都提供以下详细信息：
1. 幻灯片在原始PPT中的索引(slideIndex)
2. 详细的结构和元素布局描述
3. 项目符号列表的具体数量、使用的符号类型及特点
4. 文本块的段落数量和结构
5. 图片的内容描述(caption)
6. 幻灯片布局分组和汇总信息

只返回JSON数据，不要有其他回复。
"""

