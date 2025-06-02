"""
工作流引擎模块
"""
from typing import Dict, Any, Optional
import logging
from pathlib import Path
import asyncio
from datetime import datetime
import traceback

from core.engine.state import AgentState
from core.engine.configLoader import ConfigLoader
from core.engine.node_executor import NodeExecutor
from core.engine.workflow_builder import WorkflowBuilder
from config.settings import settings

# 引入监控功能（可选）
try:
    from core.monitoring import MLflowTracker
    HAS_MLFLOW = True
except ImportError:
    HAS_MLFLOW = False

# 配置日志
logger = logging.getLogger(__name__)

class WorkflowEngine:
    """工作流引擎，负责驱动整个工作流的执行"""
    
    def __init__(self, workflow_name: str = "ppt_assisstant", enable_tracking: bool = False):
        """
        初始化工作流引擎
        
        Args:
            workflow_name: 工作流配置名称
            enable_tracking: 是否启用MLflow跟踪
        """
        # 工作流基本配置
        self.workflow_name = workflow_name
        self.config = ConfigLoader.load_workflow_config(workflow_name)
        self.execution_logs = []
        
        # 跟踪相关
        self.enable_tracking = enable_tracking and HAS_MLFLOW
        self.tracker = None
        
        if self.enable_tracking:
            try:
                self.tracker = MLflowTracker(experiment_name=workflow_name)
                logger.info(f"已启用MLflow工作流跟踪: {workflow_name}")
            except Exception as e:
                logger.error(f"初始化MLflow跟踪器失败: {str(e)}")
                self.enable_tracking = False
        
        # 初始化工作流构建器和节点执行器
        self.workflow_builder = WorkflowBuilder(
            config=self.config,
            tracker=self.tracker,
            enable_tracking=self.enable_tracking
        )
        self.node_executor = NodeExecutor(
            config=self.config,
            tracker=self.tracker,
            enable_tracking=self.enable_tracking
        )
        
        # 构建工作流图
        self.graph = self.workflow_builder.build_workflow()
        
        logger.info(f"初始化工作流引擎: {workflow_name}")
    
    def get_execution_logs(self) -> list:
        """
        获取执行日志
        
        Returns:
            执行日志列表
        """
        return self.execution_logs
    
    def _convert_result_to_state(self, original_state: AgentState, result_dict: Optional[Dict[str, Any]]) -> AgentState:
        """
        将LangGraph返回的结果字典转换为AgentState对象
        
        Args:
            original_state: 原始状态
            result_dict: 结果字典，可能为None
            
        Returns:
            AgentState对象
        """
        # 创建新的AgentState，保留会话ID
        result_state = AgentState(session_id=original_state.session_id)
        
        # 复制原始状态中的检查点等
        result_state.checkpoints = original_state.checkpoints.copy() if original_state.checkpoints else []
        result_state.failures = original_state.failures.copy() if original_state.failures else []
        
        # 复制原始状态的所有属性作为基础
        for attr in dir(original_state):
            if not attr.startswith('_') and not callable(getattr(original_state, attr)):
                try:
                    setattr(result_state, attr, getattr(original_state, attr))
                except Exception as e:
                    logger.debug(f"无法复制属性 {attr}: {str(e)}")
        
        # 如果结果字典不为None，则更新状态
        if result_dict is not None:
            # 复制结果中的值到新状态
            for key, value in result_dict.items():
                if hasattr(result_state, key):
                    setattr(result_state, key, value)
            logger.debug(f"从结果字典更新了状态: {result_state.session_id}")
        else:
            logger.warning("结果字典为None，使用原始状态")
        
        return result_state
    
    async def run_async(self, session_id:Optional[str]=None, raw_md:Optional[str]=None, 
                        ppt_template_path:Optional[str]=None, output_dir:Optional[str]=None, 
                        enable_multimodal_validation: bool = False,
                        **kwargs) -> AgentState:
        """
        异步执行工作流
        
        Args:
            session_id: 会话ID，如果不提供则自动生成
            raw_md: 原始Markdown文本
            ppt_template_path: PPT模板路径
            output_dir: 输出目录
            enable_multimodal_validation: 是否启用多模态验证
            kwargs: 允许传递额外的参数，但会过滤掉progress_callback
            
        Returns:
            执行结果 (AgentState object)
        """
        state = None
        try:
            # 从kwargs中提取progress_callback，确保它不会传递给AgentState
            progress_callback = kwargs.pop('progress_callback', None)
            if progress_callback and hasattr(self.node_executor, 'set_progress_callback'):
                self.node_executor.set_progress_callback(progress_callback)
            
            # 初始化状态
            state = AgentState(
                session_id=session_id,
                raw_md=raw_md,
                ppt_template_path=ppt_template_path,
                output_dir=output_dir,
                enable_multimodal_validation=enable_multimodal_validation,
                **kwargs
            )
            logger.info(f"开始异步执行工作流，会话ID: {state.session_id}")
            
            # 开始跟踪（如果启用）
            if self.enable_tracking and self.tracker:
                self.tracker.start_workflow_run(state.session_id, self.workflow_name)
            
            # 按顺序执行主要节点，与LangGraph图结构保持一致
            error_response = await self.node_executor._execute_and_validate_node(
                "markdown_parser", state, 
                "content_structure", "Markdown解析失败，无法获取内容结构"
            )
            if error_response:
                state.record_failure(error_response.get("error", "未知错误"))
                state.save()
                # 通过进度回调反馈错误信息
                if hasattr(self.node_executor, 'report_progress'):
                    self.node_executor.report_progress(
                        "markdown_parser", 0, 
                        error_response.get("error", "Markdown解析失败"),
                        {"error": True}
                    )
                if self.enable_tracking and self.tracker: self.tracker.end_workflow_run("FAILED")
                return state
            
            error_response = await self.node_executor._execute_and_validate_node(
                "ppt_analyzer", state,
                "layout_features", "PPT模板分析失败，无法获取布局特征"
            )
            if error_response:
                state.record_failure(error_response.get("error", "未知错误"))
                state.save()
                # 通过进度回调反馈错误信息
                if hasattr(self.node_executor, 'report_progress'):
                    self.node_executor.report_progress(
                        "ppt_analyzer", 0, 
                        error_response.get("error", "PPT模板分析失败"),
                        {"error": True}
                    )
                if self.enable_tracking and self.tracker: self.tracker.end_workflow_run("FAILED")
                return state
            
            error_response = await self.node_executor._execute_and_validate_node(
                "content_planner", state,
                "content_plan", "内容规划失败，无法获取内容规划结果"
            )
            if error_response:
                state.record_failure(error_response.get("error", "未知错误"))
                state.save()
                # 通过进度回调反馈错误信息
                if hasattr(self.node_executor, 'report_progress'):
                    self.node_executor.report_progress(
                        "content_planner", 0, 
                        error_response.get("error", "内容规划失败"),
                        {"error": True}
                    )
                if self.enable_tracking and self.tracker: self.tracker.end_workflow_run("FAILED")
                return state
            
            # 如果内容规划失败，终止工作流
            if state.planning_failed:
                error_msg = "内容规划失败，终止工作流"
                logger.error(error_msg)
                state.record_failure(error_msg)
                # 通过进度回调反馈错误信息
                if hasattr(self.node_executor, 'report_progress'):
                    self.node_executor.report_progress(
                        "content_planner", 0, 
                        error_msg,
                        {"error": True}
                    )
                if self.enable_tracking and self.tracker: self.tracker.end_workflow_run("FAILED")
                state.save()
                return state
            
            # 初始化生成的幻灯片列表
            state.generated_slides = []
            
            # 执行幻灯片生成和PPT完善
            await self.node_executor._execute_and_validate_node("slide_generator", state)
            await self.node_executor._execute_and_validate_node("ppt_finalizer", state)
            
            # 保存最终状态
            state.save()
            logger.info(f"工作流执行完成，会话ID: {state.session_id}")
            
            # 结束跟踪（如果启用）
            if self.enable_tracking and self.tracker:
                self.tracker.end_workflow_run("FINISHED")
                
            # 返回完整的 AgentState 对象
            return state
            
        except Exception as e:
            error_msg = f"工作流执行失败: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            
            if state:
                state.record_failure(error_msg)
                state.save()
                if self.enable_tracking and self.tracker: self.tracker.end_workflow_run("FAILED")
                return state
            else:
                # 如果状态从未初始化，创建一个最小状态用于错误报告
                minimal_state = AgentState(session_id=session_id or "unknown_error_session")
                minimal_state.record_failure(error_msg)
                minimal_state.save()
                if self.enable_tracking and self.tracker: self.tracker.end_workflow_run("FAILED")
                return minimal_state
