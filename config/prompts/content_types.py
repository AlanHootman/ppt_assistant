#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
内容类型定义模块

维护统一的semantic_type和relation_type定义，供多个Agent共享使用，
保持系统中内容类型定义的一致性。

更新日志：
- 扩展了semantic_type定义，增加了更多教育和技术内容相关的类型
- 扩展了relation_type定义，增加了几种新的内容关系类型
- 增加了教育内容专项判断指南，适用于课程、教学内容的语义匹配
- 添加了新的content_structure类型，丰富内容组织形式
- 统一了各个Agent模块的类型引用，确保系统一致性
"""

# 内容语义类型定义
SEMANTIC_TYPES = """
### 内容语义类型(semantic_type)
- introduction: 介绍性内容，如标题页、简介页
- toc: 目录页，内容提纲或章节概览
- section_header: 章节标题页，表示内容分隔和组织结构
- bullet_list: 要点列表，无序列表形式呈现的要点内容
- process_description: 过程或步骤描述，展示工作流程或操作顺序
- data_presentation: 数据展示，包含图表、数字或统计内容
- comparison: 对比内容，对比不同概念、方法或成果
- feature_list: 特性列表，产品或概念的关键特点并列展示
- summary: 总结内容，内容概括或要点回顾
- conclusion: 结论，基于前文分析得出的结论性内容
- thank_you: 感谢/结束页，表示演示结束
- concept: 概念性内容，解释、定义或介绍概念
- instruction: 指导性内容，教程或操作指南
- task: 任务描述内容，任务要求或行动指南
- question_answer: 问答式内容，包含问题和对应回答
- example_list: 示例列表，实例或案例的集合
- case_study: 案例分析，详细分析特定实例的情况
- timeline: 时间线内容，按时间顺序排列的事件或进展
- list: 列表型内容，包含有序或无序的项目集合
- values_presentation: 价值观展示，呈现理念、价值或重要信息
- methodology: 方法论内容，描述处理问题的系统方法或框架
- technical_guide: 技术指南，详细的技术操作或实现步骤
- future_outlook: 未来展望，对未来趋势或发展的预测和描述
- learning_objective: 学习目标，明确描述教学或培训的具体目标
"""

# 内容关系类型定义
RELATION_TYPES = """
### 内容关系类型(relation_type)
- none: 无特定关系，内容之间没有明确的关联性
- sequence: 顺序关系，内容按特定顺序排列，如步骤、阶段或时间顺序
- timeline: 时间线/时序关系，内容按时间先后顺序排列
- hierarchical: 层级关系，内容呈现分类、从属或组织结构关系
- comparison: 对比关系，内容展示不同选项之间的对比与比较
- cause_effect: 因果关系，展示原因与结果、影响与后果的关系
- problem_solution: 问题解决关系，展示问题与对应的解决方案
- grid: 网格排列关系，多个平行概念或特性的并列展示
- parallel: 并列关系，几个同等重要的元素并列展示
- progressive: 渐进关系，内容呈现逐步深入或递进的关系
- cyclical: 循环关系，内容呈现周期性或循环性的变化
- spatial: 空间关系，内容按照空间位置或地理分布组织
"""

# 内容结构类型定义
CONTENT_STRUCTURES = """
### 内容区域组织结构(content_structure)
- title_content: 标题+正文结构（最基本的布局）
- detail_content: 详细内容结构（包含多个详细说明的文本块）
- bullet_list: 项目符号列表结构
- numbered_list: 编号列表结构
- process_flow: 流程图结构（有明确的步骤顺序和连接）
- comparison_table: 对比表格结构
- grid_layout: 网格布局结构（项目以网格方式排列）
- image_text_pair: 图文对结构（图片+对应说明文字）
- central_focus: 中心辐射结构（中心概念+周边说明）
- timeline: 时间线结构
- free_form: 自由排布结构（无明确组织模式）
- feature_group: 特性分组结构（多个特性或功能的分组展示）
- question_set: 问题集合结构（一组相关问题的集合）
- paired_content: 成对内容结构（内容以对的形式组织）
- split_screen: 分屏结构（内容在屏幕两侧分开展示）
"""

# 语义类型判断指南
SEMANTIC_TYPE_GUIDELINES = """
### 语义类型判断指南

