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
        
        # 初始化进度回调为None
        self.progress_callback = None
        
        logger.info("节点执行器初始化完成")
    
    def set_progress_callback(self, callback):
        """
        设置进度回调函数
        
        Args:
            callback: 回调函数，接受step, progress, description, preview_data参数
        """
        self.progress_callback = callback
        logger.debug("已设置进度回调函数")
    
    def report_progress(self, step: str, progress: int, description: str, preview_data: dict = None):
        """
        报告进度
        
        Args:
            step: 当前步骤
            progress: 进度百分比
            description: 描述信息
            preview_data: 预览数据（可选）
        """
        if self.progress_callback:
            try:
                self.progress_callback(step, progress, description, preview_data)
            except Exception as e:
                logger.error(f"调用进度回调函数失败: {str(e)}")
    
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
            # 反馈错误状态
            self.report_progress(node_name, 0, error_msg, {"error": True})
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
        # 报告进度
        self.report_progress("markdown_parser", 10, "开始解析Markdown内容")
        
        # 检查有效性
        if not state.raw_md:
            error_msg = "缺少原始Markdown内容"
            logger.error(error_msg)
            state.record_failure(error_msg)
            # 反馈错误状态
            self.report_progress("markdown_parser", 0, error_msg, {"error": True})
            return
        
        logger.info("执行Markdown解析节点")
        
        # 尝试从缓存获取解析结果
        cached_result = self.cache_manager.get_markdown_cache(state.raw_md)
        
        if cached_result:
            logger.info("使用缓存的Markdown解析结果")
            state.content_structure = cached_result
            # 添加检查点
            state.add_checkpoint("markdown_parser_completed")
            self.report_progress("markdown_parser", 20, "已从缓存获取Markdown解析结果")
            return
            
        try:
            # 延迟导入以避免循环导入问题
            from core.agents.markdown_agent import MarkdownAgent
            
            # 初始化Markdown解析Agent
            markdown_agent_config = self.config.get("agents", {}).get("markdown_agent", {})
            markdown_agent = MarkdownAgent(markdown_agent_config)
            
            # 执行解析
            self.report_progress("markdown_parser", 15, "正在解析Markdown内容")
            result = await markdown_agent.run(state)
            
            # 检查结果
            if result and result.content_structure:
                logger.info("Markdown解析成功")
                # 更新状态
                state.content_structure = result.content_structure
                
                # 保存到缓存
                self.cache_manager.save_markdown_cache(state.raw_md, state.content_structure)
                
                # 添加检查点并报告进度
                state.add_checkpoint("markdown_parser_completed")
                self.report_progress("markdown_parser", 20, "Markdown解析完成")
            else:
                logger.warning("Markdown解析结果为空")
                state.planning_failed = True
                self.report_progress("markdown_parser", 20, "Markdown解析未能生成有效结果", {"error": True})
                
        except Exception as e:
            error_msg = f"Markdown解析失败: {str(e)}"
            logger.error(error_msg)
            state.record_failure(error_msg)
            # 反馈错误状态
            self.report_progress("markdown_parser", 0, error_msg, {"error": True})
            
    async def _execute_ppt_analyzer(self, state: AgentState) -> None:
        """
        执行PPT模板分析节点
        
        Args:
            state: 当前状态
        """
        # 报告进度
        self.report_progress("ppt_analyzer", 25, "开始分析PPT模板")
        
        # 检查有效性
        if not state.ppt_template_path:
            error_msg = "缺少PPT模板路径"
            logger.error(error_msg)
            state.record_failure(error_msg)
            # 反馈错误状态
            self.report_progress("ppt_analyzer", 0, error_msg, {"error": True})
            return
        
        logger.info("执行PPT模板分析节点")
        
        # 尝试从缓存获取模板分析结果
        cached_result = self.cache_manager.get_ppt_analysis_cache(state.ppt_template_path)
        
        if cached_result:
            logger.info("使用缓存的PPT模板分析结果")
            state.layout_features = cached_result
            # 添加检查点
            state.add_checkpoint("ppt_analyzer_completed")
            self.report_progress("ppt_analyzer", 40, "已从缓存获取PPT模板分析结果")
            return
            
        try:
            # 延迟导入以避免循环导入问题
            from core.agents.ppt_analysis_agent import PPTAnalysisAgent
            
            # 初始化PPT分析Agent
            ppt_agent_config = self.config.get("agents", {}).get("ppt_analysis_agent", {})
            ppt_agent = PPTAnalysisAgent(ppt_agent_config)
            
            # 执行分析
            self.report_progress("ppt_analyzer", 30, "正在分析PPT模板布局特征")
            result = await ppt_agent.run(state)
            
            # 检查结果
            if result and result.layout_features:
                logger.info("PPT模板分析成功")
                # 更新状态
                state.layout_features = result.layout_features
                
                # 保存到缓存
                self.cache_manager.save_ppt_analysis_cache(state.ppt_template_path, state.layout_features)
                
                # 添加检查点
                state.add_checkpoint("ppt_analyzer_completed")
                self.report_progress("ppt_analyzer", 40, "PPT模板分析完成")
            else:
                logger.warning("PPT模板分析结果为空")
                state.planning_failed = True
                self.report_progress("ppt_analyzer", 40, "PPT模板分析未能生成有效结果", {"error": True})
                
        except Exception as e:
            error_msg = f"PPT分析失败: {str(e)}"
            logger.error(error_msg)
            state.record_failure(error_msg)
            # 反馈错误状态
            self.report_progress("ppt_analyzer", 0, error_msg, {"error": True})
            
    async def _execute_content_planner(self, state: AgentState) -> None:
        """
        执行内容规划节点
        
        Args:
            state: 当前状态
        """
        # 报告进度
        self.report_progress("content_planner", 45, "开始规划内容结构")
        
        # 检查有效性
        if not state.content_structure:
            error_msg = "缺少内容结构，无法进行内容规划"
            logger.error(error_msg)
            state.record_failure(error_msg)
            state.planning_failed = True
            # 反馈错误状态
            self.report_progress("content_planner", 0, error_msg, {"error": True})
            return
        
        if not state.layout_features:
            error_msg = "缺少布局特征，无法进行内容规划"
            logger.error(error_msg)
            state.record_failure(error_msg)
            state.planning_failed = True
            # 反馈错误状态
            self.report_progress("content_planner", 0, error_msg, {"error": True})
            return
        
        logger.info("执行内容规划节点")
        
        try:
            # 延迟导入以避免循环导入问题
            from core.agents.content_planning_agent import ContentPlanningAgent
            
            # 初始化内容规划Agent
            planner_config = self.config.get("agents", {}).get("content_planning_agent", {})
            content_planner = ContentPlanningAgent(planner_config)
            
            # 执行内容规划
            self.report_progress("content_planner", 50, "正在根据内容和模板进行规划")
            result = await content_planner.run(state)
            
            # 检查结果
            if result and result.content_plan:
                logger.info("内容规划成功")
                # 更新状态
                state.content_plan = result.content_plan
                
                # 添加检查点
                state.add_checkpoint("content_planner_completed")
                self.report_progress("content_planner", 60, "内容规划完成")
            else:
                logger.warning("内容规划结果为空")
                state.planning_failed = True
                self.report_progress("content_planner", 60, "内容规划未能生成有效结果", {"error": True})
                
        except Exception as e:
            error_msg = f"内容规划失败: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            state.record_failure(error_msg)
            state.planning_failed = True
            # 反馈错误状态
            self.report_progress("content_planner", 0, error_msg, {"error": True})
    
    async def _execute_slide_generator(self, state: AgentState) -> None:
        """
        执行幻灯片生成节点
        
        Args:
            state: 当前状态
        """
        # 报告进度
        self.report_progress("slide_generator", 65, "开始生成幻灯片")
        
        # 检查有效性
        if not state.content_plan:
            error_msg = "缺少内容规划，无法生成幻灯片"
            logger.error(error_msg)
            state.record_failure(error_msg)
            # 反馈错误状态
            self.report_progress("slide_generator", 0, error_msg, {"error": True})
            return
        
        logger.info("执行幻灯片生成节点")
        
        try:
            # 延迟导入以避免循环导入问题
            from core.agents.slide_generator_agent import SlideGeneratorAgent
            
            # 初始化幻灯片生成Agent
            generator_config = self.config.get("agents", {}).get("slide_generator_agent", {})
            slide_generator = SlideGeneratorAgent(generator_config)
            
            # 执行幻灯片生成
            self.report_progress("slide_generator", 70, "正在创建幻灯片")
            result = await slide_generator.run(state)
            
            # 更新状态
            if result:
                # 添加检查点
                state.add_checkpoint("slide_generator_completed")
                self.report_progress("slide_generator", 80, "幻灯片生成完成")
                
        except Exception as e:
            error_msg = f"幻灯片生成失败: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            state.record_failure(error_msg)
            # 反馈错误状态
            self.report_progress("slide_generator", 0, error_msg, {"error": True})
    
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
            # 反馈错误状态
            self.report_progress("next_slide_or_end", 0, error_msg, {"error": True})
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
        执行PPT完善节点
        
        Args:
            state: 当前状态
        """
        # 报告进度
        self.report_progress("ppt_finalizer", 85, "开始完善PPT文件")
        
        logger.info("执行PPT完善节点")
        
        try:
            # 延迟导入以避免循环导入问题
            from core.agents.ppt_finalizer_agent import PPTFinalizerAgent
            
            # 初始化PPT完善Agent
            finalizer_config = self.config.get("agents", {}).get("ppt_finalizer_agent", {})
            ppt_finalizer = PPTFinalizerAgent(finalizer_config)
            
            # 执行PPT完善
            self.report_progress("ppt_finalizer", 90, "正在优化和完善PPT")
            result = await ppt_finalizer.run(state)
            
            # 更新状态
            if result and result.output_ppt_path:
                logger.info(f"PPT完善成功，输出文件: {result.output_ppt_path}")
                # 添加检查点
                state.add_checkpoint("ppt_finalizer_completed")
                self.report_progress("ppt_finalizer", 95, "PPT完善完成")
                
        except Exception as e:
            error_msg = f"PPT完善失败: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            state.record_failure(error_msg)
            # 反馈错误状态
            self.report_progress("ppt_finalizer", 0, error_msg, {"error": True}) 