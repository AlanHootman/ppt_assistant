#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PPT模板分析Agent模块

负责分析PPT模板文件，提取布局、样式和主题特征。
"""

import logging
import os
import json
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from core.agents.base_agent import BaseAgent
from core.engine.state import AgentState
from core.llm.model_manager import ModelManager
from core.utils.model_helper import ModelHelper
from core.utils.ppt_agent_helper import PPTAgentHelper
from config.prompts.ppt_analyzer_prompts import TEMPLATE_ANALYSIS_PROMPT
from config.prompts.content_types import (
    SEMANTIC_TYPES,
    RELATION_TYPES,
    CONTENT_STRUCTURES,
    SEMANTIC_TYPE_GUIDELINES,
    RELATION_TYPE_GUIDELINES
)
from config.settings import settings

logger = logging.getLogger(__name__)

class LayoutUsageDetector:
    """布局用途检测工具，用于推断幻灯片布局的适用场景"""
    
    @staticmethod
    def detect_layout_usage(layout_name: str, placeholders: List[Dict[str, Any]]) -> str:
        """
        根据布局名称和占位符推断布局用途
        
        Args:
            layout_name: 布局名称
            placeholders: 布局占位符列表
            
        Returns:
            布局用途描述
        """
        layout_name_lower = layout_name.lower()
        placeholder_names = [p.get("name", "").lower() for p in placeholders]
        
        # 定义布局类型与检测规则的映射
        layout_rules = [
            # (布局类型, 检测函数)
            ("首页标题页", lambda: "title" in layout_name_lower and any(p == "subtitle" for p in placeholder_names)),
            ("章节页", lambda: "section" in layout_name_lower),
            ("双栏内容页", lambda: "content" in layout_name_lower and len([p for p in placeholder_names if p.startswith("content")]) > 1),
            ("普通内容页", lambda: "content" in layout_name_lower),
            ("图片页", lambda: any(term in layout_name_lower for term in ["picture", "photo", "image"])),
            ("表格页", lambda: "table" in layout_name_lower),
            ("对比页", lambda: "comparison" in layout_name_lower),
            ("内容页", lambda: "title" in placeholder_names and "content" in placeholder_names),
            ("标题页", lambda: "title" in placeholder_names and "subtitle" in placeholder_names),
        ]
        
        # 按顺序检查每个规则
        for layout_type, rule_func in layout_rules:
            if rule_func():
                return layout_type
        
        # 无法确定类型
        return "未知布局类型"

class PPTAnalysisAgent(BaseAgent):
    """PPT模板分析Agent，负责分析PPT模板并提取布局特征"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化PPT模板分析Agent
        
        Args:
            config: Agent配置
        """
        super().__init__(config)
        # 初始化模型管理器和辅助工具
        self.model_manager = ModelManager()
        self.model_helper = ModelHelper(self.model_manager)
        
        # 获取模型配置
        model_config = self.model_helper.get_model_config(config, "vision")
        self.vision_model = model_config.get("model")
        self.temperature = model_config.get("temperature")
        self.max_tokens = model_config.get("max_tokens")
        self.max_retries = model_config.get("max_retries", 3)
        
        # 图片分析批次大小配置
        self.batch_size = config.get("batch_size", 1)
        
        # 并行处理配置 - 优先使用配置参数，如果没有则使用环境变量设置
        self.use_parallel = config.get("use_parallel_analysis", settings.USE_PARALLEL_ANALYSIS)
        self.max_workers = config.get("analysis_max_workers", settings.ANALYSIS_MAX_WORKERS)
        
        # 初始化PPT管理器
        self.ppt_manager = PPTAgentHelper.init_ppt_manager()
        if not self.ppt_manager:
            raise ImportError("无法初始化PPT管理器，请确保PPT Manager已正确安装")
        
        # 布局用途检测器
        self.layout_detector = LayoutUsageDetector()
        
        logger.info(f"初始化PPTAnalysisAgent，使用模型: {self.vision_model}，批次大小: {self.batch_size}，"
                   f"最大重试次数: {self.max_retries}，并行处理: {'启用' if self.use_parallel else '禁用'}，"
                   f"最大协程数: {self.max_workers or '自动'}")
    
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
        session_dir = PPTAgentHelper.setup_temp_session_dir(state.session_id, "template_images")
        
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
                    "usage": LayoutUsageDetector.detect_layout_usage(
                        layout.get("layout_name", ""), 
                        layout.get("placeholders", [])
                    )
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
            "slideLayouts": visual_analysis.get("slideLayouts", []),
            "recommendations": visual_analysis.get("recommendations", {}),
            "slideImages": image_paths,  # 保存图片路径，以便后续处理
        }
        
        return layout_features
    
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
            if i < len(all_slides_json):
                slide_json = all_slides_json[i]
                all_image_indices.append((i, image_path))
                slides_json_map[i] = slide_json
        
        # 根据配置决定使用串行或并行处理
        if self.use_parallel:
            logger.info(f"使用并行处理分析 {len(all_image_indices)} 张幻灯片图像")
            batch_results = await self._analyze_batch_parallel(all_image_indices, slides_json_map)
        else:
            logger.info(f"使用串行处理分析 {len(all_image_indices)} 张幻灯片图像")
            batch_results = await self._analyze_batch_serial(all_image_indices, slides_json_map, batch_size)
        
        # 合并所有批次的结果
        return self._merge_batch_results(batch_results, presentation_json)
    
    async def _analyze_batch(self, image_paths: List[str], slides_json: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        分析一批幻灯片图像
        
        Args:
            image_paths: 当前批次的图像路径
            slides_json: 当前批次的幻灯片JSON结构
            
        Returns:
            当前批次的分析结果
        """
        if not image_paths:
            logger.warning("没有要分析的图像")
            return None
        
        # 构建提示词
        template_info = {"slides": slides_json}
        prompt = self._build_analysis_prompt(image_paths, template_info)
        
        try:
            # 使用视觉模型分析图像
            logger.info(f"开始分析 {len(image_paths)} 张幻灯片图像，使用模型: {self.vision_model}")
            
            # 使用重试机制调用视觉模型
            response = await self.model_helper.analyze_image_with_retry(
                model=self.vision_model,
                prompt=prompt,
                image_path=image_paths[0],  # 使用第一张图作为输入
                max_retries=self.max_retries
            )
            
            # 解析视觉模型响应
            analysis_result = self.model_helper.parse_json_response(response)
            
            if not analysis_result:
                logger.error("视觉模型返回的JSON无法解析")
                return {"slideLayouts": [], "visualFeatures": {}, "recommendations": {}}
            
            logger.info(f"成功分析 {len(image_paths)} 张幻灯片图像")
            return analysis_result
            
        except Exception as e:
            logger.error(f"分析幻灯片图像时出错: {str(e)}")
            # 返回空结果
            return {"slideLayouts": [], "visualFeatures": {}, "recommendations": {}}
    
    def _build_analysis_prompt(self, image_paths: List[str], template_info: Dict[str, Any]) -> str:
        """
        构建用于视觉分析的提示词
        
        Args:
            image_paths: 图像路径列表
            template_info: 模板信息
            
        Returns:
            提示词
        """
        # 将template_info转换为JSON字符串
        template_info_json = json.dumps(template_info, ensure_ascii=False, indent=2)
        
        # 构建上下文
        context = {
            # 添加模板信息和图像相关的变量
            "template_info": template_info,  # 添加模板信息对象
            "has_images": len(image_paths) > 0,  # 添加是否有图像的标志
            "image_indices": template_info.get("slides", []),  # 添加幻灯片JSON结构数据
            "template_info_json": template_info_json,
            "image_count": len(image_paths),
            # 添加内容类型变量到上下文中
            "SEMANTIC_TYPES": SEMANTIC_TYPES,
            "RELATION_TYPES": RELATION_TYPES,
            "CONTENT_STRUCTURES": CONTENT_STRUCTURES,
            "SEMANTIC_TYPE_GUIDELINES": SEMANTIC_TYPE_GUIDELINES,
            "RELATION_TYPE_GUIDELINES": RELATION_TYPE_GUIDELINES
        }
        
        # 使用ModelManager的render_template方法渲染模板
        return self.model_manager.render_template(TEMPLATE_ANALYSIS_PROMPT, context)
    
    def _merge_batch_results(self, results: List[Dict[str, Any]], template_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并多个批次的分析结果
        
        Args:
            results: 批次分析结果列表
            template_info: 模板信息
            
        Returns:
            合并后的分析结果
        """
        if not results:
            logger.warning("没有任何分析结果可合并")
            return {"slideLayouts": []}
        
        # 初始化合并结果
        merged_result = {
            "slideLayouts": []
        }
        
        # 合并所有批次的结果
        for result in results:
            # 合并幻灯片布局
            layouts = result.get("slideLayouts", [])
            if layouts:
                merged_result["slideLayouts"].extend(layouts)
        
        # 根据slide_index排序slideLayouts
        if merged_result["slideLayouts"]:
            merged_result["slideLayouts"].sort(key=lambda x: x.get("slide_index", float('inf')))
            logger.info(f"已将 {len(merged_result['slideLayouts'])} 个幻灯片布局按slide_index排序")
        
        return merged_result
    
    def add_checkpoint(self, state: AgentState) -> None:
        """
        添加工作流检查点
        
        Args:
            state: 工作流状态
        """
        state.add_checkpoint("ppt_analyzer_completed")
        logger.info("添加检查点: ppt_analyzer_completed")
    
    async def _analyze_batch_parallel(self, all_image_indices: List[Tuple[int, str]], 
                                slides_json_map: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        并行分析多个幻灯片图像
        
        Args:
            all_image_indices: 图像索引和路径元组的列表 [(index, path), ...]
            slides_json_map: 幻灯片索引到JSON结构的映射
            
        Returns:
            分析结果列表
        """
        # 配置最大协程数
        max_workers = self.max_workers or len(all_image_indices)
        max_workers = min(max_workers, len(all_image_indices))
        
        logger.info(f"使用 {max_workers} 个协程并行分析幻灯片图像")
        
        # 创建分析任务
        analysis_tasks = []
        
        for idx, image_path in all_image_indices:
            slide_json = slides_json_map.get(idx, {})
            # 创建单个图像分析任务
            task = self._analyze_single_image_task(image_path, [slide_json])
            analysis_tasks.append(task)
        
        # 并行执行所有分析任务
        results = []
        for i in range(0, len(analysis_tasks), max_workers):
            batch = analysis_tasks[i:i+max_workers]
            logger.info(f"执行第 {i//max_workers + 1} 批图像分析任务，共 {len(batch)} 个任务")
            batch_results = await asyncio.gather(*batch)
            # 过滤掉空结果
            valid_results = [result for result in batch_results if result]
            results.extend(valid_results)
        
        logger.info(f"完成 {len(results)} 个幻灯片图像的并行分析")
        return results
    
    async def _analyze_single_image_task(self, image_path: str, slides_json: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        分析单个幻灯片图像的任务
        
        Args:
            image_path: 图像路径
            slides_json: 幻灯片JSON结构列表
            
        Returns:
            分析结果
        """
        try:
            logger.info(f"开始分析图像: {image_path}")
            
            # 构建提示词
            template_info = {"slides": slides_json}
            prompt = self._build_analysis_prompt([image_path], template_info)
            
            # 使用视觉模型分析图像
            response = await self.model_helper.analyze_image_with_retry(
                model=self.vision_model,
                prompt=prompt,
                image_path=image_path,
                max_retries=self.max_retries
            )
            
            # 解析视觉模型响应
            analysis_result = self.model_helper.parse_json_response(response)
            
            if not analysis_result:
                logger.error(f"视觉模型返回的JSON无法解析: {image_path}")
                return {"slideLayouts": [], "visualFeatures": {}, "recommendations": {}}
            
            logger.info(f"成功分析图像: {image_path}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"分析图像 {image_path} 时出错: {str(e)}")
            return None
    
    async def _analyze_batch_serial(self, all_image_indices: List[Tuple[int, str]], 
                                slides_json_map: Dict[int, Dict[str, Any]], batch_size: int) -> List[Dict[str, Any]]:
        """
        串行分析多个幻灯片图像
        
        Args:
            all_image_indices: 图像索引和路径元组的列表 [(index, path), ...]
            slides_json_map: 幻灯片索引到JSON结构的映射
            batch_size: 批处理大小
            
        Returns:
            分析结果列表
        """
        logger.info(f"使用串行处理分析 {len(all_image_indices)} 张幻灯片图像")
        
        # 处理每个批次的图像
        batch_results = []
        
        for i in range(0, len(all_image_indices), batch_size):
            # 获取当前批次的图像
            batch_indices = all_image_indices[i:i+batch_size]
            
            # 收集当前批次的幻灯片JSON
            batch_slides_json = [slides_json_map[idx] for idx, _ in batch_indices if idx in slides_json_map]
            
            # 收集当前批次的图像路径
            batch_image_paths = [path for _, path in batch_indices]
            
            # 分析当前批次
            batch_result = await self._analyze_batch(batch_image_paths, batch_slides_json)
            
            # 添加批次分析结果
            if batch_result:
                batch_results.append(batch_result)
                
        logger.info(f"完成 {len(batch_results)} 批次的串行分析")
        return batch_results 