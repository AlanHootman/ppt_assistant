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
        # 直接使用模型配置中的值，不再需要类型转换
        self.temperature = model_config.get("temperature")
        self.max_tokens = model_config.get("max_tokens")
        
        # 图片分析批次大小配置
        self.batch_size = config.get("batch_size", 3)
        
        # 初始化PPT管理器
        self.ppt_manager = PPTManager()
        
        logger.info(f"初始化PPTAnalysisAgent，使用模型: {self.vision_model}, 批次大小: {self.batch_size}")
    
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
            "slideLayouts": visual_analysis.get("slideLayouts", []),  # 使用更新后的字段名
            "recommendations": visual_analysis.get("recommendations", {}),
            "slideImages": image_paths,  # 保存图片路径，以便后续处理
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
        
        # 使用配置的批次大小
        batch_size = self.batch_size
        
        # 获取所有幻灯片的JSON结构
        all_slides_json = presentation_json.get("slides", [])
        
        # 准备所有图像索引信息和对应的幻灯片JSON结构
        all_image_indices = []
        slides_json_map = {}
        
        for i, image_path in enumerate(image_paths):
            # 从图像路径中提取文件名
            filename = os.path.basename(image_path)
            # 尝试提取真实的幻灯片索引
            real_index = i  # 默认索引
            
            # 尝试从文件名中提取索引
            import re
            match = re.search(r'slide-(\d+)', filename)
            if match:
                try:
                    # 提取的索引通常从1开始，转换为从0开始
                    extracted_index = int(match.group(1)) - 1
                    real_index = extracted_index
                except ValueError:
                    pass
            
            # 获取对应的幻灯片JSON结构
            slide_json = None
            if 0 <= real_index < len(all_slides_json):
                slide_json = all_slides_json[real_index]
            
            # 构建图像索引信息，包含对应的幻灯片JSON
            image_info = {
                "filename": filename,
                "position": i,  # 在当前分析中的位置
                "slideIndex": real_index,  # 在原始PPT中的索引
                "slide_json": slide_json  # 添加幻灯片JSON结构
            }
            
            all_image_indices.append(image_info)
            slides_json_map[real_index] = slide_json
        
        # 准备模板信息
        template_info = {
            "template_name": presentation_json.get("name", "未知模板"),
            "slide_count": presentation_json.get("slide_count", 0),
            "theme": presentation_json.get("theme", {})
        }
        
        # 分批处理图像
        batched_results = []
        batch_count = (len(image_paths) + batch_size - 1) // batch_size
        
        for batch_idx in range(batch_count):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(image_paths))
            
            batch_images = image_paths[start_idx:end_idx]
            batch_indices = all_image_indices[start_idx:end_idx]
            
            # 提取当前批次对应的幻灯片JSON
            batch_slides_json = []
            for image_info in batch_indices:
                slide_index = image_info["slideIndex"]
                if slide_index in slides_json_map and slides_json_map[slide_index]:
                    batch_slides_json.append({
                        "slide_index": slide_index,
                        "content": slides_json_map[slide_index]
                    })
            
            logger.info(f"处理第 {batch_idx + 1}/{batch_count} 批图像，包含 {len(batch_images)} 张图片")
            
            # 准备模板上下文
            context = {
                "template_info": template_info,
                "has_images": True,
                "image_indices": batch_indices,
                "slides_json": batch_slides_json,  # 添加幻灯片JSON结构
                "presentation_json": presentation_json,
                "is_batch": True,
                "batch_info": {
                    "current": batch_idx + 1,
                    "total": batch_count
                }
            }
            
            # 渲染提示词
            prompt = self.model_manager.render_template(TEMPLATE_ANALYSIS_PROMPT, context)
            
            try:
                # 构建图片列表
                images = []
                for i, image_path in enumerate(batch_images):
                    if os.path.exists(image_path):
                        images.append({
                            "url": f"file://{image_path}", 
                            "detail": "high"
                        })
                
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
                        
                        batch_result = json.loads(json_text)
                        logger.info(f"第 {batch_idx + 1} 批图像视觉模型分析成功")
                        batched_results.append(batch_result)
                    except Exception as e:
                        logger.error(f"解析第 {batch_idx + 1} 批视觉模型响应失败: {str(e)}")
                        # 继续处理下一批，不中断整个过程
                else:
                    logger.warning("模型管理器不支持视觉模型调用")
                    # 返回错误信息
                    raise ValueError("当前模型管理器不支持视觉模型调用，无法分析幻灯片")
                    
            except Exception as e:
                logger.error(f"第 {batch_idx + 1} 批视觉模型分析失败: {str(e)}")
                # 继续处理下一批，不中断整个过程
        
        # 如果所有批次都失败，返回错误信息
        if not batched_results:
            logger.error("所有批次分析都失败")
            raise ValueError("幻灯片视觉分析失败，无法获取有效的分析结果")
        
        # 合并分析结果
        return self._merge_batch_results(batched_results, template_info)
    
    def _merge_batch_results(self, results: List[Dict[str, Any]], template_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并多批次分析结果
        
        Args:
            results: 多批次分析结果列表
            template_info: 模板信息
            
        Returns:
            合并后的分析结果
        """
        if not results:
            logger.error("没有有效的分析结果可合并")
            raise ValueError("幻灯片分析结果为空，无法合并分析结果")
        
        # 如果只有一个批次，直接返回
        if len(results) == 1:
            return results[0]
        
        # 提取第一个有效结果作为基础
        merged_result = {
            "templateName": template_info.get("template_name", "未知模板"),
            "style": results[0].get("style", "professional"),
            "visualFeatures": results[0].get("visualFeatures", {})
        }
        
        # 合并所有幻灯片布局
        all_slide_layouts = []
        for result in results:
            slide_layouts = result.get("slideLayouts", [])
            if slide_layouts:
                all_slide_layouts.extend(slide_layouts)
        
        # 确保幻灯片布局按照索引排序
        all_slide_layouts.sort(key=lambda x: x.get("slideIndex", 0))
        merged_result["slideLayouts"] = all_slide_layouts
        
        # 合并布局分组
        layout_groups = {}
        for result in results:
            for group in result.get("layoutGroups", []):
                group_name = group.get("groupName")
                if not group_name:
                    continue
                    
                if group_name not in layout_groups:
                    layout_groups[group_name] = {
                        "groupName": group_name,
                        "slideIndices": [],
                        "commonFeatures": group.get("commonFeatures", "")
                    }
                
                # 合并索引并去重
                layout_groups[group_name]["slideIndices"].extend(group.get("slideIndices", []))
                layout_groups[group_name]["slideIndices"] = list(set(layout_groups[group_name]["slideIndices"]))
        
        merged_result["layoutGroups"] = list(layout_groups.values())
        
        # 使用最后一个批次的推荐建议，通常最后一个批次有更全面的信息
        merged_result["recommendations"] = results[-1].get("recommendations", {})
        
        # 合并幻灯片摘要信息
        slide_summary = {
            "openingSlides": [],
            "contentSlides": [],
            "closingSlides": [],
            "presentationFlow": results[-1].get("slideSummary", {}).get("presentationFlow", "")
        }
        
        for result in results:
            summary = result.get("slideSummary", {})
            slide_summary["openingSlides"].extend(summary.get("openingSlides", []))
            slide_summary["contentSlides"].extend(summary.get("contentSlides", []))
            slide_summary["closingSlides"].extend(summary.get("closingSlides", []))
        
        # 去重并排序
        slide_summary["openingSlides"] = sorted(list(set(slide_summary["openingSlides"])))
        slide_summary["contentSlides"] = sorted(list(set(slide_summary["contentSlides"])))
        slide_summary["closingSlides"] = sorted(list(set(slide_summary["closingSlides"])))
        
        merged_result["slideSummary"] = slide_summary
        
        logger.info(f"成功合并 {len(results)} 批分析结果，共有 {len(all_slide_layouts)} 个幻灯片布局分析")
        return merged_result 