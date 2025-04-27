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
                
            # 添加普通边 - 先只添加普通边，避免条件边问题
            if from_node and to_node and not condition:
                workflow.add_edge(from_node, to_node)
                logger.debug(f"添加边: {from_node} -> {to_node}")
        
        # 手动构建简单的条件边，用于测试阶段
        workflow.add_conditional_edges(
            "validator",
            self._validate_condition,
            {
                "pass": END,
                "retry": "ppt_generator"
            }
        )
        logger.debug(f"添加条件边: validator -> END/ppt_generator")
        
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
    
    async def run(self, session_id: Optional[str] = None, 
                 input_data: Optional[Dict[str, Any]] = None) -> AgentState:
        """
        运行工作流
        
        Args:
            session_id: 会话ID，如果为None则创建新会话
            input_data: 输入数据
            
        Returns:
            最终状态
        """
        # 准备初始状态
        if session_id:
            try:
                state = AgentState.load(session_id)
                logger.info(f"加载现有会话: {session_id}")
            except Exception as e:
                logger.warning(f"加载会话失败: {str(e)}，创建新会话")
                state = AgentState(session_id=session_id)
        else:
            state = AgentState()
            logger.info(f"创建新会话: {state.session_id}")
            
        # 更新输入数据
        if input_data:
            for key, value in input_data.items():
                if hasattr(state, key):
                    setattr(state, key, value)
                    logger.debug(f"设置属性 {key}={value}")
        
        # 确保raw_md和ppt_template_path都存在，否则工作流将无法正常工作
        if state.raw_md is None:
            logger.warning("未提供Markdown内容，工作流可能无法正常执行")
        if state.ppt_template_path is None:
            logger.warning("未提供PPT模板路径，工作流可能无法正常执行")
        
        logger.info(f"启动工作流，会话: {state.session_id}")
        
        # 启动MLflow跟踪
        if self.enable_tracking and self.tracker:
            self.tracker.start_workflow_run(state.session_id, self.workflow_name)
        
        try:
            # 清除之前的执行日志
            self.execution_logs = []
            
            # 直接模拟按序执行工作流节点，避免LangGraph的问题
            if state.raw_md and state.ppt_template_path:
                # 1. 执行Markdown解析节点
                logger.info(f"直接模拟执行工作流节点...")
                
                # 模拟执行markdown_parser节点
                self._execute_node_directly("markdown_parser", state)
                
                # 继续执行其他节点
                if state.content_structure:
                    self._execute_node_directly("ppt_analyzer", state)
                    
                if state.layout_features and state.content_structure:
                    self._execute_node_directly("layout_decider", state)
                    
                if state.decision_result:
                    self._execute_node_directly("ppt_generator", state)
                    self._execute_node_directly("validator", state)
                
                # 保存最终状态
                state.save()
                
                logger.info(f"工作流直接执行完成，节点执行次数: {len(self.execution_logs)}")
                
                # 结束MLflow跟踪
                if self.enable_tracking and self.tracker:
                    self.tracker.end_workflow_run("FINISHED")
                    
                return state
            
            # 如果不满足直接执行条件，尝试使用LangGraph执行
            logger.info("开始执行LangGraph工作流")
            
            # 当前测试阶段，增加递归限制的配置
            config = {"recursion_limit": 50}
            
            # 将AgentState转换为字典 - 修复LangGraph输入类型问题
            state_dict = state.to_dict()
            logger.debug(f"状态转换为字典: {len(state_dict)} 个属性")
            
            # 调用编译后的工作流，传入字典而不是AgentState对象
            try:
                result_dict = self.graph.invoke(state_dict, config)
                logger.info("LangGraph工作流执行完成")
            except Exception as e:
                logger.error(f"LangGraph工作流执行失败: {str(e)}")
                result_dict = None
                state.record_failure(f"工作流执行错误: {str(e)}")
            
            # 将结果字典转换回AgentState对象
            result = self._convert_result_to_state(state, result_dict)
            
            # 如果在执行中有失败记录，添加到结果状态
            if state.failures and not result.failures:
                result.failures = state.failures
            
            # 保存最终状态
            result.save()
            
            # 记录执行情况
            execution_summary = {
                "session_id": result.session_id,
                "start_time": self.execution_logs[0]["timestamp"] if self.execution_logs else datetime.now().isoformat(),
                "end_time": datetime.now().isoformat(),
                "node_count": len(self.execution_logs),
                "result": {
                    "ppt_file": result.ppt_file_path,
                    "failures": result.failures
                }
            }
            
            logger.info(f"工作流完成，会话: {result.session_id}, 节点执行次数: {len(self.execution_logs)}")
            
            # 结束MLflow跟踪
            if self.enable_tracking and self.tracker:
                self.tracker.end_workflow_run("FINISHED")
                
            return result
            
        except Exception as e:
            logger.error(f"工作流失败: {str(e)}")
            state.record_failure(str(e))
            state.save()
            
            # 结束MLflow跟踪，标记为失败
            if self.enable_tracking and self.tracker:
                self.tracker.end_workflow_run("FAILED")
            
            raise
    
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
            # Markdown解析节点使用真实实现
            # 注意：这里不能直接创建任务，因为单元测试中会导致问题
            # 调用者需要确保在异步环境中处理这个节点
            loop = asyncio.get_event_loop()
            try:
                future = asyncio.ensure_future(self._execute_markdown_parser(state))
                if not loop.is_running():
                    loop.run_until_complete(future)
            except RuntimeError as e:
                logger.error(f"执行markdown_parser出错: {str(e)}")
                state.record_failure(f"运行Markdown节点错误: {str(e)}")
        else:
            # 其他节点使用模拟实现
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

    async def run_async(self, session_id=None, raw_md=None, ppt_template_path=None, output_dir=None):
        """
        异步执行工作流
        
        Args:
            session_id (str, optional): 会话ID，如果为None则自动生成
            raw_md (str): 原始Markdown文本
            ppt_template_path (str, optional): PPT模板路径，默认None
            output_dir (str, optional): 输出目录路径，默认None
        
        Returns:
            dict: 工作流执行结果状态
        """
        # 如果没有提供会话ID，生成一个
        if not session_id:
            session_id = str(uuid.uuid4())
        
        logger.info(f"开始执行工作流，会话ID: {session_id}")
        
        # 初始化状态
        agent_state = AgentState(
            session_id=session_id,
            raw_md=raw_md,
            ppt_template_path=ppt_template_path,
            output_dir=output_dir
        )
        
        try:
            # 1. 执行Markdown解析节点
            logger.info("执行节点: markdown_agent")
            
            # 从配置中获取markdown_agent节点的配置
            node_config = None
            for node in self.config.get("workflow", {}).get("nodes", []):
                if node.get("name") == "markdown_agent":
                    node_config = node.get("config", {})
                    break
            
            if not node_config:
                node_config = {"model_type": "text"}
                logger.warning("未找到markdown_agent节点配置，使用默认配置")
            
            # 创建MarkdownAgent实例
            markdown_agent = MarkdownAgent(node_config)
            
            # 执行Markdown解析
            agent_state = await markdown_agent.run(agent_state)
            
            # 添加检查点
            self._add_checkpoint("markdown_parser", agent_state.to_dict())
            
            # 2. 执行PPT模板分析节点 - 使用mock实现
            logger.info("执行节点: ppt_analyzer (mock实现)")
            if agent_state.ppt_template_path:
                self._mock_ppt_analyzer(agent_state)
                self._add_checkpoint("ppt_analyzer", agent_state.to_dict())
            else:
                logger.warning("缺少PPT模板路径，跳过模板分析节点")
            
            # 3. 执行布局决策节点 - 使用mock实现
            logger.info("执行节点: layout_decider (mock实现)")
            if agent_state.content_structure and agent_state.layout_features:
                self._mock_layout_decider(agent_state)
                self._add_checkpoint("layout_decider", agent_state.to_dict())
            else:
                logger.warning("缺少内容结构或布局特征，跳过布局决策节点")
            
            # 4. 执行PPT生成节点 - 使用mock实现
            logger.info("执行节点: ppt_generator (mock实现)")
            if agent_state.decision_result:
                self._mock_ppt_generator(agent_state)
                self._add_checkpoint("ppt_generator", agent_state.to_dict())
            else:
                logger.warning("缺少决策结果，跳过PPT生成节点")
            
            # 5. 执行验证节点 - 使用mock实现
            logger.info("执行节点: validator (mock实现)")
            self._mock_validator(agent_state)
            self._add_checkpoint("validator", agent_state.to_dict())
            
            # 6. 返回最终状态
            return agent_state.to_dict()
            
        except Exception as e:
            logger.error(f"工作流执行出错: {str(e)}")
            agent_state.record_failure(f"工作流引擎错误: {str(e)}")
            return agent_state.to_dict()
        
    def _add_checkpoint(self, checkpoint_name, state_dict):
        """
        添加检查点，保存当前状态
        
        Args:
            checkpoint_name (str): 检查点名称
            state_dict (dict): 当前状态
        """
        self.checkpoints[checkpoint_name] = {
            "timestamp": datetime.now().isoformat(),
            "state": state_dict
        }
        logger.info(f"添加检查点: {checkpoint_name}")
    
    def _get_node_config(self, node_name):
        """
        获取节点配置
        
        Args:
            node_name (str): 节点名称
            
        Returns:
            dict: 节点配置
        """
        for node in self.config.get("workflow", {}).get("nodes", []):
            if node.get("name") == node_name:
                return node.get("config", {})
        
        logger.warning(f"未找到节点配置: {node_name}")
        return {}
    
    async def _execute_layout_decider_async(self, state):
        """
        执行布局决策节点
        
        Args:
            state (AgentState): 工作流状态
            
        Returns:
            AgentState: 更新后的工作流状态
        """
        logger.info("执行节点: layout_decider")
        
        # 确保state是AgentState对象
        if isinstance(state, dict):
            state = AgentState.from_dict(state)
        
        # 检查必要的状态信息
        if not hasattr(state, 'content_structure') or not state.content_structure:
            logger.warning("缺少内容结构信息，无法进行布局决策")
            state.record_failure("布局决策失败：缺少内容结构信息")
            return state
        
        if not hasattr(state, 'layout_features') or not state.layout_features:
            logger.warning("缺少布局特征信息，无法进行完整决策")
            # 这里可以继续执行，因为可以基于内容结构进行基本决策
        
        # 使用模拟实现替代真实Agent
        logger.info("使用模拟实现替代真实的布局决策Agent")
        self._mock_layout_decider(state)
        
        logger.info("布局决策完成")
        return state 

    def _mock_ppt_analyzer(self, state: AgentState) -> None:
        """
        模拟PPT分析节点实现
        
        Args:
            state: 代理状态
        """
        WorkflowMocks.mock_ppt_analyzer(state)

    def _mock_layout_decider(self, state: AgentState) -> None:
        """
        模拟布局决策节点实现
        
        Args:
            state: 代理状态
        """
        WorkflowMocks.mock_layout_decider(state)

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