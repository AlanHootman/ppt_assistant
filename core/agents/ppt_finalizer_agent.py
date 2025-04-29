#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PPT清理与保存Agent模块

负责清理模板幻灯片、整理最终PPT文件并保存输出。
"""

import logging
import os
import datetime
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
            # 检查PPTManager是否已初始化
            if not hasattr(self, 'ppt_manager') or self.ppt_manager is None:
                raise ValueError("PPTManager未初始化")
            
            # 检查是否有已生成的幻灯片
            if not hasattr(state, "generated_slides") or not state.generated_slides:
                error_msg = "没有已生成的幻灯片可供处理"
                self.record_failure(state, error_msg)
                return state
            
            # 检查state中是否有presentation对象
            if not hasattr(state, "presentation") or state.presentation is None:
                error_msg = "状态中缺少presentation对象，无法保存PPT"
                self.record_failure(state, error_msg)
                return state
            
            # 获取presentation对象
            presentation = state.presentation
            
            # 删除未使用的幻灯片（只保留generated_slides中记录的幻灯片）
            self._delete_unused_slides(presentation, state.generated_slides)
            
            # 获取输出目录
            output_dir = state.output_dir if hasattr(state, "output_dir") and state.output_dir else "workspace/output"
            
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 生成输出文件路径
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"presentation_{state.session_id}_{timestamp}.pptx"
            output_path = os.path.join(output_dir, output_filename)
            
            # 使用PPTManager保存演示文稿
            logger.info(f"正在保存演示文稿到: {output_path}")
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
    
    def _delete_template_slides(self, presentation: Any, template_slide_ids: List[str]) -> None:
        """
        删除原始模板幻灯片
        
        Args:
            presentation: PPT演示文稿对象
            template_slide_ids: 模板幻灯片ID列表
        """
        if not self.ppt_manager:
            logger.warning("PPTManager未初始化，无法删除模板幻灯片")
            return
            
        for slide_id in template_slide_ids:
            try:
                result = self.ppt_manager.delete_slide_by_id(presentation, slide_id)
                if result.get("success"):
                    logger.info(f"已删除模板幻灯片: {slide_id}")
                else:
                    logger.warning(f"删除模板幻灯片失败: {slide_id}, 原因: {result.get('message')}")
            except Exception as e:
                logger.warning(f"删除模板幻灯片出错: {slide_id}, 原因: {str(e)}")
    
    def _arrange_slides(self, presentation: Any, slides: List[Dict[str, Any]]) -> None:
        """
        根据索引重新排列幻灯片
        
        Args:
            presentation: PPT演示文稿对象
            slides: 幻灯片列表
        """
        # 此方法可以在未来实现，用于重新排列幻灯片顺序
        pass
    
    def _update_metadata(self, presentation: Any, metadata: Dict[str, Any]) -> None:
        """
        更新PPT元数据
        
        Args:
            presentation: PPT演示文稿对象
            metadata: 元数据字典
        """
        # 此方法可以在未来实现，用于更新PPT的元数据
        pass

    def _delete_unused_slides(self, presentation: Any, generated_slides: List[Dict[str, Any]]) -> None:
        """
        删除未使用的幻灯片，只保留generated_slides中记录的幻灯片
        
        Args:
            presentation: PPT演示文稿对象
            generated_slides: 已生成的幻灯片列表，每个元素包含slide_id
        """
        if not self.ppt_manager:
            logger.warning("PPTManager未初始化，无法删除未使用的幻灯片")
            return
        
        # 提取所有已生成的幻灯片ID
        generated_slide_ids = [slide["slide_id"] for slide in generated_slides]
        logger.info(f"已生成的幻灯片ID: {generated_slide_ids}")
        
        try:
            # 获取演示文稿中的所有幻灯片
            ppt_json = self.ppt_manager.get_presentation_json(presentation, include_details=False)
            all_slides = ppt_json.get("slides", [])
            
            # 找出需要删除的幻灯片ID（不在generated_slide_ids中的）
            slides_to_delete = []
            for slide in all_slides:
                slide_id = slide.get("slide_id")
                if slide_id and slide_id not in generated_slide_ids:
                    slides_to_delete.append(slide_id)
            
            logger.info(f"需要删除的幻灯片ID: {slides_to_delete}")
            
            # 删除未使用的幻灯片
            for slide_id in slides_to_delete:
                try:
                    result = self.ppt_manager.delete_slide_by_id(presentation, slide_id)
                    if result.get("success"):
                        logger.info(f"已删除未使用的幻灯片: {slide_id}")
                    else:
                        logger.warning(f"删除幻灯片失败: {slide_id}, 原因: {result.get('message')}")
                except Exception as e:
                    logger.warning(f"删除幻灯片出错: {slide_id}, 原因: {str(e)}")
        except Exception as e:
            logger.error(f"删除未使用幻灯片过程中发生错误: {str(e)}") 