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

{% if markdown_text %}
Markdown文本:
```
{{ markdown_text }}
```
{% endif %}

# 1. 结构解析基础规则

## 1.1 文档标题解析
1. 识别并提取文档的标题和副标题
   - 主标题通常是文档的第一行文本，可能带有加粗(**文字**)、标题标记(# 文字)等格式
   - 副标题通常位于主标题附近（紧随其后）
   - 副标题可能以"模块主题："、"副标题："、"——"等开头，或是没有特定标记
   - 如果主标题带有"——"分隔符，可能第二部分就是副标题
   - 如"**五维导学案：亚洲地图技能及空间认知——你的"地理侦探"必修课**"为主标题，"模块主题：地图技能及空间认知"为副标题

2. 标题长度处理
   - 为每个超过8个汉字或15个英文字符的标题，提供一个精简版本
   - 精简版本应保留原标题的核心意思，去除修饰词和次要信息
   - 原始标题保存在original_title字段中，精简版标题作为主要title字段
   - 副标题也需遵循相同处理逻辑

## 1.2 文档结构识别
1. **层级结构识别原则**：
   - 标题层级结构严格按照Markdown标记(# ## ### #### #####)识别
   - "#"对应level=1，"##"对应level=2，"###"对应level=3，以此类推
   - 每个层级的标题都必须创建独立的节点，保持文档的层级结构
   - 每个节点都必须包含level字段，明确标识其标题层级
   - 一级标题下的二级标题必须作为section
   - 二级标题下的三级标题必须作为subsection
   - 三级标题下的四级标题必须作为子级subsection
   - 不能将下级标题文本内容并入上级标题的content中

2. **紧邻标题的处理**：
   - 当一个标题(如### 学习目标)紧接着下一级标题(如#### 介绍语)时：
     * 上级标题(学习目标)节点的content应为空数组[]
     * 上级标题节点应包含subsections数组，其中包含下级标题(介绍语)节点
     * 下级标题节点应包含其自身的content数组
   - 这种情况下，上级标题通常为section_header类型，表示一个分组标题
   - 不要将下级标题的内容提升到上级标题的content中
   - 每个标题层级必须保持独立，并保持正确的层级关系

3. **子部分识别**：
   - 当遇到冒号后跟列表项的格式，应将其视为独立的内容块
   - 正确区分章节标题(###)与加粗文本(**文字**)的区别

4. **内容保存原则**：
   - 原始markdown中的内容要完整保留，不要丢失或合并
   - 保持内容的原始格式和层次关系
   - 不要对特定类型的内容进行特殊处理或重新格式化

5. **分隔与跳过**：
   - 识别并跳过分隔线(---, ***, ___)，不要将它们解析为内容

# 2. 内容结构化规则

## 2.1 内容标准化处理
1. **统一内容对象格式**：所有content数组中的条目必须采用统一的对象格式
   - 基本类型和内容角色：
     * "type": 内容的基本类型，必须是以下类型之一：
       - "paragraph" - 连贯的文本段落
       - "bullet_list" - 无序列表
       - "numbered_list" - 有序列表

   - 文本段落格式:
     ```json
     {
       "type": "paragraph", 
       "content": "文本内容", 
       "word_count": 字数
     }
     ```


   - 无序列表格式:
     ```json
     {
       "type": "bullet_list", 
       "items": [
         {"content": "列表项1", "word_count": 字数},
         {"content": "列表项2", "word_count": 字数}
       ],
       "item_count": 项目数量,
       "total_word_count": 总字数
     }
     ```

   - 有序列表格式:
     ```json
     {
       "type": "numbered_list", 
       "items": [
         {"content": "列表项1", "word_count": 字数},
         {"content": "列表项2", "word_count": 字数}
       ],
       "item_count": 项目数量,
       "total_word_count": 总字数
     }
     ```



2. **内容计数统计**
   - 对于每种内容类型，必须添加相应的计数信息：
     * 文本段落：添加word_count字段，计算字符数
     * 列表内容：添加item_count字段计算列表项数量，total_word_count字段计算总字数，并为每个列表项添加word_count
   - 每个section和subsection必须添加content_stats字段，包含：
     * "total_word_count": 该节点下所有内容的总字数
     * "element_count": 内容元素总数（文本段落、列表等）
     * "content_types": 该节点包含的内容类型列表

3. **文本分段与长度控制**
   - 检测超长段落（超过150个字符），建议在合适位置分段
   - 对于长文本，记录每个自然段的字数，便于后续布局决策

## 2.2 内容节点统计
1. **章节内容统计**
   - 每个章节必须添加content_stats字段，包含：
     * "total_word_count": 该章节下所有内容的总字数（不包括子节点）
     * "element_count": 内容元素总数（文本段落、列表等）
     * "content_types": 该章节包含的内容类型列表

# 3. 标记清理规则

## 3.1 Markdown标记清除
1. 清除所有文本内容中的Markdown标记符号
   - 删除标题标记：去除文本开头的所有"#"符号及其后的空格（如"### 标题"→"标题"）
   - 删除加粗标记：去除文本中的"**"符号（如"**加粗文本**"→"加粗文本"）
   - 删除斜体标记：去除文本中的"*"和"_"符号（如"*斜体*"→"斜体"）
   - 删除代码块标记：去除```和`符号
   - 删除链接标记：将"[链接文本](URL)"格式转换为纯文本"链接文本"
   - 删除图片标记：将"![alt文本](URL)"格式转换为描述"alt文本"

2. 标题文本清理规则
   - 确保所有章节、子章节的title字段不包含"#"标记符号
   - 如"#### 介绍语"应转换为纯文本"介绍语"作为title
   - 对于加粗的标题如"**标题**"，应仅保留"标题"

3. 内容文本清理规则
   - content数组中的所有文本条目都必须去除Markdown标记
   - 列表项中的文本也要清除所有Markdown格式符号
   - 保留文本的语义和内容，只去除格式符号

# 4. 语义分析规则

## 4.1 语义类型判断
1. 对于只有标题而没有实际内容的章节(content为空数组且紧跟着下级标题)：
   - 应设置semantic_type为"section_header"
   - 这些章节通常适合作为PPT中的章节分隔页或分组标题

2. 对于有实际内容的章节，根据内容特点确定语义类型:
   - 纯文本描述性内容：semantic_type为"concept"
   - 有序步骤或流程：semantic_type为"process"
   - 列表内容：semantic_type为"list"
   - 比较内容：semantic_type为"comparison"
   - 时间相关的内容：semantic_type为"timeline"
   - 数据展示相关的内容：semantic_type为"data"
   - 案例分析：semantic_type为"case_study"


3. 语义类型和关系类型必须反映内容的实际特征，不要为空内容随意赋予语义特征

## 4.2 关系类型判断
1. 识别内容之间的关系模式：
   - 顺序关系(sequence)：步骤、阶段、时间顺序等
   - 因果关系(cause_effect)：原因与结果、影响与后果
   - 问题解决(problem_solution)：问题与解决方案、挑战与应对、设疑问题与回答
   - 层级关系(hierarchical)：分类、从属、组织结构等
   - 对比关系(comparison)：对比、比较、成功与失败等
   - 网格关系(grid)：多个平行概念或特性的并列展示

2. 基于关键词和内容结构判断关系类型：
   - 含有"问题"、"解决"等词汇的通常是problem_solution类型
   - 含有"原因"、"导致"、"结果"等词汇的通常是cause_effect类型
   - 含有数字序号或时间顺序的通常是sequence类型
   - 含有分类或层级结构的通常是hierarchical类型
   - 含有3-4个并列要点或概念的通常是grid类型

3. 特殊内容类型关系判断:
   - 有序列表(numbered_list)通常具有sequence关系类型
   - 并列的3-4个概念或特性通常具有grid关系类型，适合用feature_grid展示

# 5. 输出结构规范

## 5.1 整体结构范例
```json
{
  "title": "文档标题精简版（超过8个中文字符或15个英文字符时必须提供）",
  "original_title": "文档原始完整标题",
  "level": 1,
  "subtitle": "文档副标题精简版（超过8个中文字符或15个英文字符时必须提供）",
  "original_subtitle": "文档原始完整副标题(如有)",
  "document_stats": {
    "section_count": 章节数量,
    "total_word_count": 文档总字数
  },
  "sections": [
    {
      "title": "目标与任务导学设计",
      "original_title": "目标与任务导学设计",
      "level": 2,
      "content": [],
      "content_stats": {
        "total_word_count": 0,
        "element_count": 0,
        "content_types": [],
      },
      "semantic_type": "section_header",
      "relation_type": "hierarchical",
      "subsections": [
        {
          "title": "引导问题",
          "original_title": "引导问题",
          "level": 3,
          "content": [
            {
              "type": "paragraph",
              "content": "引导词：看一看\n 设疑问题：北京的暴雨淹没街道、新疆的葡萄因冰雹绝收…这些极端天气背后，藏着亚洲怎样的地理密码？\n 回答：（留白）",
              "word_count": 100
            }
          ],
          "content_stats": {
            "total_word_count": 100,
            "element_count": 2,
            "content_types": ["paragraph"],
          },
          "semantic_type": "instruction",
          "relation_type": "problem_solution"
        },
        {
          "title": "学习目标",
          "original_title": "学习目标",
          "level": 3,
          "content":[],
          "content_stats": {
            "total_word_count": 0,
            "element_count": 0,
            "content_types": [],
          },
          "semantic_type": "section_header",
          "relation_type": "hierarchical",
          "subsections": [
            {
              "title": "介绍语",
              "original_title": "介绍语",
              "level": 4,
              "content": [
                {
                  "type": "paragraph", 
                  "content": "上周新闻里，巴基斯坦洪水冲毁上百万人的家园；孟加拉台风让渔船沉没…这些亚洲真实灾难的背后，是山川河流的布局失衡？还是人类对地理的无知？今天起，你将化身"亚洲地理侦探"，用地图解谜技术，从等高线、风向标中找到答案。", 
                  "word_count": 78
                }
              ],
              "content_stats": {
                "total_word_count": 78,
                "element_count": 1,
                "content_types": ["paragraph"]
              },
              "semantic_type": "concept",
              "relation_type": "hierarchical"
            },
            {
              "title": "学习目标",
              "original_title": "学习目标",
              "level": 4,
              "content": [
                {
                  "type": "paragraph",
                  "content": "引导句：准备好解锁你的地图神器，让亚洲的地理谜题无所遁形！",
                  "word_count": 25
                },
                {
                  "type": "paragraph",
                  "content": "目标：",
                  "word_count": 3
                },
                {
                  "type": "numbered_list", 
                  "items": [
                    {"content": "解码地图形状：3秒内从亚洲地形图读出"帕米尔高原是地理十字路口"的证据", "word_count": 28},
                    {"content": "预测气候风云：用等降水量线图解北京暴雨的"水汽通道"来源。", "word_count": 25},
                    {"content": "空间透视术：通过经纬网定位，分析青藏铁路为何避开喜马拉雅山脉最险段。", "word_count": 28},
                    {"content": "人地关系连线：在卫星影像上圈出恒河三角洲洪灾高危区，为孟加拉渔民设计逃生路径。", "word_count": 38},
                    {"content": "未来规划师：基于GIS技术，为长江中下游设计能抗百年洪水的智能城市模型。", "word_count": 29}
                  ],
                  "item_count": 5,
                  "total_word_count": 148
                }
              ],
              "content_stats": {
                "total_word_count": 176,
                "element_count": 3,
                "content_types": ["paragraph", "numbered_list"]
              },
              "semantic_type": "list",
              "relation_type": "hierarchical"
            }
          ]
        },
        {
          "title": "学习任务",
          "original_title": "学习任务",
          "level": 3,
          "content": [
            {
              "type": "paragraph",
              "content": "问题引导：",
              "word_count": 5
            },
            {
              "type": "numbered_list", 
              "items": [
                {"content": "若东京奥运会时的台风突然转向，你能用季风图预测它袭击上海的概率吗？（单选）", "word_count": 36},
                {"content": "珠峰"身高"测量为什么要用北斗卫星而非传统测绘？（判断）", "word_count": 26},
                {"content": "假设你是中亚输油管道工程师，哪条线路既能避开地震带又最短？（绘图解答）", "word_count": 31}
              ],
              "item_count": 3,
              "total_word_count": 93
            },
            {
              "type": "paragraph", 
              "content": "学习任务：\n你的任务：成为亚洲气候/地形/灾害"三重间谍"！用分层设色地图+气象App，侦破2023年巴基斯坦洪灾的"自然帮凶"与"人类内鬼"，并制作防災科普H5推送给当地学生。", 
              "word_count": 76
            }
          ],
          "content_stats": {
            "total_word_count": 174,
            "element_count": 3,
            "content_types": ["paragraph", "numbered_list"]
          },
          "semantic_type": "task",
          "relation_type": "hierarchical"
        },
        {
          "title": "核心特性",
          "original_title": "核心特性",
          "level": 3,
          "content": [
            {
              "type": "feature_group",
              "items": [
                {"title": "特性一", "description": "特性一的详细描述", "title_word_count": 3, "description_word_count": 9},
                {"title": "特性二", "description": "特性二的详细描述", "title_word_count": 3, "description_word_count": 9},
                {"title": "特性三", "description": "特性三的详细描述", "title_word_count": 3, "description_word_count": 9},
                {"title": "特性四", "description": "特性四的详细描述", "title_word_count": 3, "description_word_count": 9}
              ],
              "item_count": 4,
              "total_word_count": 48
            }
          ],
          "content_stats": {
            "total_word_count": 48,
            "element_count": 1,
            "content_types": ["feature_group"]
          },
          "semantic_type": "feature_list",
          "relation_type": "grid"
        }
      ]
    }
  ]
}
```

## 5.2 关键规范要点
1. 所有内容必须采用统一的对象格式体系，按照type来组织
2. 每个内容对象必须包含适当的计数信息（如word_count、item_count、total_word_count等）
3. 章节层级结构必须严格保持，主章节下的subsections不能丢失或错误归类
4. 列表项中的每个item必须包含word_count
5. 每个章节和子章节必须包含content_stats统计信息，包括total_word_count、element_count和content_types
6. 文档根级必须包含document_stats统计信息，包含section_count和total_word_count
7. 原始markdown内容要完整保留，保持其原有结构
8. 确保所有计数准确无误

请仅返回JSON数据，不要有任何其他回复。你的输出将直接用于PPT内容生成。"""