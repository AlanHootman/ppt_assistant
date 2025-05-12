#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Markdown Agent提示词配置
"""

ANALYSIS_PROMPT = """
你是一个专业的PPT内容分析专家。请直接分析以下Markdown文本，生成适合PPT制作的完整结构化JSON，无需依赖任何已有的基础解析结果。
每个部分都需添加以下分析信息：
1. "semantic_type": 内容的语义类型，如"concept", "process", "comparison", "list", "timeline", "data", "case_study"等
2. "relation_type": 内容之间的关系类型，如"sequence", "cause_effect", "problem_solution", "hierarchical"等
3. "visualization_suggestion": 建议的可视化方式，如"bullet_points", "flowchart", "diagram", "chart", "table", "image"等

{% if markdown_text %}
Markdown文本:
```
{{ markdown_text }}
```
{% endif %}

【重要结构解析规则】：
1. 识别并提取文档的标题和副标题
2. 识别标题层级结构(# ## ### #### #####)，构建章节、子章节的嵌套关系
3. 识别并保留带有标识符的子部分（如"问题引导:"、"学习任务:"）
4. 当遇到冒号后跟列表项的格式，应将其视为独立的子部分，而非简单的内容项
5. 正确区分并列的子部分，例如"问题引导"和"学习任务"应被解析为同级的独立subsection
6. 正确处理**加粗文本**格式，识别加粗后带冒号的文本(如"**问题引导**：")作为子标题
7. 将所有内容（包括无序列表和有序列表）都放在content数组中，保持原文的顺序和层次关系
8. 识别并跳过分隔线(---, ***, ___)，不要将它们解析为内容
9. 为每一层级的内容添加语义类型、关系类型和可视化建议

【语义类型判断规则】:
1. 对于只有标题而没有实际内容的章节(content为空数组)：
   - 如果是主要章节(如"一、目标与任务导学设计")，应设置semantic_type为"section_header"
   - 将visualization_suggestion设置为"section_divider"
   - 这些章节通常适合作为PPT中的章节分隔页
2. 对于有实际内容的章节，根据内容特点确定语义类型:
   - 纯文本描述性内容：semantic_type为"concept"
   - 有序步骤或流程：semantic_type为"process"
   - 列表内容：semantic_type为"list"
   - 比较内容：semantic_type为"comparison"
   - 时间相关的内容：semantic_type为"timeline"
   - 数据展示相关的内容：semantic_type为"data"
   - 案例分析：semantic_type为"case_study"
3. 语义类型和关系类型必须反映内容的实际特征，不要为空内容随意赋予语义特征

【输出结构要求】：
必须生成以下格式的JSON结构：
```json
{
  "title": "文档标题",
  "subtitle": "文档副标题(如有)",
  "sections": [
    {
      "title": "第一章节标题",
      "content": [
        "普通段落文本...",
        {"type": "unordered_list", "items": ["无序列表项1", "无序列表项2", ...]},
        {"type": "ordered_list", "items": ["有序列表项1", "有序列表项2", ...]},
        "更多普通段落文本..."
      ],
      "semantic_type": "concept|process|comparison|list|section_header|...",
      "relation_type": "sequence|cause_effect|problem_solution|hierarchical|...",
      "visualization_suggestion": "bullet_points|flowchart|diagram|chart|table|image|section_divider|...",
      "subsections": [
        {
          "title": "子章节标题",
          "content": [
            "普通段落文本...",
            {"type": "unordered_list", "items": ["无序列表项1", "无序列表项2", ...]},
            "更多普通段落文本..."
          ],
          "semantic_type": "...",
          "relation_type": "...",
          "visualization_suggestion": "..."
        }
      ]
    }
  ]
}
```

【注意事项】：
1. 请确保每个章节、子章节都有标题(title)属性，没有明确标题的可提取内容要点作为标题
2. content数组必须存在（可以为空数组），所有内容都应放在content中，保持原文的顺序
3. 对于列表内容，使用特殊对象格式：{"type": "unordered_list|ordered_list", "items": [列表项...]}
4. 列表项始终保持在它所属内容的上下文中，不要丢失列表与周围段落的关系
5. 当发现明显的子部分标识符（如"**引导词**："），将其处理为子章节结构
6. 对每个章节和子章节都要基于其实际内容分析语义类型、关系类型和最佳可视化方式
7. 不要创建过于复杂的层级结构，一般不超过4级嵌套
8. 确保输出是有效的JSON格式，最终可以直接被程序解析
9. 对空内容的章节，使用"section_header"语义类型和"section_divider"可视化建议

请仅返回JSON数据，不要有任何其他回复。你的输出将直接用于PPT内容生成。"""