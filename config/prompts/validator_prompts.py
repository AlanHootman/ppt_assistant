#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
验证器Agent提示词配置
"""

CONTENT_VALIDATION_PROMPT = """
请验证以下PPT内容是否符合质量标准和原始需求：

原始内容结构:
{original_content}

生成的PPT内容:
{generated_ppt}

请从以下角度进行验证:
1. 完整性：是否包含所有原始内容的关键点
2. 准确性：内容是否有错误或偏离原意
3. 结构性：逻辑结构是否清晰一致
4. 专业性：表达是否专业、简洁
5. 视觉平衡：内容分布是否合理

返回JSON格式的验证结果，示例:
{
  "valid": true/false,
  "issues": [
    {
      "slide": 2,
      "issue": "问题描述",
      "severity": "high/medium/low",
      "suggestion": "修改建议"
    }
  ],
  "overall_score": 85,
  "recommendations": ["整体建议1", "整体建议2"]
}

只返回JSON数据，不要有其他回复。
"""

DESIGN_VALIDATION_PROMPT = """
验证以下PPT设计是否符合专业设计标准：

设计内容:
{design_content}

请从以下角度进行验证:
1. 一致性：设计元素是否保持一致
2. 可读性：文字大小、对比度是否适宜
3. 色彩使用：配色是否协调且符合品牌
4. 信息层次：重点内容是否突出
5. 整体美观：布局是否平衡美观

返回JSON格式的验证结果，包含具体问题和改进建议。
""" 