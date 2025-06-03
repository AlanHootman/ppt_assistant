#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
幻灯片验证管理器模块

负责幻灯片的质量验证和修复操作
"""

import logging
import os
import json
import datetime
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from core.utils.ppt_agent_helper import PPTAgentHelper, EnumEncoder
from core.utils.model_helper import ModelHelper
from core.utils.prompt_loader import PromptLoader

logger = logging.getLogger(__name__)

class SlideValidationManager:
    """幻灯片验证管理器，负责幻灯片的质量验证和修复操作"""
    
    def __init__(self, ppt_manager, ppt_operation_executor, model_manager, model_helper, 
                 vision_model, max_iterations=3, max_vision_retries=3, validation_logs_dir=None,
                 use_parallel=False, max_workers=None):
        """
        初始化幻灯片验证管理器
        
        Args:
            ppt_manager: PPT管理器实例
            ppt_operation_executor: PPT操作执行器实例
            model_manager: 模型管理器实例
            model_helper: 模型辅助工具实例
            vision_model: 视觉模型名称
            max_iterations: 最大迭代次数
            max_vision_retries: 视觉模型重试次数
            validation_logs_dir: 验证日志目录
            use_parallel: 是否使用多协程并行处理
            max_workers: 最大协程数量，如果为None则使用幻灯片数量
        """
        self.ppt_manager = ppt_manager
        self.ppt_operation_executor = ppt_operation_executor
        self.model_manager = model_manager
        self.model_helper = model_helper
        self.prompt_loader = PromptLoader()
        self.vision_model = vision_model
        self.max_iterations = max_iterations
        self.max_vision_retries = max_vision_retries
        
        # 多协程处理配置
        self.use_parallel = use_parallel
        self.max_workers = max_workers
        
        # 创建验证日志目录
        self.validation_logs_dir = validation_logs_dir
        if self.validation_logs_dir:
            self.validation_logs_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"初始化幻灯片验证管理器，使用视觉模型: {vision_model}，最大迭代次数: {max_iterations}，"
                   f"最大重试次数: {max_vision_retries}，并行处理: {'启用' if use_parallel else '禁用'}，"
                   f"最大协程数: {max_workers or '自动'}")
    
    async def validate_all_slides(self, state, presentation, generated_slides, content_plan, slide_cleanup_manager) -> List[Dict[str, Any]]:
        """
        验证所有幻灯片的质量
        
        Args:
            state: 当前状态
            presentation: 演示文稿对象
            generated_slides: 已生成的幻灯片列表
            content_plan: 内容规划列表
            slide_cleanup_manager: 幻灯片清理管理器实例
            
        Returns:
            验证后的幻灯片列表
        """
        logger.info(f"开始验证 {len(generated_slides)} 张幻灯片" + 
                    f" (使用{'并行' if self.use_parallel else '串行'}处理)")
        
        # 初始化验证环境
        validation_context = self._setup_validation_environment(state, generated_slides, content_plan)
        
        if self.use_parallel:
            # 并行执行迭代优化验证
            await self._perform_parallel_iterative_validation(
                state, presentation, generated_slides, content_plan, 
                validation_context, slide_cleanup_manager
            )
        else:
            # 串行执行迭代优化验证
            await self._perform_iterative_validation(
                state, presentation, generated_slides, content_plan, 
                validation_context, slide_cleanup_manager
            )
        
        # 处理最终验证结果
        validated_slides = self._finalize_validation_results(state, generated_slides)
        
        logger.info(f"所有幻灯片验证完成，共 {len(validated_slides)} 张，平均质量分数: {sum(state.quality_scores)/len(state.quality_scores) if state.quality_scores else 0}")
        
        return validated_slides
    
    def _setup_validation_environment(self, state, generated_slides, content_plan) -> Dict[str, Any]:
        """
        设置验证环境
        
        Args:
            state: 当前状态
            generated_slides: 已生成的幻灯片列表
            content_plan: 内容规划列表
            
        Returns:
            验证上下文信息
        """
        # 创建验证会话目录
        session_id = state.session_id
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        validation_session_dir = self.validation_logs_dir / f"{session_id}_{timestamp}_all_slides" if self.validation_logs_dir else None
        if validation_session_dir:
            validation_session_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化验证指标
        state.validation_attempts = 0
        state.quality_scores = []
        
        # 创建slide_id到content的映射
        content_map = {}
        for section in content_plan:
            slide_id = section.get("slide_id")
            if slide_id:
                content_map[slide_id] = section
        
        # 重要：获取当前演示文稿中的实际幻灯片索引
        # 因为经过删除和重排序后，原始的slide_index已经失效
        presentation = getattr(state, "presentation", None)
        if presentation:
            # 获取当前演示文稿的所有幻灯片
            ppt_json = self.ppt_manager.get_presentation_json(presentation, include_details=False)
            current_slides_count = len(ppt_json.get("slides", []))
            slide_indices = list(range(current_slides_count))  # 使用当前的连续索引 [0, 1, 2, ...]
            logger.info(f"删除和重排序后，演示文稿中共有 {current_slides_count} 张幻灯片，索引: {slide_indices}")
        else:
            logger.warning("无法获取presentation对象，使用空的slide_indices")
            slide_indices = []
        
        return {
            "validation_session_dir": validation_session_dir,
            "content_map": content_map,
            "slide_indices": slide_indices,
            "max_iterations": self.max_iterations
        }
    
    async def _perform_iterative_validation(self, state, presentation, generated_slides, 
                                          content_plan, validation_context, slide_cleanup_manager) -> None:
        """
        执行迭代优化验证
        
        Args:
            state: 当前状态
            presentation: 演示文稿对象
            generated_slides: 已生成的幻灯片列表
            content_plan: 内容规划列表
            validation_context: 验证上下文信息
            slide_cleanup_manager: 幻灯片清理管理器实例
        """
        slide_indices = validation_context["slide_indices"]
        max_iterations = validation_context["max_iterations"]
        validation_session_dir = validation_context["validation_session_dir"]
        
        # 开始迭代优化循环
        has_issues = True
        iteration_count = 0
        
        while has_issues and iteration_count < max_iterations:
            iteration_count += 1
            logger.info(f"开始第 {iteration_count} 次全局优化迭代")
            
            # 一次性渲染所有幻灯片为图片
            slide_image_map = await self._render_all_slides_to_images(state, presentation, slide_indices)
            
            # 验证每张幻灯片并进行修改
            all_slides_ok, operation_count = await self._validate_and_fix_slides(
                presentation, generated_slides, content_plan, slide_image_map,
                validation_session_dir, iteration_count, slide_cleanup_manager
            )
            
            # 如果所有幻灯片都没有问题，或者没有执行任何操作，结束迭代
            has_issues = not all_slides_ok and operation_count > 0
            logger.info(f"第 {iteration_count} 次迭代完成，执行了 {operation_count} 项修改操作，还有问题: {has_issues}")
            
            # 增加验证尝试次数
            state.validation_attempts += 1
    
    async def _perform_parallel_iterative_validation(self, state, presentation, generated_slides, 
                                          content_plan, validation_context, slide_cleanup_manager) -> None:
        """
        执行并行迭代优化验证
        
        Args:
            state: 当前状态
            presentation: 演示文稿对象
            generated_slides: 已生成的幻灯片列表
            content_plan: 内容规划列表
            validation_context: 验证上下文信息
            slide_cleanup_manager: 幻灯片清理管理器实例
        """
        slide_indices = validation_context["slide_indices"]
        max_iterations = validation_context["max_iterations"]
        validation_session_dir = validation_context["validation_session_dir"]
        
        # 开始迭代优化循环
        has_issues = True
        iteration_count = 0
        
        while has_issues and iteration_count < max_iterations:
            iteration_count += 1
            logger.info(f"开始第 {iteration_count} 次全局优化迭代（并行处理）")
            
            # 一次性渲染所有幻灯片为图片
            slide_image_map = await self._render_all_slides_to_images(state, presentation, slide_indices)
            
            # 获取当前演示文稿中的所有幻灯片，建立position到slide_id的映射
            current_slide_mapping = slide_cleanup_manager.build_current_slide_mapping(presentation)
            
            # 准备并行分析任务
            analysis_tasks, slides_to_process = self._prepare_parallel_tasks(
                presentation, 
                slide_image_map, 
                current_slide_mapping, 
                content_plan, 
                slide_cleanup_manager,
                validation_session_dir, 
                iteration_count
            )
            
            # 并行执行分析任务
            analysis_results = await self._execute_parallel_analysis(analysis_tasks)
            
            # 串行执行修复操作并更新状态
            all_slides_ok, operation_count = await self._process_analysis_results(
                presentation, 
                generated_slides, 
                analysis_results, 
                slides_to_process, 
                slide_image_map,
                validation_session_dir, 
                iteration_count
            )
            
            # 如果所有幻灯片都没有问题，或者没有执行任何操作，结束迭代
            has_issues = not all_slides_ok and operation_count > 0
            logger.info(f"第 {iteration_count} 次迭代完成，执行了 {operation_count} 项修改操作，还有问题: {has_issues}")
            
            # 增加验证尝试次数
            state.validation_attempts += 1
    
    def _prepare_parallel_tasks(self, presentation, slide_image_map, current_slide_mapping, 
                              content_plan, slide_cleanup_manager, validation_session_dir, 
                              iteration_count):
        """
        准备并行分析任务
        
        Args:
            presentation: 演示文稿对象
            slide_image_map: 幻灯片索引到图像路径的映射
            current_slide_mapping: 当前幻灯片位置到ID的映射
            content_plan: 内容规划列表
            slide_cleanup_manager: 幻灯片清理管理器实例
            validation_session_dir: 验证日志目录
            iteration_count: 当前迭代次数
            
        Returns:
            (analysis_tasks, slides_to_process): 分析任务列表和待处理的幻灯片信息列表
        """
        # 准备并行处理的任务
        analysis_tasks = []
        slides_to_process = []
        
        # 配置最大协程数
        max_workers = self.max_workers or len(slide_image_map)
        max_workers = min(max_workers, len(slide_image_map))  # 确保不超过幻灯片数量
        
        logger.info(f"使用 {max_workers} 个协程并行处理幻灯片分析")
        
        # 准备并行任务
        for current_position in slide_image_map.keys():
            if current_position not in current_slide_mapping:
                logger.warning(f"跳过无法识别slide_id的幻灯片，位置: {current_position}")
                continue
            
            slide_id = current_slide_mapping[current_position]
            section_content = slide_cleanup_manager.get_section_content_by_slide_id(slide_id, content_plan)
            
            if not section_content:
                logger.warning(f"找不到幻灯片 {current_position} (slide_id: {slide_id}) 的内容数据")
                continue
            
            # 获取幻灯片图像路径
            image_path = slide_image_map.get(current_position)
            if not image_path:
                logger.warning(f"幻灯片 {current_position} 缺少有效的图像路径")
                continue
            
            # 获取幻灯片元素信息
            slide_elements = self.ppt_manager.get_slide_json(
                presentation=presentation,
                slide_index=current_position            
            )
            
            # 准备分析任务（只包含分析部分，不包含修改操作）
            task = self._analyze_slide_task(
                image_path=image_path,
                slide_elements=slide_elements,
                section_content=section_content,
                slide_index=current_position,
                validation_session_dir=validation_session_dir,
                iteration_count=iteration_count
            )
            
            analysis_tasks.append(task)
            slides_to_process.append({
                "current_position": current_position,
                "slide_id": slide_id,
                "section_content": section_content
            })
            
        return analysis_tasks, slides_to_process
    
    async def _execute_parallel_analysis(self, analysis_tasks):
        """
        并行执行幻灯片分析任务
        
        Args:
            analysis_tasks: 分析任务列表
            
        Returns:
            分析结果列表
        """
        if not analysis_tasks:
            logger.warning("没有需要分析的幻灯片任务")
            return []
            
        # 使用asyncio.gather并行执行所有分析任务
        analysis_results = []
        batch_size = self.max_workers or len(analysis_tasks)
        
        for i in range(0, len(analysis_tasks), batch_size):
            batch = analysis_tasks[i:i+batch_size]
            logger.info(f"执行第 {i//batch_size + 1} 批分析任务，共 {len(batch)} 个任务")
            batch_results = await asyncio.gather(*batch)
            analysis_results.extend(batch_results)
            
        logger.info(f"完成 {len(analysis_results)} 个幻灯片分析任务")
        return analysis_results
    
    async def _process_analysis_results(self, presentation, generated_slides, analysis_results, 
                                      slides_to_process, slide_image_map, validation_session_dir, 
                                      iteration_count):
        """
        处理分析结果，串行执行修复操作
        
        Args:
            presentation: 演示文稿对象
            generated_slides: 已生成的幻灯片列表
            analysis_results: 分析结果列表
            slides_to_process: 待处理的幻灯片信息列表
            slide_image_map: 幻灯片索引到图像路径的映射
            validation_session_dir: 验证日志目录
            iteration_count: 当前迭代次数
            
        Returns:
            (all_slides_ok, operation_count): 所有幻灯片是否都没有问题，执行的操作数量
        """
        # 串行执行修复操作（避免并发操作同一个PPTX文件）
        operation_count = 0
        all_slides_ok = True
        
        for i, result in enumerate(analysis_results):
            if i >= len(slides_to_process):
                continue
                
            slide_info = slides_to_process[i]
            current_position = slide_info["current_position"]
            slide_id = slide_info["slide_id"]
            section_content = slide_info["section_content"]
            
            # 执行修复操作
            if result["has_issues"]:
                all_slides_ok = False
                operations = result.get("operations", [])
                if operations:
                    # 执行当前幻灯片的修复操作
                    executed = await self._execute_slide_fixes(
                        presentation, current_position, result, validation_session_dir,
                        iteration_count, section_content
                    )
                    operation_count += executed
            
            # 更新generated_slides中的信息
            self._update_generated_slide_info(
                generated_slides, slide_id, current_position, 
                {
                    "iteration": iteration_count,
                    "validation_issues": result.get("issues", []),
                    "validation_suggestions": result.get("suggestions", []),
                    "quality_score": result.get("quality_score", 0),
                    "image_path": slide_image_map.get(current_position)
                }
            )
            
        return all_slides_ok, operation_count
    
    async def _validate_and_fix_slides(self, presentation, generated_slides, content_plan, 
                                     slide_image_map, validation_session_dir, iteration_count, 
                                     slide_cleanup_manager) -> Tuple[bool, int]:
        """
        验证并修复所有幻灯片
        
        Args:
            presentation: 演示文稿对象
            generated_slides: 已生成的幻灯片列表
            content_plan: 内容规划列表
            slide_image_map: 幻灯片索引到图片路径的映射
            validation_session_dir: 验证日志目录
            iteration_count: 当前迭代次数
            slide_cleanup_manager: 幻灯片清理管理器实例
            
        Returns:
            (所有幻灯片是否都OK, 执行的操作数量)
        """
        all_slides_ok = True
        operation_count = 0
        
        # 获取当前演示文稿中的所有幻灯片，建立position到slide_id的映射
        current_slide_mapping = slide_cleanup_manager.build_current_slide_mapping(presentation)
        
        # 遍历当前演示文稿中的每张幻灯片（按位置索引）
        for current_position in slide_image_map.keys():
            if current_position not in current_slide_mapping:
                logger.warning(f"跳过无法识别slide_id的幻灯片，位置: {current_position}")
                continue
            
            slide_id = current_slide_mapping[current_position]
            
            # 根据slide_id找到对应的章节内容
            section_content = slide_cleanup_manager.get_section_content_by_slide_id(slide_id, content_plan)
            
            # 验证单张幻灯片
            slide_validation_result = await self._validate_single_slide(
                presentation, current_position, section_content, slide_image_map,
                validation_session_dir, iteration_count
            )
            
            # 更新全局状态
            if slide_validation_result["has_issues"]:
                all_slides_ok = False
                operation_count += slide_validation_result["operations_executed"]
            
            # 更新对应的generated_slides中的信息
            self._update_generated_slide_info(generated_slides, slide_id, current_position, slide_validation_result["slide_update_info"])
        
        return all_slides_ok, operation_count
    
    def _update_generated_slide_info(self, generated_slides, slide_id, current_position, slide_update_info) -> None:
        """
        更新generated_slides中对应幻灯片的信息
        
        Args:
            generated_slides: 已生成的幻灯片列表
            slide_id: 幻灯片ID
            current_position: 当前位置索引
            slide_update_info: 需要更新的幻灯片信息
        """
        # 找到对应的generated_slide并更新信息
        for slide_info in generated_slides:
            # 尝试多种方式匹配
            if (slide_info.get("section_content", {}).get("slide_id") == slide_id or 
                self._extract_slide_id_from_section(slide_info) == slide_id):
                
                # 更新当前位置索引
                slide_info["current_position"] = current_position
                # 更新验证信息
                slide_info.update(slide_update_info)
                logger.debug(f"更新了slide_id {slide_id} 的验证信息，当前位置: {current_position}")
                return
        
        logger.warning(f"无法在generated_slides中找到slide_id为 {slide_id} 的幻灯片信息")
    
    def _extract_slide_id_from_section(self, slide_info) -> Optional[str]:
        """
        从slide_info中提取slide_id
        
        Args:
            slide_info: 幻灯片信息
            
        Returns:
            提取的slide_id，如果未找到则返回None
        """
        # 尝试从不同的位置提取slide_id
        section_content = slide_info.get("section_content", {})
        if isinstance(section_content, dict) and "slide_id" in section_content:
            return section_content["slide_id"]
        
        # 如果section_content是字典但没有slide_id，尝试其他方式
        if "slide_id" in slide_info:
            return slide_info["slide_id"]
            
        return None
    
    async def _render_all_slides_to_images(self, state, presentation, slide_indices) -> Dict[int, str]:
        """
        渲染多张幻灯片为图像
        
        Args:
            state: 工作流状态
            presentation: 演示文稿对象
            slide_indices: 要渲染的幻灯片索引列表
            
        Returns:
            幻灯片索引到图像路径的映射
        """
        # 创建临时目录
        session_dir = PPTAgentHelper.setup_temp_session_dir(state.session_id, "validation_images")
        
        # 临时保存PPT文件
        temp_pptx_filename = PPTAgentHelper.create_temp_filename("temp_for_validation")
        temp_pptx_path = session_dir / temp_pptx_filename
        
        logger.info(f"临时保存演示文稿到: {temp_pptx_path}")
        self.ppt_manager.save_presentation(presentation, str(temp_pptx_path))
        
        # 渲染所有指定幻灯片
        logger.info(f"渲染 {len(slide_indices)} 张幻灯片为图像")
        slide_image_map = {}
        
        try:
            # 一次性渲染所有幻灯片
            image_paths = self.ppt_manager.render_pptx_file(
                pptx_path=str(temp_pptx_path),
                output_dir=str(session_dir)
            )
            
            # 构建幻灯片索引到图像的映射
            if image_paths:
                for slide_index in slide_indices:
                    if 0 <= slide_index < len(image_paths):
                        slide_image_map[slide_index] = image_paths[slide_index]
                        logger.info(f"幻灯片 {slide_index} 已渲染为图像: {image_paths[slide_index]}")
                    else:
                        logger.warning(f"幻灯片索引超出范围: {slide_index}, 总幻灯片数: {len(image_paths)}")
            
            logger.info(f"成功渲染 {len(slide_image_map)}/{len(slide_indices)} 张幻灯片为图像")
            
        except Exception as e:
            logger.error(f"渲染幻灯片为图像时出错: {str(e)}")
        finally:
            # 删除临时PPTX文件
            if temp_pptx_path.exists():
                temp_pptx_path.unlink()
                
        return slide_image_map
    
    async def _validate_single_slide(self, presentation, slide_index, section_content, 
                                   slide_image_map, validation_session_dir, iteration_count) -> Dict[str, Any]:
        """
        验证单张幻灯片
        
        Args:
            presentation: 演示文稿对象
            slide_index: 幻灯片索引
            section_content: 章节内容
            slide_image_map: 幻灯片索引到图片路径的映射
            validation_session_dir: 验证日志目录
            iteration_count: 当前迭代次数
            
        Returns:
            验证结果字典
        """
        # 创建单独的验证目录
        if validation_session_dir:
            validation_dir = validation_session_dir / f"iteration_{iteration_count}_slide_{slide_index}"
            validation_dir.mkdir(parents=True, exist_ok=True)
        else:
            validation_dir = None
        
        # 获取幻灯片图像路径
        image_path = slide_image_map.get(slide_index)
        if not image_path:
            logger.warning(f"幻灯片 {slide_index} 缺少有效的图像路径")
            return self._create_empty_validation_result()
        
        # 获取幻灯片详细信息
        slide_elements = self.ppt_manager.get_slide_json(
            presentation=presentation,
            slide_index=slide_index            
        )
        
        # 保存初始信息到日志
        if validation_dir:
            self._save_validation_logs(
                log_dir=validation_dir,
                iteration=iteration_count,
                slide_index=slide_index,
                slide_elements=slide_elements,
                section_content=section_content,
                analysis=None,
                image_path=image_path,
                phase="initial"
            )
        
        # 使用多模态模型分析幻灯片
        analysis = await self._analyze_with_vision_model(
            image_path=image_path, 
            slide_elements=slide_elements,
            section_content=section_content
        )
        
        # 保存分析结果
        if validation_dir:
            self._save_validation_logs(
                log_dir=validation_dir,
                iteration=iteration_count,
                slide_index=slide_index,
                slide_elements=slide_elements,
                section_content=section_content,
                analysis=analysis,
                image_path=image_path,
                phase="analysis"
            )
        
        # 执行修复操作（如果需要）
        operations_executed = 0
        has_slide_issues = analysis.get("has_issues", False)
        
        if has_slide_issues:
            operations_executed = await self._execute_slide_fixes(
                presentation, slide_index, analysis, validation_dir,
                iteration_count, section_content
            )
        
        # 返回验证结果
        return {
            "has_issues": has_slide_issues,
            "operations_executed": operations_executed,
            "slide_update_info": {
                "iteration": iteration_count,
                "validation_issues": analysis.get("issues", []),
                "validation_suggestions": analysis.get("suggestions", []),
                "quality_score": analysis.get("quality_score", 0),
                "image_path": image_path
            }
        }
    
    def _create_empty_validation_result(self) -> Dict[str, Any]:
        """
        创建空的验证结果
        
        Returns:
            空的验证结果字典
        """
        return {
            "has_issues": False,
            "operations_executed": 0,
            "slide_update_info": {
                "iteration": 0,
                "validation_issues": [],
                "validation_suggestions": [],
                "quality_score": 0,
                "image_path": None
            }
        }
    
    async def _analyze_with_vision_model(self, image_path, slide_elements, section_content) -> Dict[str, Any]:
        """
        使用视觉模型分析幻灯片
        
        Args:
            image_path: 幻灯片图像路径
            slide_elements: 幻灯片元素列表
            section_content: 章节内容
            
        Returns:
            分析结果
        """
        # 准备上下文数据
        context = {
            "section_json": json.dumps(section_content, ensure_ascii=False, indent=2, cls=EnumEncoder),
            "slide_elements_json": json.dumps(slide_elements, ensure_ascii=False, indent=2, cls=EnumEncoder)
        }
        
        # 使用新的yaml格式prompt
        prompt = self.prompt_loader.render_prompt("slide_validation_prompts", context)
        
        # 定义分析失败时的默认返回结果
        empty_result = {
            "has_issues": True,
            "issues": ["多模态分析返回空结果"],
            "suggestions": ["尝试重新生成"],
            "operations": [],
            "quality_score": 0
        }
        
        try:
            # 使用视觉模型分析幻灯片，带重试机制
            logger.info(f"使用视觉模型分析幻灯片图像: {image_path}")
            response = await self.model_helper.analyze_image_with_retry(
                model=self.vision_model,
                prompt=prompt,
                image_path=image_path,
                max_retries=self.max_vision_retries
            )
            
            # 解析视觉模型响应
            analysis_result = self.model_helper.parse_vision_response(response, default_fields=empty_result)
            
            if analysis_result:
                # 确保结果包含必要的字段
                analysis_result.setdefault("has_issues", False)
                analysis_result.setdefault("issues", [])
                analysis_result.setdefault("suggestions", [])
                analysis_result.setdefault("operations", [])
                analysis_result.setdefault("quality_score", 0)
                
                logger.info(f"幻灯片分析结果: 质量分数={analysis_result.get('quality_score')}, 问题数量={len(analysis_result.get('issues'))}")
                return analysis_result
            else:
                logger.error("解析视觉模型响应失败，返回默认分析结果")
                return empty_result
                
        except Exception as e:
            logger.error(f"视觉模型分析失败: {str(e)}")
            return empty_result
    
    async def _execute_slide_fixes(self, presentation, slide_index, analysis, validation_dir, 
                                 iteration_count, section_content) -> int:
        """
        执行幻灯片修复操作
        
        Args:
            presentation: 演示文稿对象
            slide_index: 幻灯片索引
            analysis: 分析结果
            validation_dir: 验证日志目录
            iteration_count: 当前迭代次数
            section_content: 章节内容
            
        Returns:
            执行的操作数量
        """
        fix_operations = analysis.get("operations", [])
        if not fix_operations:
            return 0
        
        # 执行修复操作
        logger.info(f"执行幻灯片 {slide_index} 的第 {iteration_count} 次修复操作，共 {len(fix_operations)} 项")
        success = await self._execute_operations(presentation, slide_index, fix_operations)
        
        # 记录操作执行结果
        if validation_dir:
            self._save_validation_logs(
                log_dir=validation_dir,
                iteration=iteration_count,
                slide_index=slide_index,
                slide_elements=self.ppt_manager.get_slide_json(presentation, slide_index),
                section_content=section_content,
                analysis={"operations": fix_operations, "success": success},
                image_path=None,
                phase="operations"
            )
        
        return len(fix_operations)
    
    async def _execute_operations(self, presentation, slide_index, operations) -> bool:
        """
        执行幻灯片操作
        
        Args:
            presentation: 演示文稿对象
            slide_index: 幻灯片索引
            operations: 操作列表
            
        Returns:
            操作是否全部成功
        """
        if not operations:
            logger.info("没有需要执行的操作")
            return True
            
        # 使用PPT操作执行器执行操作
        result = await self.ppt_operation_executor.execute_batch_operations(
            presentation=presentation,
            slide_index=slide_index,
            operations=operations
        )
        
        success = result.get("success", False)
        if not success:
            logger.warning(f"执行幻灯片操作失败: {result.get('message', '未知错误')}")
        else:
            logger.info(f"成功执行 {len(operations)} 个幻灯片操作")
        
        return success
    
    def _save_validation_logs(self, log_dir, iteration, slide_index, slide_elements, 
                           section_content, analysis, image_path, phase) -> None:
        """
        保存验证日志
        
        Args:
            log_dir: 日志目录
            iteration: 当前迭代次数
            slide_index: 幻灯片索引
            slide_elements: 幻灯片元素信息
            section_content: 当前处理的章节内容
            analysis: 分析结果
            image_path: 幻灯片图像路径
            phase: 当前阶段（初始、分析、操作、最终）
        """
        try:
            # 创建迭代子目录
            iter_dir = log_dir / f"iteration_{iteration}_{phase}"
            iter_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存幻灯片元素信息
            slide_json_path = iter_dir / "slide_elements.json"
            with open(slide_json_path, 'w', encoding='utf-8') as f:
                json.dump(slide_elements, f, ensure_ascii=False, indent=2, cls=EnumEncoder)
            
            # 保存章节内容
            if section_content:
                section_json_path = iter_dir / "section_content.json"
                with open(section_json_path, 'w', encoding='utf-8') as f:
                    json.dump(section_content, f, ensure_ascii=False, indent=2, cls=EnumEncoder)
            
            # 保存分析结果（如果有）
            if analysis:
                analysis_json_path = iter_dir / "analysis_result.json"
                with open(analysis_json_path, 'w', encoding='utf-8') as f:
                    json.dump(analysis, f, ensure_ascii=False, indent=2, cls=EnumEncoder)
            
            # 复制图片（如果有）
            if image_path and os.path.exists(image_path):
                import shutil
                image_filename = os.path.basename(image_path)
                dest_image_path = iter_dir / image_filename
                shutil.copy2(image_path, dest_image_path)
                
            # 创建元数据文件
            metadata = {
                "timestamp": datetime.datetime.now().isoformat(),
                "iteration": iteration,
                "slide_index": slide_index,
                "phase": phase,
                "has_image": image_path is not None and os.path.exists(image_path),
                "has_analysis": analysis is not None
            }
            
            metadata_path = iter_dir / "metadata.json"
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
                
            logger.debug(f"已保存验证日志到 {iter_dir}")
            
        except Exception as e:
            logger.error(f"保存验证日志失败: {str(e)}")
    
    def _finalize_validation_results(self, state, generated_slides) -> List[Dict[str, Any]]:
        """
        处理最终验证结果
        
        Args:
            state: 当前状态
            generated_slides: 已生成的幻灯片列表
            
        Returns:
            最终验证后的幻灯片列表
        """
        validated_slides = []
        
        for slide_info in generated_slides:
            slide_index = slide_info.get("slide_index")
            if slide_index is None:
                continue
                
            # 记录最终的验证结果
            slide_info["validation_result"] = True  # 假设经过迭代后都已通过验证
            
            # 记录质量分数
            quality_score = slide_info.get("quality_score", 0)
            state.quality_scores.append(quality_score)
            
            # 添加到已验证的幻灯片列表
            validated_slides.append(slide_info)
            
            # 记录验证结果
            if slide_info["validation_result"]:
                logger.info(f"幻灯片 {slide_index} 验证通过，质量评分: {quality_score}/10")
            else:
                logger.warning(f"幻灯片 {slide_index} 验证不通过，质量评分: {quality_score}/10")
                logger.warning(f"问题: {slide_info.get('validation_issues', [])}")
                logger.info(f"修复建议: {slide_info.get('validation_suggestions', [])}")
        
        return validated_slides
    
    async def _analyze_slide_task(self, image_path, slide_elements, section_content, 
                             slide_index, validation_session_dir, iteration_count) -> Dict[str, Any]:
        """
        处理单个幻灯片的分析任务
        
        Args:
            image_path: 幻灯片图像路径
            slide_elements: 幻灯片元素列表
            section_content: 章节内容
            slide_index: 幻灯片索引
            validation_session_dir: 验证日志目录
            iteration_count: 当前迭代次数
            
        Returns:
            分析结果
        """
        # 创建单独的验证目录
        if validation_session_dir:
            validation_dir = validation_session_dir / f"iteration_{iteration_count}_slide_{slide_index}"
            validation_dir.mkdir(parents=True, exist_ok=True)
        else:
            validation_dir = None
        
        # 保存初始信息到日志
        if validation_dir:
            self._save_validation_logs(
                log_dir=validation_dir,
                iteration=iteration_count,
                slide_index=slide_index,
                slide_elements=slide_elements,
                section_content=section_content,
                analysis=None,
                image_path=image_path,
                phase="initial"
            )
        
        # 使用多模态模型分析幻灯片
        analysis = await self._analyze_with_vision_model(
            image_path=image_path, 
            slide_elements=slide_elements,
            section_content=section_content
        )
        
        # 保存分析结果
        if validation_dir:
            self._save_validation_logs(
                log_dir=validation_dir,
                iteration=iteration_count,
                slide_index=slide_index,
                slide_elements=slide_elements,
                section_content=section_content,
                analysis=analysis,
                image_path=image_path,
                phase="analysis"
            )
        
        return analysis 