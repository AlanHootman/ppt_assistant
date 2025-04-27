#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
布局决策Agent模块

负责将结构化内容与PPT模板布局进行匹配，做出最佳布局决策。
"""

import logging
from typing import Dict, Any, List, Optional, Tuple

from core.agents.base_agent import BaseAgent
from core.engine.state import AgentState

logger = logging.getLogger(__name__)

class LayoutDecisionAgent(BaseAgent):
    """布局决策Agent，负责决定内容在PPT中的布局方式"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化布局决策Agent
        
        Args:
            config: Agent配置
        """
        super().__init__(config)
        # 配置Embedding模型，实际项目中会加载OpenAI等模型
        self.embedding_model = config.get("embedding_model", "text-embedding-3-large")
        logger.info(f"初始化LayoutDecisionAgent，使用模型: {self.embedding_model}")
    
    async def run(self, state: AgentState) -> AgentState:
        """
        执行布局决策
        
        Args:
            state: 当前工作流状态
            
        Returns:
            更新后的状态
        """
        logger.info("开始布局决策")
        
        # 检查必要的输入
        if not state.content_structure:
            error_msg = "没有提供内容结构"
            self.record_failure(state, error_msg)
            return state
        
        if not state.layout_features:
            error_msg = "没有提供布局特征"
            self.record_failure(state, error_msg)
            return state
        
        try:
            # 做出布局决策
            decision_result = self._make_layout_decision(
                state.content_structure, 
                state.layout_features
            )
            
            # 更新状态
            state.decision_result = decision_result
            logger.info(f"布局决策完成，幻灯片数量: {len(decision_result.get('slides', []))}")
            
            # 记录检查点
            self.add_checkpoint(state)
            
        except Exception as e:
            error_msg = f"布局决策失败: {str(e)}"
            self.record_failure(state, error_msg)
        
        return state
    
    def _make_layout_decision(self, content_structure: Dict[str, Any], 
                             layout_features: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据内容结构和布局特征，做出布局决策
        
        Args:
            content_structure: 内容结构
            layout_features: 布局特征
            
        Returns:
            布局决策结果
        """
        logger.info("匹配内容与布局")
        
        # 提取标题
        title = content_structure.get("title", "无标题")
        
        # 提取章节
        sections = content_structure.get("sections", [])
        
        # 提取可用布局
        available_layouts = layout_features.get("layouts", [])
        available_layout_names = [layout.get("name") for layout in available_layouts]
        
        # 初始化幻灯片列表
        slides = []
        
        # 添加标题页
        slides.append({
            "type": "title",
            "content": {
                "title": title,
                "subtitle": "自动生成的演示文稿"
            }
        })
        
        # 为每个章节选择合适的布局
        for section in sections:
            section_title = section.get("title", "")
            section_content = section.get("content", [])
            section_items = section.get("items", [])
            
            # 根据内容特征选择布局
            slide_type = self._select_layout_for_content(
                section_title, 
                section_content, 
                section_items,
                available_layout_names
            )
            
            # 创建幻灯片内容
            slide_content = {
                "title": section_title
            }
            
            # 根据布局类型组织内容
            if slide_type == "twoColumns":
                # 双栏布局：将内容分为左右两栏
                midpoint = len(section_items) // 2
                slide_content["leftContent"] = section_items[:midpoint]
                slide_content["rightContent"] = section_items[midpoint:]
            elif slide_type == "image":
                # 图片布局：假设内容中包含图片路径
                slide_content["content"] = section_content
                slide_content["imagePath"] = self._extract_image_path(section_content)
                slide_content["caption"] = "图片说明"
            else:
                # 普通内容布局
                slide_content["bullets"] = section_items
                slide_content["paragraphs"] = section_content
            
            # 添加幻灯片
            slides.append({
                "type": slide_type,
                "content": slide_content
            })
        
        # 构建决策结果
        decision_result = {
            "slides": slides,
            "template": layout_features.get("templateName", "default"),
            "totalSlides": len(slides),
            "theme": {
                "colors": layout_features.get("themeColors", []),
                "fonts": layout_features.get("fontFamilies", [])
            }
        }
        
        return decision_result
    
    def _select_layout_for_content(self, title: str, content: List[str], 
                                  items: List[str], available_layouts: List[str]) -> str:
        """
        为内容选择合适的布局
        
        Args:
            title: 章节标题
            content: 章节内容
            items: 章节列表项
            available_layouts: 可用布局列表
            
        Returns:
            选择的布局类型
        """
        # 在实际项目中，这里会使用更复杂的规则或机器学习方法
        
        # 判断是否包含图片
        has_image = any(["图片" in item or "image" in item.lower() for item in items])
        if has_image and "image" in available_layouts:
            return "image"
        
        # 判断是否使用双栏布局
        if len(items) > 4 and "twoColumns" in available_layouts:
            return "twoColumns"
        
        # 默认使用内容布局
        return "content" if "content" in available_layouts else available_layouts[0]
    
    def _extract_image_path(self, content: List[str]) -> Optional[str]:
        """
        从内容中提取图片路径
        
        Args:
            content: 章节内容
            
        Returns:
            图片路径，如果没有则返回None
        """
        # 在实际项目中，这里会使用正则表达式等方法提取图片路径
        # 这里仅返回一个示例路径
        return "placeholder_image.jpg" 