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

class PPTFinalizerAgent(BaseAgent):
    """PPT清理与保存Agent，负责最终PPT的处理与输出"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化PPT清理与保存Agent
        
        Args:
            config: Agent配置
        """
        super().__init__(config)
        # 实际应该引入PPT管理器
        # from libs.ppt_manager import PPTManager
        # self.ppt_manager = PPTManager()
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
        
        # 检查是否有已生成的幻灯片
        if not hasattr(state, "generated_slides") or not state.generated_slides:
            error_msg = "没有已生成的幻灯片可供处理"
            self.record_failure(state, error_msg)
            return state
        
        try:
            # 获取输出目录
            output_dir = state.output_dir
            if not output_dir:
                # 默认使用工作区中的output目录
                output_dir = os.path.join("workspace", "output")
            
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 生成输出文件路径
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"presentation_{state.session_id}_{timestamp}.pptx"
            output_path = os.path.join(output_dir, output_filename)
            
            # 在实际实现中，这里应该使用PPT管理器进行幻灯片处理
            # 现在使用模拟方法
            self._mock_finalize_ppt(state, output_path)
            
            # 更新状态
            state.output_ppt_path = output_path
            
            logger.info(f"PPT已保存: {output_path}")
            
            # 记录检查点
            self.add_checkpoint(state)
            
        except Exception as e:
            error_msg = f"PPT清理与保存失败: {str(e)}"
            self.record_failure(state, error_msg)
        
        return state
    
    def _mock_finalize_ppt(self, state: AgentState, output_path: str) -> None:
        """
        模拟PPT清理与保存过程
        
        Args:
            state: 工作流状态
            output_path: 输出文件路径
        """
        # 记录处理信息
        logger.info(f"模拟PPT处理，生成文件: {output_path}")
        
        # 获取已生成的幻灯片
        slides = state.generated_slides
        
        # 创建日志文件以记录处理过程
        log_path = f"{output_path}.log"
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"PPT处理时间: {datetime.datetime.now()}\n")
            f.write(f"会话ID: {state.session_id}\n")
            f.write(f"幻灯片数量: {len(slides)}\n")
            f.write("\n幻灯片列表:\n")
            
            for i, slide in enumerate(slides):
                slide_id = slide.get("slide_id", f"未知_{i}")
                content_summary = str(slide.get("content", {}))[:100] + "..."
                f.write(f"{i+1}. {slide_id}: {content_summary}\n")
        
        # 创建一个空文件表示输出的PPT
        with open(output_path, "w") as f:
            f.write(f"# 模拟PPT文件 - {datetime.datetime.now()}\n")
            f.write(f"# 包含 {len(slides)} 张幻灯片\n")
        
        logger.info(f"已保存处理日志: {log_path}")
    
    def _delete_template_slides(self, template_slide_ids: List[str]) -> None:
        """
        删除原始模板幻灯片
        
        Args:
            template_slide_ids: 模板幻灯片ID列表
        """
        # 在实际实现中，应该调用PPT管理器删除原始模板幻灯片
        pass
    
    def _arrange_slides(self, slides: List[Dict[str, Any]]) -> None:
        """
        根据索引重新排列幻灯片
        
        Args:
            slides: 幻灯片列表
        """
        # 在实际实现中，应该调用PPT管理器重新排列幻灯片
        pass
    
    def _update_metadata(self, metadata: Dict[str, Any]) -> None:
        """
        更新PPT元数据
        
        Args:
            metadata: 元数据字典
        """
        # 在实际实现中，应该调用PPT管理器更新文档属性
        pass 