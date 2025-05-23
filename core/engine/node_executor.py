"""
节点执行器模块
"""
import logging
import traceback
import json
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from core.engine.state import AgentState
from core.engine.mocks import WorkflowMocks
from core.engine.cache_manager import CacheManager
from core.agents.markdown_agent import MarkdownAgent
from core.agents.ppt_analysis_agent import PPTAnalysisAgent
from core.agents.content_planning_agent import ContentPlanningAgent
from core.agents.slide_generator_agent import SlideGeneratorAgent
from core.agents.ppt_finalizer_agent import PPTFinalizerAgent
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
        
        # 从状态中获取markdown文件路径（可能是从命令行参数传递的）
        md_file_path = state.markdown_path if hasattr(state, 'markdown_path') else None
        
        # 尝试从缓存获取解析结果
        cached_result = self.cache_manager.get_markdown_cache(state.raw_md, md_file_path)
        
        if cached_result:
            logger.info("使用缓存的Markdown解析结果")
            state.content_structure = cached_result
            # 添加检查点
            state.add_checkpoint("markdown_parser_completed")
            return
            
        try:
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
                self.cache_manager.save_markdown_cache(state.raw_md, state.content_structure, md_file_path)
                
                # 添加检查点
                state.add_checkpoint("markdown_parser_completed")
            else:
                error_msg = "Markdown解析失败，未生成内容结构"
                logger.error(error_msg)
                state.record_failure(error_msg)
        except Exception as e:
            error_msg = f"Markdown解析异常: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            state.record_failure(error_msg)
    
    async def _execute_slide_generator(self, state: AgentState) -> None:
        """
        执行幻灯片生成节点
        
        Args:
            state: 当前状态
        """
        logger.info("执行幻灯片生成节点")
        
        try:
            # 初始化幻灯片生成Agent
            slide_generator_config = self.config.get("agents", {}).get("slide_generator", {})
            slide_generator = SlideGeneratorAgent(slide_generator_config)
            
            # 执行幻灯片生成
            result = await slide_generator.run(state)
            
            # 检查结果，设置验证标记供下一步使用
            state.validation_result = True  # 在 run 方法中已进行验证
            state.has_more_content = False  # 标记没有更多内容需要处理
            
            # 添加检查点
            state.add_checkpoint("slide_generator_completed")
        except Exception as e:
            error_msg = f"幻灯片生成失败: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            state.record_failure(error_msg)
            state.validation_result = False
    
    async def _execute_next_slide_or_end(self, state: AgentState) -> None:
        """
        检查是否还有更多内容需要处理，更新状态
        
        Args:
            state: 代理状态
        """
        try:
            logger.info("执行幻灯片进度检查")
            
            # 确保状态中有必要的属性
            if not hasattr(state, 'content_plan') or not state.content_plan:
                # 移除使用decision_result的兼容代码
                error_msg = "无法检查进度：缺少内容规划结果"
                logger.error(error_msg)
                state.record_failure(error_msg)
                state.has_more_content = False
                return
            
            # 直接使用content_plan
            total_slides = len(state.content_plan)
            
            # 当前幻灯片已验证通过，将其添加到已生成列表中
            if state.current_slide and state.validation_result:
                if not hasattr(state, 'generated_slides') or state.generated_slides is None:
                    state.generated_slides = []
                
                # 避免重复添加
                slide_ids = [slide.get('section_index') for slide in state.generated_slides]
                if (state.current_slide.get('section_index') not in slide_ids) and state.current_slide not in state.generated_slides:
                    state.generated_slides.append(state.current_slide)
                    logger.info(f"将验证通过的幻灯片添加到生成列表，当前共 {len(state.generated_slides)} 张")
            
            # 如果未设置当前章节索引，初始化为-1
            if state.current_section_index is None:
                state.current_section_index = -1
            
            # 更新到下一个章节索引
            state.current_section_index += 1
            next_index = state.current_section_index
            
            # 检查是否还有更多内容
            if next_index < total_slides:
                state.has_more_content = True
                logger.info(f"还有更多内容需要处理, 下一章节索引: {next_index}/{total_slides-1}")
            else:
                state.has_more_content = False
                logger.info("所有内容处理完成")
            
        except Exception as e:
            error_msg = f"检查进度失败: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            state.record_failure(error_msg)
            state.has_more_content = False
    
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
        
        logger.info(f"执行PPT分析节点, 模板路径: {state.ppt_template_path}")
        
        # 尝试从缓存获取分析结果
        cached_result = self.cache_manager.get_ppt_analysis_cache(state.ppt_template_path)
        
        if cached_result:
            logger.info("使用缓存的PPT分析结果")
            state.layout_features = cached_result
            # 添加检查点
            state.add_checkpoint("ppt_analyzer_completed")
            return
        
        try:
            # 初始化PPT分析Agent
            ppt_analyzer_config = self.config.get("agents", {}).get("ppt_analyzer", {})
            ppt_analyzer = PPTAnalysisAgent(ppt_analyzer_config)
            
            # 执行分析
            result = await ppt_analyzer.run(state)
            
            # 检查结果
            if result and result.layout_features:
                logger.info("PPT模板分析成功")
                # 更新状态
                state.layout_features = result.layout_features
                
                # 保存到缓存
                self.cache_manager.save_ppt_analysis_cache(state.ppt_template_path, state.layout_features)
                
                # 添加检查点
                state.add_checkpoint("ppt_analyzer_completed")
            else:
                error_msg = "PPT模板分析失败，未生成布局特征"
                logger.error(error_msg)
                state.record_failure(error_msg)
        except Exception as e:
            error_msg = f"PPT模板分析异常: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            state.record_failure(error_msg)
    
    async def _execute_content_planner(self, state: AgentState) -> None:
        """
        执行内容规划节点
        
        Args:
            state: 当前状态
        """
        # 检查有效性
        if not state.content_structure or not state.layout_features:
            error_msg = "缺少内容结构或布局特征，无法执行内容规划"
            logger.error(error_msg)
            state.record_failure(error_msg)
            return
        
        logger.info("执行内容规划节点")
        
        # 尝试从缓存获取规划结果
        cached_result = self.cache_manager.get_content_plan_cache(
            state.content_structure, 
            state.layout_features
        )
        
        if cached_result:
            logger.info("使用缓存的内容规划结果")
            state.content_plan = cached_result
            # 添加检查点
            state.add_checkpoint("content_planner_completed")
            return
        
        try:
            # 初始化内容规划Agent
            content_planner_config = self.config.get("agents", {}).get("content_planner", {})
            content_planner = ContentPlanningAgent(content_planner_config)
            
            # 执行规划
            result = await content_planner.run(state)
            
            # 检查结果
            if result and result.content_plan:
                logger.info("内容规划成功")
                # 更新状态
                state.content_plan = result.content_plan
                
                # 保存到缓存
                self.cache_manager.save_content_plan_cache(
                    state.content_structure,
                    state.layout_features,
                    state.content_plan
                )
                
                # 添加检查点
                state.add_checkpoint("content_planner_completed")
            else:
                error_msg = "内容规划失败，未生成规划结果"
                logger.error(error_msg)
                state.record_failure(error_msg)
                state.planning_failed = True
        except Exception as e:
            error_msg = f"内容规划异常: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            state.record_failure(error_msg)
            state.planning_failed = True
    
    async def _execute_ppt_finalizer(self, state: AgentState) -> None:
        """
        执行PPT清理与保存节点
        
        Args:
            state: 当前状态
        """
        logger.info("执行PPT清理与保存节点")
        
        try:
            # 初始化PPT清理与保存Agent
            ppt_finalizer_config = self.config.get("agents", {}).get("ppt_finalizer", {})
            ppt_finalizer = PPTFinalizerAgent(ppt_finalizer_config)
            
            # 执行清理与保存
            result = await ppt_finalizer.run(state)
            
            # 检查结果
            if result and result.output_ppt_path:
                logger.info(f"PPT清理与保存成功，文件路径: {result.output_ppt_path}")
                # 添加检查点
                state.add_checkpoint("ppt_finalizer_completed")
            else:
                error_msg = "PPT清理与保存失败，未生成输出文件"
                logger.error(error_msg)
                state.record_failure(error_msg)
        except Exception as e:
            error_msg = f"PPT清理与保存异常: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            state.record_failure(error_msg) 