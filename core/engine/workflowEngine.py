"""
工作流引擎模块
"""
from typing import Dict, Any, Callable, Optional, List, Tuple, Union
import logging
from pathlib import Path
import os
import json
import asyncio
from datetime import datetime
import uuid
import traceback

from langgraph.graph import StateGraph, END
# 修复: LangGraph API变更，确保使用最新API

from config.settings import settings
from core.engine.state import AgentState
from core.engine.configLoader import ConfigLoader
# 引入MarkdownAgent
from core.agents.markdown_agent import MarkdownAgent
# 导入模拟模块
from core.engine.mocks import WorkflowMocks
# 引入监控功能（可选）
try:
    from core.monitoring import MLflowTracker, register_with_langgraph
    HAS_MLFLOW = True
except ImportError:
    HAS_MLFLOW = False
# 暂时注释掉不存在的导入
# from core.agents.layout_agent import LayoutAgent
# from core.agents.ppt_agent import PPTAgent
from core.utils.markdown_parser import MarkdownParser

# 配置日志
logger = logging.getLogger(__name__)

class WorkflowEngine:
    """工作流引擎"""
    
    def __init__(self, workflow_name: str = "ppt_generation", enable_tracking: bool = False):
        """
        初始化工作流引擎
        
        Args:
            workflow_name: 工作流配置名称
            enable_tracking: 是否启用MLflow跟踪
        """
        self.workflow_name = workflow_name
        self.config = ConfigLoader.load_workflow_config(workflow_name)
        self.execution_logs = []
        self.checkpoints = {}
        self.enable_tracking = enable_tracking and HAS_MLFLOW
        self.tracker = None
        
        # 如果启用跟踪，初始化MLflow跟踪器
        if self.enable_tracking:
            try:
                self.tracker = MLflowTracker(experiment_name=workflow_name)
                logger.info(f"已启用MLflow工作流跟踪: {workflow_name}")
            except Exception as e:
                logger.error(f"初始化MLflow跟踪器失败: {str(e)}")
                self.enable_tracking = False
        
        self.graph = self._build_workflow()
        logger.info(f"初始化工作流引擎: {workflow_name}")
    
    def _build_workflow(self) -> StateGraph:
        """
        构建工作流图
        
        Returns:
            StateGraph: 工作流图实例
        """
        # 创建状态图
        workflow = StateGraph(AgentState)
        
        # 创建临时目录存储运行日志
        checkpoint_dir = settings.WORKSPACE_DIR / "checkpoints"
        checkpoint_dir.mkdir(exist_ok=True)
        
        # 从配置中读取节点信息
        nodes = self.config.get("workflow", {}).get("nodes", [])
        edges = self.config.get("workflow", {}).get("edges", [])
        
        logger.info(f"从配置中加载: {len(nodes)}个节点, {len(edges)}个边")
        
        # 添加节点
        for node_config in nodes:
            node_name = node_config.get("name")
            if node_name:
                # 当前使用占位节点，稍后会被真实Agent替换
                workflow.add_node(node_name, self._placeholder_node(node_name))
                logger.debug(f"添加节点: {node_name}")
        
        # 添加特殊节点处理next_slide_or_end逻辑
        workflow.add_node("next_slide_or_end", self._placeholder_node("next_slide_or_end"))
        logger.debug(f"添加特殊节点: next_slide_or_end")
                
        # 确定入口点
        entry_point = None
        
        # 添加普通边
        for edge_config in edges:
            from_node = edge_config.get("from")
            to_node = edge_config.get("to")
            condition = edge_config.get("condition")
            
            # 处理start边，确定入口点
            if from_node == "start":
                entry_point = to_node
                continue
                
            # 处理end节点，将小写的"end"转换为END常量
            if to_node == "end":
                to_node = END
            
            # 添加普通边 - 先只添加没有条件的边
            if from_node and to_node and not condition:
                workflow.add_edge(from_node, to_node)
                logger.debug(f"添加边: {from_node} -> {to_node}")
        
        # 添加条件边
        for edge_config in edges:
            from_node = edge_config.get("from")
            to_node = edge_config.get("to")
            condition = edge_config.get("condition")
            
            if condition:
                if from_node == "slide_validator":
                    workflow.add_conditional_edges(
                        from_node,
                        self._validation_condition,
                        condition
                    )
                    logger.debug(f"添加验证条件边: {from_node} -> {condition}")
                elif from_node == "next_slide_or_end":
                    workflow.add_conditional_edges(
                        from_node,
                        self._content_check_condition,
                        condition
                    )
                    logger.debug(f"添加内容检查条件边: {from_node} -> {condition}")
        
        # 设置入口点
        if entry_point:
            workflow.set_entry_point(entry_point)
            logger.debug(f"设置入口点: {entry_point}")
        else:
            # 默认使用第一个节点作为入口点
            if nodes:
                first_node = nodes[0].get("name")
                workflow.set_entry_point(first_node)
                logger.debug(f"设置默认入口点: {first_node}")
        
        # 如果启用了跟踪，添加MLflow处理器
        if self.enable_tracking and self.tracker:
            try:
                # 使用新的注册方法
                register_with_langgraph(self.tracker, workflow)
                logger.info("已注册MLflow节点执行跟踪器")
            except Exception as e:
                logger.error(f"添加MLflow处理器失败: {str(e)}")
        
        # 获取节点数量
        node_count = len(workflow.nodes) if hasattr(workflow, "nodes") else 0
        logger.info(f"构建工作流图完成，共{node_count}个节点")
        
        # 编译图 - 不使用递归限制参数，它在调用时设置
        return workflow.compile()
    
    def _validation_condition(self, state: Dict[str, Any]) -> str:
        """
        验证条件函数
        
        Args:
            state: 当前状态字典
            
        Returns:
            下一步分支名称
        """
        # 使用WorkflowMocks中的验证逻辑或实现新逻辑
        if isinstance(state, AgentState):
            if state.validation_result:
                return "pass"
            else:
                return "retry"
        else:
            # 字典状态
            return "pass" if state.get("validation_result", False) else "retry"
    
    def _content_check_condition(self, state: Dict[str, Any]) -> str:
        """
        内容检查条件函数，检查是否还有更多内容需要处理
        
        Args:
            state: 当前状态字典
            
        Returns:
            下一步分支名称
        """
        if isinstance(state, AgentState):
            return "has_more_content" if state.has_more_content else "completed"
        else:
            # 字典状态
            return "has_more_content" if state.get("has_more_content", False) else "completed"

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
    
    def _placeholder_node(self, node_name: str) -> Callable:
        """
        创建模拟节点处理函数（仅用于开发和测试阶段）
        
        Args:
            node_name: 节点名称
            
        Returns:
            节点处理函数
        """
        def mock_node_handler(state: Any) -> AgentState:
            """模拟节点处理函数，返回处理后的状态"""
            # 使用WorkflowMocks创建的处理函数处理状态
            mock_handler = WorkflowMocks.create_placeholder_node(node_name)
            
            # 先记录执行
            if isinstance(state, dict):
                session_id = state.get("session_id", "unknown")
            elif isinstance(state, AgentState):
                session_id = state.session_id
            else:
                session_id = "unknown"
                
            # 记录执行信息
            self._record_execution(node_name, session_id)
            
            # 使用模拟处理函数处理
            result_state = mock_handler(state)
            
            # 确保返回AgentState对象而不是字典
            return result_state
            
        return mock_node_handler
    
    def _execute_mock_node_logic(self, node_name: str, state: AgentState) -> None:
        """
        执行模拟节点逻辑（仅用于开发和测试阶段）
        
        Args:
            node_name: 节点名称
            state: 代理状态
        """
        # 这个方法已移至WorkflowMocks，此处只保留接口兼容性
        # 并转发到新的模拟实现
        WorkflowMocks.execute_mock_node_logic(node_name, state)
    
    async def _execute_markdown_parser(self, state: AgentState) -> None:
        """
        使用真实的MarkdownAgent解析Markdown内容
        
        Args:
            state: 代理状态
        """
        try:
            logger.info("执行真实的MarkdownAgent处理")
            
            # 从配置中获取markdown_parser节点的配置
            node_config = None
            for node in self.config.get("workflow", {}).get("nodes", []):
                if node.get("name") == "markdown_parser":
                    node_config = node.get("config", {})
                    break
            
            if not node_config:
                node_config = {"model_type": "text", "model_name": "gpt-4"}
                logger.warning("未找到markdown_parser节点配置，使用默认配置")
            
            # 创建MarkdownAgent实例
            markdown_agent = MarkdownAgent(node_config)
            
            # 执行Markdown解析
            updated_state = await markdown_agent.run(state)
            
            # 更新状态（虽然run方法已经更新了状态，但为了清晰起见，再次赋值）
            state.content_structure = updated_state.content_structure
            
            logger.info(f"MarkdownAgent执行完成，内容结构: {state.content_structure is not None}")
            
        except Exception as e:
            logger.error(f"执行MarkdownAgent失败: {str(e)}")
            state.record_failure(f"Markdown解析错误: {str(e)}")
    
    def _validate_condition(self, state: Dict[str, Any]) -> str:
        """
        验证条件函数
        
        Args:
            state: 当前状态字典
            
        Returns:
            下一步分支名称
        """
        # 使用WorkflowMocks中的验证逻辑
        return WorkflowMocks.validate_condition(state)
    
    async def run_async(self, session_id=None, raw_md=None, ppt_template_path=None, output_dir=None):
        """
        异步运行工作流
        
        Args:
            session_id: 会话ID
            raw_md: 原始Markdown内容
            ppt_template_path: PPT模板路径
            output_dir: 输出目录
            
        Returns:
            执行结果
        """
        # 准备初始状态
        state = AgentState(
            session_id=session_id,
            raw_md=raw_md,
            ppt_template_path=ppt_template_path,
            output_dir=output_dir
        )
        
        logger.info(f"异步运行工作流，会话: {state.session_id}")
        
        # 启动MLflow跟踪
        if self.enable_tracking and self.tracker:
            self.tracker.start_workflow_run(state.session_id, self.workflow_name)
        
        try:
            # 清除之前的执行日志
            self.execution_logs = []
            
            # 直接模拟按序执行工作流节点
            if state.raw_md and state.ppt_template_path:
                logger.info(f"直接模拟执行工作流节点...")
                
                # 1. 执行Markdown解析节点
                await self._execute_markdown_parser(state)
                
                # 2. 执行PPT分析节点
                if state.content_structure:
                    self._execute_node_directly("ppt_analyzer", state)
                
                # 3. 执行内容规划节点
                if state.content_structure and state.layout_features:
                    self._execute_node_directly("content_planner", state)
                
                # 初始化幻灯片生成状态
                if state.decision_result:
                    # 初始化当前章节索引和内容标记
                    state.current_section_index = 0
                    state.has_more_content = True
                    state.generated_slides = []
                    
                    # 循环生成幻灯片，直到所有内容处理完毕
                    while state.has_more_content:
                        # 幻灯片生成
                        self._execute_node_directly("slide_generator", state)
                        
                        # 幻灯片验证
                        self._execute_node_directly("slide_validator", state)
                        
                        # 检查验证结果，如果不通过则重新生成
                        if not state.validation_result:
                            logger.info(f"幻灯片验证不通过，重新生成...")
                            continue
                        
                        # 验证通过，处理下一章节
                        state.current_section_index += 1
                        
                        # 检查是否还有更多内容
                        state.has_more_content = (state.current_section_index < 
                                                len(state.decision_result.get("slides", [])))
                    
                    # 所有内容处理完毕，执行PPT清理和保存
                    self._execute_node_directly("ppt_finalizer", state)
                
                # 保存最终状态
                state.save()
                
                logger.info(f"工作流直接执行完成，节点执行次数: {len(self.execution_logs)}")
                
                # 结束MLflow跟踪
                if self.enable_tracking and self.tracker:
                    self.tracker.end_workflow_run("FINISHED")
                    
                return state.to_dict()
                
            # 如果无法直接模拟，尝试使用LangGraph执行
            logger.warning("无法直接模拟执行，将尝试使用LangGraph执行")
            return {"error": "直接模拟执行失败，LangGraph执行尚未实现"}
            
        except Exception as e:
            logger.error(f"工作流执行失败: {str(e)}")
            traceback.print_exc()
            
            # 结束MLflow跟踪，标记为失败
            if self.enable_tracking and self.tracker:
                self.tracker.end_workflow_run("FAILED")
                
            # 返回错误信息
            return {
                "error": str(e),
                "session_id": state.session_id,
                "timestamp": datetime.now().isoformat()
            }
    
    def _execute_node_directly(self, node_name: str, state: AgentState) -> None:
        """
        直接执行节点，跳过LangGraph框架
        
        Args:
            node_name: 节点名称
            state: 状态对象
        """
        logger.info(f"直接执行节点: {node_name}, 会话: {state.session_id}")
        state.current_node = node_name
        
        # 记录执行信息
        self._record_execution(node_name, state.session_id)
        
        # 根据节点类型执行不同的处理逻辑
        if node_name == "markdown_parser":
            # Markdown解析节点需要异步执行，由调用者处理
            logger.warning("markdown_parser节点需要异步执行，应由调用者处理")
        elif node_name == "ppt_analyzer":
            self._mock_ppt_analyzer(state)
        elif node_name == "content_planner":
            self._mock_content_planner(state)
        elif node_name == "slide_generator":
            self._mock_slide_generator(state)
        elif node_name == "slide_validator":
            self._mock_slide_validator(state)
        elif node_name == "ppt_finalizer":
            self._mock_ppt_finalizer(state)
        elif node_name == "next_slide_or_end":
            self._mock_next_slide_or_end(state)
        else:
            # 未知节点，使用通用模拟逻辑
            WorkflowMocks.execute_mock_node_logic(node_name, state)
        
        # 记录执行完成的检查点
        state.add_checkpoint(f"{node_name}_completed")
    
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
    
    def get_execution_logs(self) -> List[Dict[str, Any]]:
        """
        获取执行日志
        
        Returns:
            执行日志列表
        """
        return self.execution_logs

    def _mock_ppt_analyzer(self, state: AgentState) -> None:
        """
        模拟PPT分析节点实现
        
        Args:
            state: 代理状态
        """
        WorkflowMocks.mock_ppt_analyzer(state)

    def _mock_content_planner(self, state: AgentState) -> None:
        """
        模拟内容规划节点实现
        
        Args:
            state: 代理状态
        """
        WorkflowMocks.mock_content_planner(state)

    def _mock_slide_generator(self, state: AgentState) -> None:
        """
        模拟幻灯片生成节点实现
        
        Args:
            state: 代理状态
        """
        WorkflowMocks.mock_slide_generator(state)

    def _mock_slide_validator(self, state: AgentState) -> None:
        """
        模拟幻灯片验证节点实现
        
        Args:
            state: 代理状态
        """
        WorkflowMocks.mock_slide_validator(state)

    def _mock_next_slide_or_end(self, state: AgentState) -> None:
        """
        模拟检查是否还有更多内容节点实现
        
        Args:
            state: 代理状态
        """
        WorkflowMocks.mock_next_slide_or_end(state)

    def _mock_ppt_finalizer(self, state: AgentState) -> None:
        """
        模拟PPT清理与保存节点实现
        
        Args:
            state: 代理状态
        """
        WorkflowMocks.mock_ppt_finalizer(state)

    def _mock_ppt_generator(self, state: AgentState) -> None:
        """
        模拟PPT生成节点实现
        
        Args:
            state: 代理状态
        """
        WorkflowMocks.mock_ppt_generator(state)

    def _mock_validator(self, state: AgentState) -> None:
        """
        模拟验证节点实现
        
        Args:
            state: 代理状态
        """
        WorkflowMocks.mock_validator(state) 