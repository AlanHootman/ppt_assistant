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
下面是模板中的几页幻灯片图像及其对应的JSON结构，请仔细分析每一页的布局和设计特点。
每张图像都对应模板中的一个幻灯片，图像文件名包含它在原始PPT中的索引信息。
请同时参考图像和对应的JSON结构，进行全面分析。
{% endif %}

{% if image_indices %}
图像索引和对应的幻灯片JSON结构:
{{ image_indices | tojson(indent=2) }}
{% endif %}

{% if slides_json %}
对应的幻灯片JSON结构:
{{ slides_json | tojson(indent=2) }}
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
      "layout_description": "页面上部居中有一个title元素(最多支持20-30个字符)，中部有subtitle元素(支持40-60个字符)，右下角有一个image元素(建议尺寸120x60像素)。整体采用简洁大方的排版，突出标题，背景使用渐变色彩。共有2个text元素，1个image元素。主标题文本容量约20字，副标题文本容量约40字。"
    },
    {
      "slide_index": 1,
      "type": "内容页", 
      "semantic_type": "feature_list",
      "relation_type": "bullet_list",
      "visualization": "bullet_points",
      "layout_description": "左侧有title元素(支持15-20个字符)，右侧主区域(占80%空间)包含带有bullet_points的text元素，有4个项目点，每个项目点支持30-40个字符，每个点前有绿色圆点符号。底部有两个单独的text元素：简短介绍段落(30-40字)和详细说明段落(60-80字)。右上角有一个image元素(建议尺寸200x150像素)。共有3个text元素(1个标题，1个带bullet_points的列表包含4个项目，1个底部说明)，以及1个image元素。"
    },
    {
      "slide_index": 2,
      "type": "过程页", 
      "semantic_type": "process_description",
      "relation_type": "timeline",
      "visualization": "process_diagram",
      "layout_description": "顶部居中有title元素(最多25个字符)，中央区域为由4个group元素组成的流程图，每个group包含一个shape元素(箭头)和两个text元素(步骤标题和描述)。每个group内部结构统一：上部为步骤标题text元素(10-15字)，下部为描述text元素(20-30字)，箭头shape元素连接各个group。整体呈现水平方向的流程走向。共包含9个元素：1个主标题text元素、4个group元素(每个包含2个text元素和1个shape元素)。每个步骤支持标题约10个字，描述约25个字。"
    },
    {
      "slide_index": 3,
      "type": "目录页", 
      "semantic_type": "toc",
      "relation_type": "hierarchy",
      "visualization": "bullet_points",
      "layout_description": "顶部居中有title元素(15-20字符)，主体区域包含多个编号目录项，每个目录项由一个group元素组成，内部包含两个text元素：序号元素(显示如'01'、'02'的编号)和标题元素(25-35字符)。共有1个title元素和5个group元素(每个group包含2个text元素，总共有11个元素)。目录项之间有统一的间距，布局整齐有序。编号使用强调色，目录标题使用主要文本色。整体设计简洁明了，方便快速浏览章节结构。"
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

## PPT元素专业术语(element_type)说明
描述布局时请使用以下专业术语：
1. text - 文本元素，可以是标题、正文、注脚等
2. image - 图片元素
3. shape - 形状元素，如矩形、圆形、箭头等
4. group - 组合元素，由多个子元素组成的集合
5. chart - 图表元素，如柱状图、饼图、折线图等
6. table - 表格元素
7. video - 视频元素
8. audio - 音频元素

## 特殊元素结构说明
1. bullet_points - 带有项目符号的文本列表，通常是text元素的一种特殊形式
2. group元素 - 由多个子元素组成的组合，需说明其内部结构和组织方式
   - 例如："目录项group包含序号text元素和标题text元素，两者水平排列"
   - 例如："流程图由4个step-group组成，每个step-group包含图标shape元素和描述text元素"

## 布局描述(layout_description)说明
请用一段简明扼要但详细的文字描述幻灯片的布局结构，必须包含以下内容：
1. 各元素的位置和大小特征，使用专业元素术语（如"左侧title元素，右侧text元素"）
2. 详细说明各种元素类型及其数量（如"1个title元素，4个带bullet_points的text元素"）
3. 如果有group元素，详细描述其内部结构（如"每个step-group包含1个icon和2个text元素"）
4. 元素之间的组织关系（如"4个相同结构的group水平排列，通过箭头shape连接"）
5. 文本容量估计，明确标出各个文本区域可以容纳的大致字数
6. 对于带bullet_points的text元素，说明可容纳的项目数量
7. 对于image元素，建议的图片尺寸和比例
8. 对于shape元素，说明其用途（如"用于分隔的线条shape"，"表示流程的箭头shape"）
9. 总结整体布局特点和视觉层次结构

请确保为每个幻灯片布局的分析都提供以下详细信息：
1. 幻灯片在原始PPT中的索引(slide_index)
2. 内容语义类型(semantic_type)
3. 内容关系类型(relation_type) 
4. 可视化类型(visualization)
5. 详尽的布局描述(layout_description)，使用专业元素术语描述所有元素类型、数量、位置和容量
6. 幻灯片布局分组和汇总信息

只返回JSON数据，不要有其他回复。
"""

