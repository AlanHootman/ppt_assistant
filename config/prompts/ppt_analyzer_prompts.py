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
下面是模板中的几页幻灯片图像，请分析它们的布局和设计特点。
{% endif %}

请以JSON格式返回分析结果，示例格式:
{
  "templateName": "模板名称",
  "style": "整体风格描述",
  "visualFeatures": {
    "colorScheme": "颜色方案描述",
    "designStyle": "设计风格",
    "layoutComplexity": "布局复杂度",
    "textDensity": "文本密度"
  },
  "layouts": [
    {
      "type": "layout类型名称",
      "features": ["特点1", "特点2"],
      "suitableContent": ["适合的内容类型1", "适合的内容类型2"]
    }
  ],
  "recommendations": {
    "textContent": "文本内容适用性描述",
    "dataVisualization": "数据可视化适用性描述",
    "imageContent": "图片内容展示适用性",
    "presentationFlow": "演示流程适用性描述"
  }
}

只返回JSON数据，不要有其他回复。
"""

LAYOUT_COMPATIBILITY_PROMPT = """
给定下列内容类型，请分析其与模板中可用布局的兼容性：

内容类型:
{{ content_types | tojson(indent=2) }}

可用布局:
{{ available_layouts | tojson(indent=2) }}

为每种内容类型推荐最佳的布局选择，并给出匹配度评分（1-10）。
请以JSON格式返回结果，示例:
{
  "recommendations": [
    {
      "contentType": "内容类型1",
      "recommendedLayout": "布局名称",
      "score": 8,
      "reason": "推荐理由"
    }
  ]
}

只返回JSON数据，不要有其他回复。
""" 