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
from typing import Dict, Any, List, Optional

from core.agents.base_agent import BaseAgent
from core.engine.state import AgentState

logger = logging.getLogger(__name__)

# 导入PPT管理器
try:
    from interfaces.ppt_api import PPTManager
except ImportError:
    logger = logging.getLogger(__name__)
    logger.error("无法导入PPTManager，请确保ppt_manager库已正确安装")
    PPTManager = None

class PPTFinalizerAgent(BaseAgent):
    """PPT清理与保存Agent，负责最终PPT的处理与输出"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化PPT清理与保存Agent
        
        Args:
            config: Agent配置
        """
        super().__init__(config)
        
        # 初始化PPTManager
        try:
            from interfaces.ppt_api import PPTManager
            self.ppt_manager = PPTManager()
            logger.info("成功初始化PPT管理器")
        except ImportError as e:
            logger.error(f"无法导入PPTManager: {str(e)}")
            self.ppt_manager = None
        
        logger.info(f"初始化PPTFinalizerAgent")
    
    async def run(self, state: AgentState) -> AgentState:
        """
        执行PPT清理与保存
        
        Args:
            state: 当前工作流状态
            
        Returns:
            更新后的状态
        """
        logger.info("开始清理和保存PPT")
        
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
                logger.warning("找不到content_plan，将跳过幻灯片排序")

            # 1. 删除未使用的幻灯片（只保留generated_slides中记录的幻灯片）
            logger.info("删除未使用的模板幻灯片")
            self._delete_unused_slides(presentation, generated_slides)
            
            # 2. 重新排序幻灯片
            if content_plan:
                logger.info("根据content_plan重新排序幻灯片")
                self._reorder_slides(presentation, content_plan)

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