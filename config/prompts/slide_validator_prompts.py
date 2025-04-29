#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
幻灯片验证Agent提示词配置
"""

SLIDE_VALIDATION_PROMPT = """分析这张PPT幻灯片图像，检查是否存在以下问题：
1. 文本溢出或截断
2. 布局不平衡或混乱
3. 文字太小或难以阅读
4. 颜色对比度不足
5. 内容过于拥挤
6. 风格不一致

如果发现问题，请详细说明并提供具体改进建议。
以下是生成此幻灯片时执行的操作：
{{ operations_json }}

请以JSON格式回答，包含以下字段：
1. has_issues: 布尔值，表示是否存在问题
2. issues: 问题列表
3. suggestions: 改进建议列表
"""

CONTENT_VALIDATION_PROMPT = """分析这个幻灯片的内容操作，检查是否存在以下问题：
1. 文本内容过多
2. 缺少清晰的标题
3. 项目符号列表过长
4. 关键信息不突出
5. 结构不清晰

以下是幻灯片的内容操作：
{{ operations_json }}

请以JSON格式回答，包含以下字段：
1. is_valid: 布尔值，表示内容是否合适
2. issues: 问题列表
3. suggestions: 改进建议列表
""" 