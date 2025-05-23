#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PPT清理与保存Agent模块

负责清理模板幻灯片、整理最终PPT文件并保存输出。
"""

import logging
import os
import datetime
import re
import json
import uuid
import enum
from pathlib import Path
from typing import Dict, Any, List, Optional

from core.agents.base_agent import BaseAgent
from core.engine.state import AgentState
from core.llm.model_manager import ModelManager
from config.prompts.slide_generator_prompts import SLIDE_SELF_VALIDATION_PROMPT
from config.settings import settings

logger = logging.getLogger(__name__)

# 导入PPT管理器
try:
    from interfaces.ppt_api import PPTManager
except ImportError:
    logger = logging.getLogger(__name__)
    logger.error("无法导入PPTManager，请确保ppt_manager库已正确安装")
    PPTManager = None

class EnumEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, enum.Enum):
            return obj.value if hasattr(obj, 'value') else str(obj)
        return super().default(obj)

class PPTFinalizerAgent(BaseAgent):
    """PPT清理与保存Agent，负责最终PPT的处理与输出"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化PPT清理与保存Agent
        
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
        self.temperature = model_config.get("temperature")
        self.max_tokens = model_config.get("max_tokens")
        
        # 验证迭代相关配置
        self.max_iterations = config.get("max_iterations", settings.MAX_SLIDE_ITERATIONS)
        
        # 初始化PPTManager
        try:
            from interfaces.ppt_api import PPTManager
            self.ppt_manager = PPTManager()
            logger.info("成功初始化PPT管理器")
        except ImportError as e:
            logger.error(f"无法导入PPTManager: {str(e)}")
            self.ppt_manager = None
        
        # 创建验证日志目录
        self.validation_logs_dir = settings.LOG_DIR / "slide_validation"
        self.validation_logs_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"初始化PPTFinalizerAgent，使用模型: {self.vision_model}, 最大迭代次数: {self.max_iterations}")
    
    async def run(self, state: AgentState) -> AgentState:
        """
        执行PPT清理、验证与保存
        
        Args:
            state: 当前工作流状态
            
        Returns:
            更新后的状态
        """
        logger.info("开始清理、验证和保存PPT")
        
        try:
            # 获取presentation对象和已生成的幻灯片
            presentation = getattr(state, "presentation", None)
            if not presentation:
                error_msg = "找不到presentation对象，无法保存PPT"
                logger.error(error_msg)
                state.record_failure(error_msg)
                return state
                
            generated_slides = getattr(state, "generated_slides", [])
            logger.info(f"获取到已生成的幻灯片列表: {len(generated_slides)} 张")
            
            # 记录每个幻灯片的索引，便于调试
            slide_indices = [slide.get("slide_index") for slide in generated_slides if slide.get("slide_index") is not None]
            logger.info(f"幻灯片索引列表: {slide_indices}")
            
            # 获取content_plan
            content_plan = getattr(state, "content_plan", [])
            if not content_plan:
                logger.warning("找不到content_plan，将跳过幻灯片排序和内容验证")
                return state

            # 1. 删除未使用的幻灯片（只保留generated_slides中记录的幻灯片）
            logger.info("删除未使用的模板幻灯片")
            self._delete_unused_slides(presentation, generated_slides)
            
            # 2. 重新排序幻灯片
            logger.info("根据content_plan重新排序幻灯片")
            self._reorder_slides(presentation, content_plan)
            
            # 3. 生成所有幻灯片截图并进行质量验证
            validated_slides = await self._validate_all_slides(state, presentation, generated_slides, content_plan)
            logger.info(f"完成 {len(validated_slides)}/{len(generated_slides)} 张幻灯片的质量验证")
            
            # 获取或创建输出目录
            output_dir = getattr(state, "output_dir", "workspace/output")
            os.makedirs(output_dir, exist_ok=True)
            
            # 生成输出文件路径
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"presentation_{state.session_id}_{timestamp}.pptx"
            output_path = os.path.join(output_dir, output_filename)
            
            # 保存前检查演示文稿状态
            ppt_json = self.ppt_manager.get_presentation_json(presentation, include_details=False)
            all_slides = ppt_json.get("slides", [])
            logger.info(f"保存前，演示文稿中共有 {len(all_slides)} 张幻灯片")
            
            # 保存演示文稿
            logger.info(f"保存演示文稿到: {output_path}")
            saved_path = self.ppt_manager.save_presentation(presentation, output_path)
            
            # 更新状态
            state.output_ppt_path = saved_path
            state.validated_slides = validated_slides
            logger.info(f"PPT已成功保存: {saved_path}")
            
            # 记录检查点
            self.add_checkpoint(state)
            
        except Exception as e:
            error_msg = f"PPT清理与保存失败: {str(e)}"
            logger.error(error_msg)
            logger.exception(e)
            self.record_failure(state, error_msg)
        
        return state
    
    def _delete_template_slides(self, presentation: Any, template_slide_indices: List[int]) -> None:
        """
        删除原始模板幻灯片
        
        Args:
            presentation: PPT演示文稿对象
            template_slide_indices: 模板幻灯片索引列表
        """
        if not self.ppt_manager:
            logger.warning("PPTManager未初始化，无法删除模板幻灯片")
            return
            
        # 按照索引从大到小排序，避免删除时的索引变化影响
        sorted_indices = sorted(template_slide_indices, reverse=True)
        
        for slide_index in sorted_indices:
            try:
                result = self.ppt_manager.delete_slide(presentation, slide_index)
                if result.get("success"):
                    logger.info(f"已删除模板幻灯片，索引: {slide_index}")
                else:
                    logger.warning(f"删除模板幻灯片失败，索引: {slide_index}, 原因: {result.get('message')}")
            except Exception as e:
                logger.warning(f"删除模板幻灯片出错，索引: {slide_index}, 原因: {str(e)}")
    
    def _reorder_slides(self, presentation: Any, content_plan: List[Dict[str, Any]]) -> None:
        """
        根据content_plan中的page_number信息重新排序幻灯片
        
        Args:
            presentation: PPT演示文稿对象
            content_plan: 内容规划列表，每个元素包含slide_id和page_number
        """
        if not self.ppt_manager:
            logger.warning("PPTManager未初始化，无法重新排序幻灯片")
            return
        
        # 创建slide_id到page_number的映射
        slide_id_to_page = {}
        for slide_info in content_plan:
            slide_id = slide_info.get("slide_id")
            page_number = slide_info.get("page_number")
            if slide_id and page_number is not None:
                slide_id_to_page[slide_id] = page_number
        
        if not slide_id_to_page:
            logger.warning("内容规划中没有找到有效的slide_id和page_number映射")
            return
        
        logger.info(f"获取到slide_id到page_number的映射: {slide_id_to_page}")
        
        # 创建当前幻灯片索引到slide_id的映射
        current_slides = {}
        try:
            # 遍历所有幻灯片的备注信息
            ppt_json = self.ppt_manager.get_presentation_json(presentation, include_details=False)
            for slide_index in range(len(ppt_json.get("slides", []))):
                # 获取幻灯片备注
                notes_result = self.ppt_manager.get_slide_notes(presentation, slide_index)
                if notes_result.get("success") and notes_result.get("notes"):
                    notes = notes_result.get("notes", "")
                    # 使用正则表达式匹配slide_id
                    match = re.search(r"slide_id:\s*(slide_\d+)", notes)
                    if match:
                        slide_id = match.group(1)
                        current_slides[slide_index] = slide_id
                        logger.info(f"幻灯片索引 {slide_index} 对应的slide_id: {slide_id}")
            
            # 检查是否找到了足够的幻灯片
            if not current_slides:
                logger.warning("未在幻灯片备注中找到任何slide_id信息，无法进行排序")
                return
                
            # 根据page_number对幻灯片进行排序
            # 创建源索引到目标索引的映射
            moves = []
            for current_index, slide_id in current_slides.items():
                if slide_id in slide_id_to_page:
                    target_index = slide_id_to_page[slide_id]
                    moves.append((current_index, target_index))
            
            # 按目标索引排序，确保移动操作的正确性
            moves.sort(key=lambda x: x[1])
            
            # 执行移动操作
            for source_index, target_index in moves:
                try:
                    result = self.ppt_manager.move_slide(presentation, source_index, target_index)
                    if result.get("success"):
                        logger.info(f"成功将幻灯片从索引 {source_index} 移动到 {target_index}")
                    else:
                        logger.warning(f"移动幻灯片失败: {result.get('message')}")
                except Exception as e:
                    logger.error(f"移动幻灯片时出错: {str(e)}")
                    
        except Exception as e:
            logger.error(f"重新排序幻灯片时发生错误: {str(e)}")
    
    def _delete_unused_slides(self, presentation: Any, generated_slides: List[Dict[str, Any]]) -> None:
        """
        删除未使用的幻灯片，只保留generated_slides中记录的幻灯片
        
        Args:
            presentation: PPT演示文稿对象
            generated_slides: 已生成的幻灯片列表，每个元素包含slide_index
        """
        if not self.ppt_manager:
            logger.warning("PPTManager未初始化，无法删除未使用的幻灯片")
            return
        
        # 如果没有已生成的幻灯片，则不执行删除操作
        if not generated_slides:
            logger.warning("没有已生成的幻灯片记录，跳过删除操作")
            return
        
        # 提取所有已生成的幻灯片索引
        generated_slide_indices = [slide.get("slide_index") for slide in generated_slides if slide.get("slide_index") is not None]
        
        if not generated_slide_indices:
            logger.warning("生成的幻灯片列表中没有有效的slide_index，跳过删除操作")
            return
            
        logger.info(f"已生成的幻灯片索引: {generated_slide_indices}")
        
        try:
            # 获取演示文稿中的所有幻灯片
            ppt_json = self.ppt_manager.get_presentation_json(presentation, include_details=False)
            all_slides = ppt_json.get("slides", [])
            
            logger.info(f"演示文稿中共有 {len(all_slides)} 张幻灯片")
            
            # 找出需要删除的幻灯片索引（不在generated_slide_indices中的）
            slides_to_delete = []
            preserved_slides = []
            
            for i, slide in enumerate(all_slides):
                real_index = slide.get("real_index", i)
                if real_index not in generated_slide_indices:
                    slides_to_delete.append(real_index)
                else:
                    preserved_slides.append(real_index)
            
            logger.info(f"需要保留的幻灯片索引: {preserved_slides}")
            logger.info(f"需要删除的幻灯片索引: {slides_to_delete}")
            
            # 安全检查：确保不会删除所有幻灯片
            if len(slides_to_delete) == len(all_slides):
                logger.error("安全检查失败：删除操作将移除所有幻灯片，已中止")
                return
            
            # 删除未使用的幻灯片（从后向前删除，避免索引变化）
            slides_to_delete.sort(reverse=True)
            for slide_index in slides_to_delete:
                try:
                    result = self.ppt_manager.delete_slide(presentation, slide_index)
                    if result.get("success"):
                        logger.info(f"已删除未使用的幻灯片，索引: {slide_index}")
                    else:
                        logger.warning(f"删除幻灯片失败，索引: {slide_index}, 原因: {result.get('message')}")
                except Exception as e:
                    logger.warning(f"删除幻灯片出错，索引: {slide_index}, 原因: {str(e)}")
        except Exception as e:
            logger.error(f"删除未使用幻灯片过程中发生错误: {str(e)}") 
    
    async def _validate_all_slides(self, state: AgentState, presentation: Any, 
                                  generated_slides: List[Dict[str, Any]], 
                                  content_plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        验证所有幻灯片的质量
        
        Args:
            state: 当前状态
            presentation: 演示文稿对象
            generated_slides: 已生成的幻灯片列表
            content_plan: 内容规划列表
            
        Returns:
            验证后的幻灯片列表
        """
        logger.info(f"开始验证 {len(generated_slides)} 张幻灯片")
        
        # 创建验证会话目录
        session_id = state.session_id
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        validation_session_dir = self.validation_logs_dir / f"{session_id}_{timestamp}_all_slides"
        validation_session_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化验证指标
        state.validation_attempts = 0
        state.quality_scores = []
        
        # 存储验证结果
        validated_slides = []
        
        # 创建slide_id到content的映射
        content_map = {}
        for section in content_plan:
            slide_id = section.get("slide_id")
            if slide_id:
                content_map[slide_id] = section
        
        # 提取所有需要验证的幻灯片索引
        slide_indices = [slide_info.get("slide_index") for slide_info in generated_slides 
                        if slide_info.get("slide_index") is not None]
        
        # 最大迭代次数
        max_iterations = self.max_iterations
        
        # 开始迭代优化循环
        has_issues = True
        iteration_count = 0
        
        while has_issues and iteration_count < max_iterations:
            iteration_count += 1
            logger.info(f"开始第 {iteration_count} 次全局优化迭代")
            
            # 一次性渲染所有幻灯片为图片
            slide_image_map = await self._render_all_slides_to_images(state, presentation, slide_indices)
            
            # 验证每张幻灯片并进行修改
            all_slides_ok = True
            operation_count = 0
            
            for slide_info in generated_slides:
                slide_index = slide_info.get("slide_index")
                if slide_index is None or slide_index not in slide_image_map:
                    logger.warning(f"跳过缺少有效图片的幻灯片，索引: {slide_index}")
                    continue
                    
                section_index = slide_info.get("section_index")
                if section_index is None or section_index >= len(content_plan):
                    logger.warning(f"幻灯片 {slide_index} 缺少有效的section_index")
                    section_content = None
                else:
                    section_content = content_plan[section_index]
                
                # 验证单张幻灯片
                validation_dir = validation_session_dir / f"iteration_{iteration_count}_slide_{slide_index}"
                validation_dir.mkdir(parents=True, exist_ok=True)
                
                # 获取该幻灯片的图像路径
                image_path = slide_image_map.get(slide_index)
                if not image_path:
                    logger.warning(f"幻灯片 {slide_index} 缺少有效的图像路径")
                    continue
                
                # 获取幻灯片详细信息
                slide_elements = self.ppt_manager.get_slide_json(
                    presentation=presentation,
                    slide_index=slide_index            
                )
                
                # 保存初始信息到日志
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
                
                # 检查是否有问题需要修复
                has_slide_issues = analysis.get("has_issues", False)
                
                # 如果有任何一张幻灯片有问题，则标记全局还有问题
                if has_slide_issues:
                    all_slides_ok = False
                    
                    # 获取修改操作列表
                    fix_operations = analysis.get("operations", [])
                    if fix_operations:
                        # 执行修复操作
                        logger.info(f"执行幻灯片 {slide_index} 的第 {iteration_count} 次修复操作，共 {len(fix_operations)} 项")
                        success = await self._execute_operations(presentation, slide_index, fix_operations)
                        operation_count += len(fix_operations)
                        
                        # 记录操作执行结果
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
                
                # 更新幻灯片信息
                slide_info.update({
                    "iteration": iteration_count,
                    "validation_issues": analysis.get("issues", []),
                    "validation_suggestions": analysis.get("suggestions", []),
                    "quality_score": analysis.get("quality_score", 0),
                    "image_path": image_path
                })
            
            # 如果所有幻灯片都没有问题，或者没有执行任何操作，结束迭代
            has_issues = not all_slides_ok and operation_count > 0
            logger.info(f"第 {iteration_count} 次迭代完成，执行了 {operation_count} 项修改操作，还有问题: {has_issues}")
            
            # 增加验证尝试次数
            state.validation_attempts += 1
        
        # 最终验证结果处理
        for slide_info in generated_slides:
            slide_index = slide_info.get("slide_index")
            if slide_index is None:
                continue
                
            # 记录最终的验证结果
            slide_info["validation_result"] = not has_issues or iteration_count >= max_iterations
            
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
        
        
        logger.info(f"所有幻灯片验证完成，共 {len(validated_slides)} 张，平均质量分数: {sum(state.quality_scores)/len(state.quality_scores) if state.quality_scores else 0}")
        
        return validated_slides
    
    async def _render_all_slides_to_images(self, state: AgentState, presentation: Any, slide_indices: List[int]) -> Dict[int, str]:
        """
        一次性渲染所有幻灯片为图片
        
        Args:
            state: 当前状态
            presentation: 演示文稿对象
            slide_indices: 要渲染的幻灯片索引列表
            
        Returns:
            幻灯片索引到图片路径的映射字典
        """
        # 创建临时目录用于存储渲染的幻灯片图像和临时PPTX文件
        session_dir = Path(f"workspace/sessions/{state.session_id}/validator_images")
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建唯一的临时文件名
        temp_pptx_filename = f"temp_{uuid.uuid4().hex}.pptx"
        temp_pptx_path = session_dir / temp_pptx_filename
        
        # 存储索引到图片路径的映射
        slide_image_map = {}
        
        try:
            # 临时保存修改后的presentation对象为PPTX文件
            logger.info(f"临时保存修改后的演示文稿到: {temp_pptx_path}")
            self.ppt_manager.save_presentation(presentation, str(temp_pptx_path))
            
            # 一次性渲染所有幻灯片
            logger.info(f"一次性渲染所有幻灯片")
            
            # 不传slide_index参数，render_pptx_file将渲染所有幻灯片
            all_image_paths = self.ppt_manager.render_pptx_file(
                pptx_path=str(temp_pptx_path),
                output_dir=str(session_dir)
            )
            
            logger.info(f"渲染完成，获得 {len(all_image_paths)} 张图片")
            
            # 获取presentation中的所有幻灯片信息，用于确认幻灯片顺序
            ppt_json = self.ppt_manager.get_presentation_json(presentation, include_details=False)
            slides = ppt_json.get("slides", [])
            
            # 建立幻灯片索引与图片路径的映射
            # 假设render_pptx_file返回的图片路径列表顺序与幻灯片索引一致
            for i, image_path in enumerate(all_image_paths):
                # 确认当前索引是否在需要渲染的索引列表中
                if i < len(slides):
                    slide_real_index = slides[i].get("real_index", i)
                    if slide_real_index in slide_indices:
                        slide_image_map[slide_real_index] = image_path
                        logger.info(f"幻灯片 {slide_real_index} 渲染成功: {image_path}")
            
            logger.info(f"成功建立 {len(slide_image_map)}/{len(slide_indices)} 张幻灯片的图片映射")
            return slide_image_map
            
        except Exception as e:
            logger.error(f"渲染幻灯片时出错: {str(e)}")
            return slide_image_map
            
        finally:
            # 无论渲染成功与否，都删除临时PPTX文件
            if temp_pptx_path.exists():
                logger.info(f"删除临时PPTX文件: {temp_pptx_path}")
                temp_pptx_path.unlink()
    
    async def _analyze_with_vision_model(self, image_path: str, slide_elements: List[Dict[str, Any]], 
                                       section_content: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用多模态视觉模型分析幻灯片图像并提供修改建议
        
        Args:
            image_path: 幻灯片图像路径
            slide_elements: 幻灯片元素详细信息
            section_content: 章节内容
            
        Returns:
            分析结果，包含问题、建议和操作指令
        """
        # 检查图像是否存在
        if not os.path.exists(image_path):
            logger.warning(f"图像文件不存在: {image_path}")
            return {
                "has_issues": True, 
                "issues": ["图像文件不存在"], 
                "suggestions": ["重新生成幻灯片预览"]
            }
        
        try:
            # 准备并发送分析请求
            logger.info(f"使用多模态模型分析幻灯片图像: {image_path}")
            
            # 准备上下文数据
            context = {
                "section_json": json.dumps(section_content, ensure_ascii=False, indent=2, cls=EnumEncoder),
                "slide_elements_json": json.dumps(slide_elements, ensure_ascii=False, indent=2, cls=EnumEncoder)
            }
            
            # 渲染提示词
            prompt = self.model_manager.render_template(SLIDE_SELF_VALIDATION_PROMPT, context)
            
            # 调用多模态视觉模型
            response = await self.model_manager.analyze_image(
                model=self.vision_model,
                prompt=prompt,
                image_path=image_path
            )
            
            # 解析响应
            result = self._parse_vision_response(response)
            
            # 记录分析结果
            issues = result.get("issues", [])
            suggestions = result.get("suggestions", [])
            operations = result.get("operations", [])
            
            if issues:
                logger.info(f"多模态模型发现问题: {issues}")
                logger.info(f"修改建议: {suggestions}")
                logger.info(f"修改操作: {len(operations)} 项")
            else:
                logger.info("多模态模型未发现问题")
            
            return result
            
        except Exception as e:
            logger.exception(f"多模态分析过程中出错: {str(e)}")
            return {
                "has_issues": True,
                "issues": ["多模态分析过程中出错"],
                "suggestions": ["检查日志并修复错误"]
            }
    
    def _parse_vision_response(self, response: str) -> Dict[str, Any]:
        """
        解析视觉模型响应
        
        Args:
            response: 视觉模型响应文本
            
        Returns:
            解析后的结果字典
        """
        try:
            # 提取JSON部分
            json_text = response
            if "```json" in response:
                # 提取JSON代码块
                pattern = r"```(?:json)?\s*([\s\S]*?)```"
                matches = re.findall(pattern, response)
                if matches:
                    json_text = matches[0]
            
            # 解析JSON
            result = json.loads(json_text)
            
            # 确保结果有必要的字段
            if not isinstance(result, dict):
                raise ValueError("响应不是有效的JSON对象")
            
            # 添加默认字段
            result.setdefault("has_issues", False)
            result.setdefault("issues", [])
            result.setdefault("suggestions", [])
            result.setdefault("operations", [])
            result.setdefault("quality_score", 0)
            
            return result
            
        except Exception as e:
            logger.error(f"解析视觉模型响应时出错: {str(e)}")
            return {
                "has_issues": True,
                "issues": ["解析响应失败"],
                "suggestions": ["尝试重新生成"],
                "operations": [],
                "quality_score": 0
            }
    
    async def _execute_operations(self, presentation: Any, slide_index: int, operations: List[Dict[str, Any]]) -> bool:
        """
        执行幻灯片操作指令
        
        Args:
            presentation: PPT演示文稿对象
            slide_index: 幻灯片索引
            operations: 操作指令列表
            
        Returns:
            是否成功执行所有操作
        """
        if not operations:
            logger.warning("没有操作指令可执行")
            return False
        
        success_count = 0
        total_count = len(operations)
        
        for operation in operations:
            element_id = operation.get("element_id")
            if not element_id:
                logger.warning(f"跳过缺少element_id的操作: {operation}")
                continue
                
            try:
                # 执行操作
                result = await self._execute_single_operation(presentation, slide_index, operation)
                
                if result.get("success"):
                    success_count += 1
                    logger.info(f"成功执行操作 {operation.get('operation')} 于元素 {element_id}")
                else:
                    logger.warning(f"执行操作 {operation.get('operation')} 失败: {result.get('message')}")
            
            except Exception as e:
                logger.warning(f"执行操作时出错: {str(e)}")
        
        # 计算成功率
        success_rate = success_count / total_count if total_count > 0 else 0
        logger.info(f"操作执行完成，成功率: {success_rate:.2%} ({success_count}/{total_count})")
        
        # 如果有任何操作成功应用，就认为整体成功
        return success_count > 0
    
    async def _execute_single_operation(self, presentation: Any, slide_index: int, operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行单个操作
        
        Args:
            presentation: PPT演示文稿对象
            slide_index: 幻灯片索引
            operation: 操作指令
            
        Returns:
            操作结果
        """
        element_id = operation.get("element_id")
        operation_type = operation.get("operation", "update_element_content")
        content = operation.get("content")
        
        # 根据操作类型执行不同的操作
        if operation_type == "update_element_content":
            # 文本替换操作
            return self.ppt_manager.update_element_content(
                presentation=presentation,
                slide_index=slide_index,
                element_id=element_id,
                new_content=str(content).strip()
            )
        elif operation_type == "adjust_text_font_size":
            # 调整字体大小
            return self.ppt_manager.adjust_text_font_size(
                presentation=presentation,
                slide_index=slide_index,
                element_id=element_id,
                font_size=int(content)
            )
        elif operation_type == "replace_image":
            # 替换图片
            return self.ppt_manager.replace_image(
                presentation=presentation,
                slide_index=slide_index,
                element_id=element_id,
                image_path=content
            )
        elif operation_type == "adjust_element_position":
            # 调整元素位置
            return self.ppt_manager.adjust_element_position(
                presentation=presentation,
                slide_index=slide_index,
                element_id=element_id,
                left=content.get("left"),
                top=content.get("top"),
                width=content.get("width"),
                height=content.get("height")
            )
        elif operation_type == "delete_element":
            # 删除元素
            return self.ppt_manager.delete_element(
                presentation=presentation,
                slide_index=slide_index,
                element_id=element_id
            )
        else:
            logger.warning(f"未知的操作类型: {operation_type}")
            return {"success": False, "message": f"未知的操作类型: {operation_type}"}
    
    def _save_validation_logs(self, log_dir: Path, iteration: int, slide_index: int, 
                            slide_elements: List[Dict[str, Any]], section_content: Dict[str, Any],
                            analysis: Optional[Dict[str, Any]], image_path: Optional[str],
                            phase: str) -> None:
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
            # 记录错误但不中断主要流程 