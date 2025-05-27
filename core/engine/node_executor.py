"""
节点执行器模块
"""
import logging
import traceback
import json
import hashlib
from typing import Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime
from pathlib import Path

from core.engine.state import AgentState
from core.engine.mocks import WorkflowMocks
from core.engine.cache_manager import CacheManager
from config.settings import settings

logger = logging.getLogger(__name__)

class NodeExecutor:
    """负责执行工作流中的各个节点"""

    def __init__(self, config: Dict[str, Any], tracker: Optional[Any] = None, enable_tracking: bool = False):
        """
        初始化节点执行器
        
        Args:
            config: 工作流配置
            tracker: 跟踪器实例（可选）
            enable_tracking: 是否启用跟踪
        """
        self.config = config
        self.tracker = tracker
        self.enable_tracking = enable_tracking
        
        # 初始化缓存管理器
        self.cache_manager = CacheManager()
        
        # 记录执行日志
        self.execution_logs = []
        
        logger.info("节点执行器初始化完成")
    
    async def _execute_node(self, node_name: str, state: AgentState, use_mock: bool = False) -> None:
        """
        执行节点
        
        Args:
            node_name: 节点名称
            state: 当前状态
            use_mock: 是否使用模拟实现
        """
        logger.info(f"执行节点: {node_name}")
        state.current_node = node_name
        
        # 记录执行信息
        self._record_execution(node_name, state.session_id)
                
        try:
            # 根据节点名称调用相应的执行函数
            if node_name == "markdown_parser":
                await self._execute_markdown_parser(state)
            elif node_name == "ppt_analyzer":
                await self._execute_ppt_analyzer(state) 
            elif node_name == "content_planner":
                await self._execute_content_planner(state)
            elif node_name == "slide_generator":
                await self._execute_slide_generator(state)
            elif node_name == "next_slide_or_end":
                await self._execute_next_slide_or_end(state)
            elif node_name == "ppt_finalizer":
                await self._execute_ppt_finalizer(state)
            else:
                logger.warning(f"未知节点: {node_name}，将使用模拟实现")
                # 对于未知节点，使用WorkflowMocks中的处理函数
                mock_handler = WorkflowMocks.create_placeholder_node(node_name)
                mock_handler(state)
        except Exception as e:
            error_msg = f"执行节点 {node_name} 失败: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            state.record_failure(error_msg)
            raise
    
    async def _execute_and_validate_node(self, node_name: str, state: AgentState, 
                                       check_item: Optional[str] = None, 
                                       error_message: Optional[str] = None,
                                       use_mock: bool = False) -> Optional[Dict[str, Any]]:
        """
        执行节点并验证结果
        
        Args:
            node_name: 节点名称
            state: 当前状态
            check_item: 需要检查的状态属性(如果不需要验证则为None)
            error_message: 条件不满足时的错误消息
            use_mock: 是否使用模拟实现
            
        Returns:
            如果条件不满足返回错误响应，否则返回None
        """
        # 执行节点
        await self._execute_node(node_name, state, use_mock)
        
        # 如果需要验证结果
        if check_item and error_message:
            return self._check_state_condition(state, check_item, error_message)
        
        return None
    
    def _check_state_condition(self, state: AgentState, check_item: str, error_message: str) -> Optional[Dict[str, Any]]:
        """
        检查状态条件并处理错误情况
        
        Args:
            state: 当前状态
            check_item: 需要检查的状态属性
            error_message: 条件不满足时的错误消息
            
        Returns:
            如果条件不满足返回错误响应，否则返回None
        """
        if not getattr(state, check_item, None):
            logger.error(error_message)
            state.record_failure(error_message)
            
            # 结束MLflow跟踪，标记为失败
            if self.enable_tracking and self.tracker:
                self.tracker.end_workflow_run("FAILED")
                
            return {
                "error": error_message,
                "session_id": state.session_id,
                "timestamp": datetime.now().isoformat()
            }
        return None
    
    def _record_execution(self, node_name: str, session_id: str):
        """
        记录执行信息
        
        Args:
            node_name: 节点名称
            session_id: 会话ID
        """
        record = {
            "timestamp": datetime.now().isoformat(),
            "node": node_name,
            "session_id": session_id
        }
        self.execution_logs.append(record)
        logger.debug(f"执行节点: {node_name}, 会话: {session_id}")
    
    async def _execute_markdown_parser(self, state: AgentState) -> None:
        """
        执行Markdown解析节点
        
        Args:
            state: 当前状态
        """
        # 检查有效性
        if not state.raw_md:
            error_msg = "缺少原始Markdown内容"
            logger.error(error_msg)
            state.record_failure(error_msg)
            return
        
        logger.info("执行Markdown解析节点")
        
        # 尝试从缓存获取解析结果
        cached_result = self.cache_manager.get_markdown_cache(state.raw_md)
        
        if cached_result:
            logger.info("使用缓存的Markdown解析结果")
            state.content_structure = cached_result
            # 添加检查点
            state.add_checkpoint("markdown_parser_completed")
            return
            
        try:
            # 延迟导入以避免循环导入问题
            from core.agents.markdown_agent import MarkdownAgent
            
            # 初始化Markdown解析Agent
            markdown_agent_config = self.config.get("agents", {}).get("markdown_agent", {})
            markdown_agent = MarkdownAgent(markdown_agent_config)
            
            # 执行解析
            result = await markdown_agent.run(state)
            
            # 检查结果
            if result and result.content_structure:
                logger.info("Markdown解析成功")
                # 更新状态
                state.content_structure = result.content_structure
                
                # 保存到缓存
                self.cache_manager.save_markdown_cache(state.raw_md, state.content_structure)
                
        except Exception as e:
            error_msg = f"Markdown解析失败: {str(e)}"
            logger.error(error_msg)
            state.record_failure(error_msg)
            
    async def _execute_ppt_analyzer(self, state: AgentState) -> None:
        """
        执行PPT分析节点
        
        Args:
            state: 当前状态
        """
        # 检查有效性
        if not state.ppt_template_path:
            error_msg = "缺少PPT模板路径"
            logger.error(error_msg)
            state.record_failure(error_msg)
            return
        
        logger.info(f"执行PPT分析节点，模板路径: {state.ppt_template_path}")
        
        # 尝试从缓存获取分析结果
        cached_result = self.cache_manager.get_ppt_analysis_cache(state.ppt_template_path)
        
        if cached_result:
            logger.info("使用缓存的PPT分析结果")
            state.layout_features = cached_result
            # 添加检查点
            state.add_checkpoint("ppt_analyzer_completed")
            return
            
        try:
            # 延迟导入以避免循环导入问题
            from core.agents.ppt_analysis_agent import PPTAnalysisAgent
            
            # 初始化PPT分析Agent
            ppt_analysis_agent_config = self.config.get("agents", {}).get("ppt_analysis_agent", {})
            ppt_analysis_agent = PPTAnalysisAgent(ppt_analysis_agent_config)
            
            # 执行分析
            result = await ppt_analysis_agent.run(state)
            
            # 检查结果
            if result and result.layout_features:
                logger.info("PPT分析成功")
                # 保存到缓存
                self.cache_manager.save_ppt_analysis_cache(state.ppt_template_path, result.layout_features)
                
        except Exception as e:
            error_msg = f"PPT分析失败: {str(e)}"
            logger.error(error_msg)
            state.record_failure(error_msg)
            
    async def _execute_content_planner(self, state: AgentState) -> None:
        """
        执行内容规划节点
        
        Args:
            state: 当前状态
        """
        # 检查依赖
        if not state.content_structure:
            error_msg = "缺少Markdown解析结果"
            logger.error(error_msg)
            state.record_failure(error_msg)
            return
            
        if not state.layout_features:
            error_msg = "缺少PPT模板分析结果"
            logger.error(error_msg)
            state.record_failure(error_msg)
            return
        
        logger.info("执行内容规划节点")
        
        # 尝试从缓存获取规划结果
        cache_key = f"{hash(str(state.content_structure))}-{hash(str(state.layout_features))}"
        cached_result = self.cache_manager.get_content_plan_cache(
            state.content_structure,
            state.layout_features
        )
        
        if cached_result:
            logger.info("使用缓存的内容规划结果")
            state.planned_content = cached_result
            state.current_slide_index = 0
            # 添加检查点
            state.add_checkpoint("content_planner_completed")
            return
            
        try:
            # 延迟导入以避免循环导入问题
            from core.agents.content_planning_agent import ContentPlanningAgent
            
            # 初始化内容规划Agent
            content_planning_agent_config = self.config.get("agents", {}).get("content_planning_agent", {})
            content_planning_agent = ContentPlanningAgent(content_planning_agent_config)
            
            # 执行规划
            result = await content_planning_agent.run(state)
            
            # 检查结果
            if result and result.planned_content:
                logger.info("内容规划成功")
                # 初始化幻灯片索引
                state.current_slide_index = 0
                
                # 保存到缓存
                self.cache_manager.save_content_plan_cache(
                    state.content_structure,
                    state.layout_features,
                    result.planned_content
                )
                
        except Exception as e:
            error_msg = f"内容规划失败: {str(e)}"
            logger.error(error_msg)
            state.record_failure(error_msg)
            
    async def _execute_slide_generator(self, state: AgentState) -> None:
        """
        执行幻灯片生成节点
        
        Args:
            state: 当前状态
        """
        # 检查依赖
        if not state.planned_content:
            error_msg = "缺少内容规划结果"
            logger.error(error_msg)
            state.record_failure(error_msg)
            return
            
        if state.current_slide_index is None or state.current_slide_index >= len(state.planned_content.get("slides", [])):
            error_msg = "无效的幻灯片索引"
            logger.error(error_msg)
            state.record_failure(error_msg)
            return
        
        current_index = state.current_slide_index
        total_slides = len(state.planned_content.get("slides", []))
        logger.info(f"执行幻灯片生成节点: 第 {current_index+1}/{total_slides} 张幻灯片")
        
        try:
            # 延迟导入以避免循环导入问题
            from core.agents.slide_generator_agent import SlideGeneratorAgent
            
            # 初始化幻灯片生成Agent
            slide_generator_config = self.config.get("agents", {}).get("slide_generator_agent", {})
            slide_generator_agent = SlideGeneratorAgent(slide_generator_config)
            
            # 执行生成
            result = await slide_generator_agent.run(state)
            
            # 检查结果
            if result:
                logger.info(f"幻灯片 {current_index+1}/{total_slides} 生成成功")
                
        except Exception as e:
            error_msg = f"幻灯片生成失败: {str(e)}"
            logger.error(error_msg)
            state.record_failure(error_msg)
            
    async def _execute_next_slide_or_end(self, state: AgentState) -> None:
        """
        执行下一张幻灯片或结束决策节点
        
        Args:
            state: 当前状态
        """
        # 检查依赖
        if state.current_slide_index is None or not state.planned_content:
            error_msg = "无效的状态，缺少幻灯片索引或内容规划"
            logger.error(error_msg)
            state.record_failure(error_msg)
            return
        
        total_slides = len(state.planned_content.get("slides", []))
        current_index = state.current_slide_index
        
        # 检查是否所有幻灯片都已生成
        if current_index >= total_slides - 1:
            logger.info(f"所有幻灯片 ({total_slides} 张) 已生成完成，准备进入最终整合阶段")
            state.add_checkpoint("all_slides_generated")
            return
        
        # 还有更多幻灯片需要生成，增加索引
        state.current_slide_index += 1
        next_index = state.current_slide_index
        logger.info(f"准备生成下一张幻灯片: {next_index + 1}/{total_slides}")
        
    async def _execute_ppt_finalizer(self, state: AgentState) -> None:
        """
        执行PPT最终整合节点
        
        Args:
            state: 当前状态
        """
        # 检查依赖
        if not state.slides_content or not state.ppt_template_path:
            error_msg = "缺少幻灯片内容或模板路径"
            logger.error(error_msg)
            state.record_failure(error_msg)
            return
            
        logger.info("执行PPT最终整合节点")
        
        try:
            # 延迟导入以避免循环导入问题
            from core.agents.ppt_finalizer_agent import PPTFinalizerAgent
            
            # 初始化PPT整合Agent
            ppt_finalizer_config = self.config.get("agents", {}).get("ppt_finalizer_agent", {})
            ppt_finalizer_agent = PPTFinalizerAgent(ppt_finalizer_config)
            
            # 执行整合
            result = await ppt_finalizer_agent.run(state)
            
            # 检查结果
            if result and result.output_ppt_path:
                logger.info(f"PPT整合成功，输出路径: {result.output_ppt_path}")
                
        except Exception as e:
            error_msg = f"PPT整合失败: {str(e)}"
            logger.error(error_msg)
            state.record_failure(error_msg) 