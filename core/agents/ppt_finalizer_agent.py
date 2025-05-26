#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PPT清理与保存Agent模块

负责清理模板幻灯片、整理最终PPT文件并保存输出。
"""

import logging
import os
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from core.agents.base_agent import BaseAgent
from core.engine.state import AgentState
from core.llm.model_manager import ModelManager
from core.utils.model_helper import ModelHelper
from core.utils.ppt_agent_helper import PPTAgentHelper
from core.utils.ppt_operations import PPTOperationExecutor
from core.utils.slide_cleanup_manager import SlideCleanupManager
from core.utils.slide_validation_manager import SlideValidationManager
from config.settings import settings

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
        
        # 初始化模型管理器和模型辅助工具
        self.model_manager = ModelManager()
        self.model_helper = ModelHelper(self.model_manager)
        
        # 获取模型配置
        model_config = self.model_helper.get_model_config(config, "vision")
        self.vision_model = model_config.get("model")
        self.temperature = model_config.get("temperature")
        self.max_tokens = model_config.get("max_tokens")
        
        # 验证迭代相关配置
        self.max_iterations = config.get("max_iterations", settings.MAX_SLIDE_ITERATIONS)
        
        # 视觉模型重试相关配置
        self.max_vision_retries = int(config.get("max_vision_retries", settings.MAX_VISION_RETRIES))
        
        # 初始化PPT管理器
        self.ppt_manager = PPTAgentHelper.init_ppt_manager()
        if not self.ppt_manager:
            raise ImportError("无法初始化PPT管理器，请确保PPT Manager已正确安装")
        
        # 初始化PPT操作执行器
        self.ppt_operation_executor = PPTOperationExecutor(
            ppt_manager=self.ppt_manager,
            agent_name="PPTFinalizerAgent"
        )
        
        # 创建验证日志目录
        self.validation_logs_dir = settings.LOG_DIR / "slide_validation"
        self.validation_logs_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化幻灯片清理管理器
        self.slide_cleanup_manager = SlideCleanupManager(self.ppt_manager)
        
        # 初始化幻灯片验证管理器
        self.slide_validation_manager = SlideValidationManager(
            ppt_manager=self.ppt_manager,
            ppt_operation_executor=self.ppt_operation_executor,
            model_manager=self.model_manager,
            model_helper=self.model_helper,
            vision_model=self.vision_model,
            max_iterations=self.max_iterations,
            max_vision_retries=self.max_vision_retries,
            validation_logs_dir=self.validation_logs_dir
        )
        
        logger.info(f"初始化PPTFinalizerAgent，使用模型: {self.vision_model}, 最大迭代次数: {self.max_iterations}, 视觉模型最大重试次数: {self.max_vision_retries}")
    
    async def run(self, state: AgentState) -> AgentState:
        """
        执行PPT清理、验证与保存
        
        主要职责：
        1. 删除未使用的模板幻灯片
        2. 根据内容计划重新排序幻灯片
        3. 对所有幻灯片进行质量验证和优化
        4. 保存最终PPT文件
        
        Args:
            state: 当前工作流状态，包含生成的幻灯片信息和演示文稿对象
            
        Returns:
            更新后的状态，包含最终PPT文件路径和验证结果
        """
        logger.info("开始清理、验证和保存PPT")
        
        try:
            # 步骤1：准备必要资源
            resources = await self._prepare_resources(state)
            if not resources:
                return state
            
            presentation, generated_slides, content_plan = resources
            
            # 步骤2：清理和排序幻灯片
            await self._process_slides(state, presentation, generated_slides, content_plan)
            
            # 步骤3：验证和优化幻灯片
            validated_slides = await self._validate_slides(state, presentation, generated_slides, content_plan)
            
            # 步骤4：保存最终PPT文件
            await self._save_presentation(state, presentation, validated_slides)
            
            # 记录检查点，标记完成
            self.add_checkpoint(state)
            
        except Exception as e:
            # 错误处理：记录异常并更新状态
            error_msg = f"PPT清理与保存失败: {str(e)}"
            logger.error(error_msg)
            logger.exception(e)
            self.record_failure(state, error_msg)
        
        return state
        
    async def _prepare_resources(self, state: AgentState) -> Optional[Tuple[Any, List[Dict[str, Any]], List[Dict[str, Any]]]]:
        """
        准备必要的资源，包括演示文稿对象、已生成的幻灯片列表和内容计划
        
        Args:
            state: 当前工作流状态
            
        Returns:
            如果准备成功，返回(presentation, generated_slides, content_plan)元组；
            如果失败，返回None
        """
        # 获取演示文稿对象
        presentation = getattr(state, "presentation", None)
        if not presentation:
            error_msg = "找不到presentation对象，无法保存PPT"
            logger.error(error_msg)
            state.record_failure(error_msg)
            return None
                
        # 获取已生成的幻灯片列表
        generated_slides = getattr(state, "generated_slides", [])
        logger.info(f"获取到已生成的幻灯片列表: {len(generated_slides)} 张")
            
        # 提取幻灯片索引用于日志记录和调试
        slide_indices = [slide.get("slide_index") for slide in generated_slides if slide.get("slide_index") is not None]
        logger.info(f"幻灯片索引列表: {slide_indices}")
            
        # 获取内容计划
        content_plan = getattr(state, "content_plan", [])
        if not content_plan:
            logger.warning("找不到content_plan，将跳过幻灯片排序和内容验证")
        return None
            
        return presentation, generated_slides, content_plan
    
    async def _process_slides(self, state: AgentState, presentation: Any, 
                           generated_slides: List[Dict[str, Any]], 
                           content_plan: List[Dict[str, Any]]) -> None:
        """
        处理幻灯片，包括删除未使用的幻灯片和重新排序
        
        Args:
            state: 当前工作流状态
            presentation: 演示文稿对象
            generated_slides: 已生成的幻灯片列表
            content_plan: 内容计划
        """
        # 删除未使用的幻灯片（只保留generated_slides中记录的幻灯片）
        logger.info("删除未使用的模板幻灯片")
        self.slide_cleanup_manager.delete_unused_slides(presentation, generated_slides)
            
        # 重新排序幻灯片
        logger.info("根据content_plan重新排序幻灯片")
        self.slide_cleanup_manager.reorder_slides(presentation, content_plan)
    
    async def _validate_slides(self, state: AgentState, presentation: Any, 
                            generated_slides: List[Dict[str, Any]], 
                            content_plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        验证幻灯片质量并进行优化
        
        Args:
            state: 当前工作流状态
            presentation: 演示文稿对象
            generated_slides: 已生成的幻灯片列表
            content_plan: 内容计划
            
        Returns:
            验证后的幻灯片列表
        """
        # 生成所有幻灯片截图并进行质量验证
        validated_slides = await self.slide_validation_manager.validate_all_slides(
            state, presentation, generated_slides, content_plan, self.slide_cleanup_manager
        )
        logger.info(f"完成 {len(validated_slides)}/{len(generated_slides)} 张幻灯片的质量验证")
        
        return validated_slides
    
    async def _save_presentation(self, state: AgentState, presentation: Any, 
                              validated_slides: List[Dict[str, Any]]) -> None:
        """
        保存最终的演示文稿
        
        Args:
            state: 当前工作流状态
            presentation: 演示文稿对象
            validated_slides: 验证后的幻灯片列表
        """
        # 获取或创建输出目录
        output_dir = getattr(state, "output_dir", "workspace/output")
        os.makedirs(output_dir, exist_ok=True)
            
        # 生成带有时间戳的输出文件名
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
            
    def add_checkpoint(self, state: AgentState) -> None:
        """
        添加工作流检查点
        
        Args:
            state: 工作流状态
        """
        state.add_checkpoint("ppt_finalizer_completed")
        logger.info("添加检查点: ppt_finalizer_completed")
    
    def record_failure(self, state: AgentState, error: str) -> None:
        """
        记录失败信息
        
        Args:
            state: 工作流状态
            error: 错误信息
        """
        state.record_failure(error)
        logger.error(f"记录失败: {error}") 