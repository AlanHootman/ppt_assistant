#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PPT模板分析Agent模块

负责分析PPT模板文件，提取布局、样式和主题特征。
"""

import logging
import os
import json
from typing import Dict, Any, List, Optional
from pathlib import Path

from core.agents.base_agent import BaseAgent
from core.engine.state import AgentState
from core.llm.model_manager import ModelManager
from config.prompts.ppt_analyzer_prompts import TEMPLATE_ANALYSIS_PROMPT

# 导入PPT管理器
try:
    from libs.ppt_manager.interfaces.ppt_api import PPTManager
except ImportError:
    logger = logging.getLogger(__name__)
    logger.error("无法导入PPT管理器，请确保libs/ppt_manager已正确安装")
    raise

logger = logging.getLogger(__name__)

class PPTAnalysisAgent(BaseAgent):
    """PPT模板分析Agent，负责分析PPT模板并提取布局特征"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化PPT模板分析Agent
        
        Args:
            config: Agent配置
        """
        super().__init__(config)
        # 初始化模型管理器
        self.model_manager = ModelManager()
        
        # 从配置获取模型类型和名称
        self.model_type = config.get("model_type", "vision")
        
        # 初始化模型属性
        model_config = self.model_manager.get_model_config(self.model_type)
        self.vision_model = model_config.get("model")
        self.temperature = model_config.get("temperature", 0.7)
        self.max_tokens = model_config.get("max_tokens", 4000)
        
        # 初始化PPT管理器
        self.ppt_manager = PPTManager()
        
        logger.info(f"初始化PPTAnalysisAgent，使用模型: {self.vision_model}")
    
    async def run(self, state: AgentState) -> AgentState:
        """
        执行PPT模板分析
        
        Args:
            state: 当前工作流状态
            
        Returns:
            更新后的状态
        """
        logger.info("开始分析PPT模板")
        
        # 检查是否有PPT模板路径
        if not state.ppt_template_path:
            error_msg = "没有提供PPT模板路径"
            self.record_failure(state, error_msg)
            return state
        
        # 检查文件是否存在
        template_path = Path(state.ppt_template_path)
        if not template_path.exists():
            error_msg = f"PPT模板文件不存在: {state.ppt_template_path}"
            self.record_failure(state, error_msg)
            return state
        
        try:
            # 分析PPT模板
            layout_features = await self._analyze_ppt_template(template_path, state)
            
            # 更新状态
            state.layout_features = layout_features
            logger.info(f"PPT模板分析完成，模板名称: {layout_features.get('templateName', '未知')}")
            
            # 记录检查点
            self.add_checkpoint(state)
            
        except Exception as e:
            error_msg = f"PPT模板分析失败: {str(e)}"
            self.record_failure(state, error_msg)
            logger.exception("PPT模板分析过程中发生异常")
        
        return state
    
    async def _analyze_ppt_template(self, template_path: Path, state: AgentState) -> Dict[str, Any]:
        """
        分析PPT模板文件
        
        Args:
            template_path: PPT模板文件路径
            state: 当前工作流状态
            
        Returns:
            分析结果，包含布局特征
        """
        logger.info(f"分析PPT模板: {template_path}")
        
        # 创建临时目录用于存储渲染的幻灯片图像
        session_dir = Path(f"workspace/sessions/{state.session_id}/template_images")
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. 加载PPT文件
        presentation = self.ppt_manager.load_presentation(str(template_path))
        if not presentation:
            raise ValueError(f"无法加载PPT文件: {template_path}")
        
        # 2. 获取PPT文件的基本信息
        presentation_json = self.ppt_manager.get_presentation_json(presentation, include_details=True)
        
        # 3. 获取所有布局信息
        layouts_json = self.ppt_manager.get_layouts_json(presentation)
        
        # 4. 渲染PPT为图片以供分析
        image_paths = self.ppt_manager.render_presentation(
            presentation=presentation,
            output_dir=str(session_dir),
            format="png"
        )
        
        # 提取有用的布局信息
        available_layouts = []
        for master in layouts_json:
            for layout in master.get("layouts", []):
                layout_info = {
                    "name": layout.get("layout_name", "未知布局"),
                    "placeholders": layout.get("placeholders", []),
                    "usage": self._infer_layout_usage(layout.get("layout_name", ""), layout.get("placeholders", []))
                }
                available_layouts.append(layout_info)
        
        # 5. 使用视觉模型分析渲染的图片
        visual_analysis = await self._analyze_slides_with_vision(image_paths, presentation_json)
        
        # 6. 组合分析结果
        template_name = template_path.stem
        theme_colors = presentation_json.get("theme", {}).get("colors", [])
        font_families = presentation_json.get("theme", {}).get("fonts", [])
        
        # 7. 构建完整的分析结果
        layout_features = {
            "templateName": template_name,
            "slideCount": presentation_json.get("slide_count", 0),
            "layouts": available_layouts,
            "theme": {
                "colors": theme_colors,
                "fonts": font_families
            },
            "visualFeatures": visual_analysis.get("visualFeatures", {}),
            "slideImages": image_paths,  # 保存图片路径，以便后续处理
            "recommendations": visual_analysis.get("recommendations", {})
        }
        
        return layout_features
    
    def _infer_layout_usage(self, layout_name: str, placeholders: List[Dict[str, Any]]) -> str:
        """
        根据布局名称和占位符推断布局用途
        
        Args:
            layout_name: 布局名称
            placeholders: 布局占位符列表
            
        Returns:
            布局用途描述
        """
        layout_name_lower = layout_name.lower()
        
        # 标题页布局
        if "title" in layout_name_lower and any(p.get("name", "").lower() == "subtitle" for p in placeholders):
            return "首页标题页"
            
        # 章节页布局
        if "section" in layout_name_lower:
            return "章节页"
            
        # 内容页布局
        if "content" in layout_name_lower:
            # 检查是否为双栏布局
            if len([p for p in placeholders if p.get("name", "").lower().startswith("content")]) > 1:
                return "双栏内容页"
            return "普通内容页"
            
        # 图片布局
        if "picture" in layout_name_lower or "photo" in layout_name_lower or "image" in layout_name_lower:
            return "图片页"
            
        # 表格布局
        if "table" in layout_name_lower:
            return "表格页"
            
        # 对比布局
        if "comparison" in layout_name_lower:
            return "对比页"
            
        # 默认判断
        placeholder_names = [p.get("name", "").lower() for p in placeholders]
        if "title" in placeholder_names:
            if "content" in placeholder_names:
                return "内容页"
            if "subtitle" in placeholder_names:
                return "标题页"
        
        # 无法确定类型
        return "未知布局类型"
    
    async def _analyze_slides_with_vision(self, image_paths: List[str], presentation_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用视觉模型分析幻灯片图像
        
        Args:
            image_paths: 幻灯片图像路径列表
            presentation_json: 演示文稿的JSON结构
            
        Returns:
            视觉分析结果
        """
        logger.info(f"使用视觉模型分析 {len(image_paths)} 张幻灯片图像")
        
        # 为了避免向模型传递太多图像，我们选择最有代表性的几张幻灯片进行分析
        # 如果图像超过5张，只选择前5张
        representative_images = image_paths[:min(30, len(image_paths))]
        
        # 对于每张图像，使用视觉模型进行分析
        # 使用Jinja2模板构建提示词
        template_info = {
            "template_name": presentation_json.get("name", "未知模板"),
            "slide_count": presentation_json.get("slide_count", 0),
            "theme": presentation_json.get("theme", {})
        }
        
        # 准备模板上下文
        context = {
            "template_info": template_info,
            "has_images": len(representative_images) > 0
        }
        
        # 使用模型管理器的模板渲染方法
        prompt = self.model_manager.render_template(TEMPLATE_ANALYSIS_PROMPT, context)
        
        # 由于视觉模型API调用需要具体的实现，这里模拟一个分析结果
        # 实际项目中应该调用self.model_manager提供的视觉模型API
        
        try:
            # 构建图片列表，实际项目中这些图片应该被编码并传给视觉模型
            images = []
            for image_path in representative_images:
                if os.path.exists(image_path):
                    images.append({"url": f"file://{image_path}", "detail": "high"})
            
            # 调用视觉模型API
            if hasattr(self.model_manager, 'generate_vision_response'):
                vision_response = await self.model_manager.generate_vision_response(
                    model=self.vision_model,
                    prompt=prompt,
                    images=images,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                
                # 解析JSON响应
                try:
                    # 清理响应中的markdown格式代码块
                    json_text = vision_response
                    if "```json" in vision_response:
                        import re
                        pattern = r"```(?:json)?\s*([\s\S]*?)```"
                        matches = re.findall(pattern, vision_response)
                        if matches:
                            json_text = matches[0]
                    
                    analysis_result = json.loads(json_text)
                    logger.info("视觉模型分析成功")
                    return analysis_result
                except Exception as e:
                    logger.error(f"解析视觉模型响应失败: {str(e)}")
                    # 返回一个默认的分析结果
                    return self._get_default_visual_analysis(template_info)
            else:
                logger.warning("模型管理器不支持视觉模型调用，使用默认分析结果")
                return self._get_default_visual_analysis(template_info)
                
        except Exception as e:
            logger.error(f"视觉模型分析失败: {str(e)}")
            # 如果分析失败，返回一个默认的分析结果
            return self._get_default_visual_analysis(template_info)
    
    def _get_default_visual_analysis(self, template_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取默认的视觉分析结果
        
        Args:
            template_info: 模板基本信息
            
        Returns:
            默认的视觉分析结果
        """
        template_name = template_info.get("template_name", "未知模板")
        
        return {
            "templateName": template_name,
            "style": "professional",
            "visualFeatures": {
                "colorScheme": "balanced",
                "designStyle": "modern",
                "layoutComplexity": "medium",
                "textDensity": "moderate"
            },
            "recommendations": {
                "textContent": "适合文字内容较多的演示",
                "dataVisualization": "提供了良好的图表支持",
                "imageContent": "图片展示效果良好",
                "presentationFlow": "结构清晰，适合逻辑性强的内容"
            }
        } 