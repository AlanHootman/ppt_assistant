#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
幻灯片清理管理器模块

负责处理幻灯片的删除、排序等操作
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

class SlideCleanupManager:
    """幻灯片清理管理器，负责处理幻灯片的删除和排序操作"""
    
    def __init__(self, ppt_manager):
        """
        初始化幻灯片清理管理器
        
        Args:
            ppt_manager: PPT管理器实例
        """
        self.ppt_manager = ppt_manager
    
    def delete_unused_slides(self, presentation: Any, generated_slides: List[Dict[str, Any]]) -> None:
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
    
    def reorder_slides(self, presentation: Any, content_plan: List[Dict[str, Any]]) -> None:
        """
        根据content_plan中的page_number信息重新排序幻灯片
        
        Args:
            presentation: PPT演示文稿对象
            content_plan: 内容规划列表，每个元素包含slide_id和page_number
        """
        if not self.ppt_manager:
            logger.warning("PPTManager未初始化，无法重新排序幻灯片")
            return
        
        # 获取slide_id到page_number的映射关系
        slide_id_to_page = self._get_slide_id_to_page_mapping(content_plan)
        if not slide_id_to_page:
            return
            
        # 获取当前幻灯片索引到slide_id的映射关系
        current_slides = self._get_current_slides_mapping(presentation)
        if not current_slides:
            return
                
        # 生成幻灯片移动计划
        move_operations = self._generate_slide_move_operations(current_slides, slide_id_to_page)
        
        # 执行移动操作
        self._execute_slide_move_operations(presentation, move_operations)
    
    def _get_slide_id_to_page_mapping(self, content_plan: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        从内容规划中提取slide_id到page_number的映射关系
        
        Args:
            content_plan: 内容规划列表
            
        Returns:
            slide_id到page_number的映射字典
        """
        slide_id_to_page = {}
        for slide_info in content_plan:
            slide_id = slide_info.get("slide_id")
            page_number = slide_info.get("page_number")
            if slide_id and page_number is not None:
                slide_id_to_page[slide_id] = page_number
        
        if not slide_id_to_page:
            logger.warning("内容规划中没有找到有效的slide_id和page_number映射")
        else:
            logger.info(f"获取到slide_id到page_number的映射: {slide_id_to_page}")
            
        return slide_id_to_page
    
    def _get_current_slides_mapping(self, presentation: Any) -> Dict[int, str]:
        """
        获取当前演示文稿中幻灯片索引到slide_id的映射
        
        Args:
            presentation: PPT演示文稿对象
            
        Returns:
            幻灯片索引到slide_id的映射字典
        """
        current_slides = {}
        try:
            # 获取演示文稿JSON结构
            ppt_json = self.ppt_manager.get_presentation_json(presentation, include_details=False)
            slides_count = len(ppt_json.get("slides", []))
            
            # 遍历所有幻灯片，从备注中提取slide_id
            for slide_index in range(slides_count):
                slide_id = self._extract_slide_id_from_notes(presentation, slide_index)
                if slide_id:
                    current_slides[slide_index] = slide_id
                    logger.info(f"幻灯片索引 {slide_index} 对应的slide_id: {slide_id}")
            
            # 检查是否找到了足够的幻灯片
            if not current_slides:
                logger.warning("未在幻灯片备注中找到任何slide_id信息，无法进行排序")
            
            return current_slides
                
        except Exception as e:
            logger.error(f"获取当前幻灯片映射时出错: {str(e)}")
            return {}
    
    def _extract_slide_id_from_notes(self, presentation: Any, slide_index: int) -> Optional[str]:
        """
        从幻灯片备注中提取slide_id
        
        Args:
            presentation: PPT演示文稿对象
            slide_index: 幻灯片索引
            
        Returns:
            提取的slide_id，如果未找到则返回None
        """
        # 获取幻灯片备注
        notes_result = self.ppt_manager.get_slide_notes(presentation, slide_index)
        if not notes_result.get("success") or not notes_result.get("notes"):
            return None
            
        notes = notes_result.get("notes", "")
        # 使用正则表达式匹配slide_id
        match = re.search(r"slide_id:\s*(slide_\d+)", notes)
        if match:
            return match.group(1)
        return None
    
    def _generate_slide_move_operations(
        self, current_slides: Dict[int, str], slide_id_to_page: Dict[str, int]
    ) -> List[Tuple[int, int]]:
        """
        生成幻灯片移动操作计划
        
        Args:
            current_slides: 当前幻灯片索引到slide_id的映射
            slide_id_to_page: slide_id到目标页码的映射
            
        Returns:
            移动操作列表，每个元素为(源索引, 目标索引)元组
        """
        moves = []
        for current_index, slide_id in current_slides.items():
            if slide_id in slide_id_to_page:
                target_index = slide_id_to_page[slide_id]
                moves.append((current_index, target_index))
        
        # 按目标索引排序，确保移动操作的正确性
        moves.sort(key=lambda x: x[1])
        return moves
    
    def _execute_slide_move_operations(self, presentation: Any, move_operations: List[Tuple[int, int]]) -> None:
        """
        执行幻灯片移动操作
        
        Args:
            presentation: PPT演示文稿对象
            move_operations: 移动操作列表，每个元素为(源索引, 目标索引)元组
        """
        for source_index, target_index in move_operations:
            try:
                result = self.ppt_manager.move_slide(presentation, source_index, target_index)
                if result.get("success"):
                    logger.info(f"成功将幻灯片从索引 {source_index} 移动到 {target_index}")
                else:
                    logger.warning(f"移动幻灯片失败: {result.get('message')}")
            except Exception as e:
                logger.error(f"移动幻灯片时出错: {str(e)}")
    
    def build_current_slide_mapping(self, presentation: Any) -> Dict[int, str]:
        """
        建立当前演示文稿中位置索引到slide_id的映射
        
        Args:
            presentation: 演示文稿对象
            
        Returns:
            位置索引到slide_id的映射字典
        """
        current_mapping = {}
        try:
            # 获取演示文稿JSON结构
            ppt_json = self.ppt_manager.get_presentation_json(presentation, include_details=False)
            slides_count = len(ppt_json.get("slides", []))
            
            # 遍历所有当前位置，从备注中提取slide_id
            for position in range(slides_count):
                slide_id = self._extract_slide_id_from_notes(presentation, position)
                if slide_id:
                    current_mapping[position] = slide_id
                    logger.debug(f"当前位置 {position} 对应的slide_id: {slide_id}")
            
            logger.info(f"建立了当前幻灯片映射: {current_mapping}")
            return current_mapping
                
        except Exception as e:
            logger.error(f"建立当前幻灯片映射时出错: {str(e)}")
            return {}
    
    def get_section_content_by_slide_id(self, slide_id: str, content_plan: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        根据slide_id获取对应的章节内容
        
        Args:
            slide_id: 幻灯片ID
            content_plan: 内容规划列表
            
        Returns:
            章节内容，如果找不到则返回None
        """
        for section in content_plan:
            if section.get("slide_id") == slide_id:
                return section
        
        logger.warning(f"无法找到slide_id为 {slide_id} 的章节内容")
        return None 