1. 基于内容特征判断:
   - 纯介绍性/导入内容 → introduction
   - 展示章节大纲或目录 → toc
   - 只有标题无实际内容的分组标题 → section_header
   - 包含不带序号的项目列表 → bullet_list
   - 展示步骤或顺序流程 → process_description
   - 包含图表或数据统计 → data_presentation
   - 并列对比两个或多个事物 → comparison
   - 产品或概念特性的并列呈现 → feature_list
   - 内容总结或要点回顾 → summary
   - 演讲或文档的结尾 → conclusion
   - 感谢页或标记结束 → thank_you
   - 概念讲解或定义 → concept
   - 操作指南或教程 → instruction
   - 任务要求或设计 → task
   - 问题和回答的组合 → question_answer
   - 多个案例的列举 → example_list
   - 深入分析的单个案例 → case_study
   - 按时间顺序的事件排列 → timeline
   - 任何类型的列表内容 → list
   - 学习目标或教学目标 → learning_objective
   - 价值观或核心理念展示 → values_presentation
   - 方法论或系统方法 → methodology
   - 技术操作指南 → technical_guide
   - 未来展望或预测 → future_outlook
   - 需要大段文字说明的详细内容 → content_rich

2. 多重语义类型情况:
   - 当内容符合多个语义类型时，应选择最能代表内容核心特征的1-3个类型
   - 符合多个类型时，将最匹配的类型放在最左侧
   - 避免选择超过3个类型，以保持分类的清晰性和有用性
   
3. 教育内容专项判断:
   - 包含引导问题和学习目标的内容 → instruction|learning_objective
   - 提供具体学习任务的内容 → task|instruction
   - 包含案例和经验分享的内容 → case_study|example_list
   - 描述技术思维建构步骤的内容 → process_description|methodology
   - 价值与意义相关的内容 → values_presentation|concept

4. 文字容量分类判断:
   - 需要展示大量文字内容（超过100字）→ content_rich|text_heavy

"""

# 关系类型判断指南
RELATION_TYPE_GUIDELINES = """
### 关系类型判断指南

1. 基于内容间关系判断:
   - 无明确关联的内容 → none
   - 按步骤或程序排列的内容 → sequence
   - 按时间发展排列的内容 → timeline
   - 按类别或层级结构的内容 → hierarchical
   - 呈现对比或比较的内容 → comparison
   - 展示原因和结果关系的内容 → cause_effect
   - 提出问题并给出解决方案的内容 → problem_solution
   - 并列展示3-4个平等概念的内容 → grid
   - 几个同等重要的元素同时呈现 → parallel
   - 内容从简单到复杂逐步深入 → progressive
   - 内容围绕一个循环周期展开 → cyclical
   - 内容按地理或空间位置组织 → spatial

2. 关键词识别技巧:
   - 包含"步骤""第一""然后""最后"等词语 → sequence
   - 包含日期、年份或时间标记 → timeline
   - 包含"分类""类型""级别"等词语 → hierarchical
   - 包含"相比""不同""优缺点"等词语 → comparison
   - 包含"因为""所以""导致"等词语 → cause_effect
   - 包含"问题""解决""方案"等词语 → problem_solution
   - 内容呈现网格化或并列特征 → grid
   - 包含"过去""现在""未来"等词语 → timeline或progressive
   - 包含"循环""周期""反复"等词语 → cyclical
   - 包含"东南西北""位置""地区"等词语 → spatial

3. 结构特征判识别:
   - 有序列表(numbered_list) → 通常为sequence关系
   - 层级嵌套列表 → 通常为hierarchical关系
   - 对称的两栏内容 → 通常为comparison关系
   - 3-4个并列模块 → 通常为grid关系
   - 子章节标题暗示时序 → 通常为timeline或sequence关系
   - 案例分析中的成功/失败对比 → 通常为comparison关系
   - 问题引导与答案 → 通常为problem_solution关系
   - 知识点与应用场景 → 通常为hierarchical或parallel关系
""" 