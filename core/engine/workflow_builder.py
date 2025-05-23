"""
工作流构建器模块
负责构建和管理 LangGraph 工作流图
"""
import logging
from typing import Dict, Any, Optional, List, Callable
import uuid

from langgraph.graph import StateGraph, END

from core.engine.state import AgentState
from core.engine.mocks import WorkflowMocks

logger = logging.getLogger(__name__)

class WorkflowBuilder:
    """工作流构建器，负责构建 LangGraph 工作流图"""
    
    def __init__(self, config: Dict[str, Any], tracker: Optional[Any] = None, enable_tracking: bool = False):
        """
        初始化工作流构建器
        
        Args:
            config: 工作流配置
            tracker: 追踪器实例（可选）
            enable_tracking: 是否启用追踪
        """
        self.config = config
        self.tracker = tracker
        self.enable_tracking = enable_tracking
        
    def build_workflow(self) -> StateGraph:
        """
        构建工作流图
        
        Returns:
            StateGraph: 工作流图实例
        """
        # 创建状态图
        workflow = StateGraph(AgentState)
        
        # 从配置中读取节点信息
        nodes = self.config.get("workflow", {}).get("nodes", [])
        edges = self.config.get("workflow", {}).get("edges", [])
        
        logger.info(f"从配置中加载: {len(nodes)}个节点, {len(edges)}个边")
        
        # 添加节点
        for node_config in nodes:
            node_name = node_config.get("name")
            # 跳过slide_validator节点，因为它的功能已合并到slide_generator
            if node_name and node_name != "slide_validator":
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
                # 使用通用的跟踪器注册接口
                from core.monitoring import register_with_langgraph
                register_with_langgraph(self.tracker, workflow)
                logger.info("已注册节点执行跟踪器")
            except Exception as e:
                logger.error(f"添加跟踪处理器失败: {str(e)}")
        
        # 获取节点数量
        node_count = len(workflow.nodes) if hasattr(workflow, "nodes") else 0
        logger.info(f"构建工作流图完成，共{node_count}个节点")
        
        # 编译图
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
                
            # 记录执行信息（此处简化处理，实际记录由调用方执行）
            logger.debug(f"执行占位节点: {node_name}, 会话: {session_id}")
            
            # 使用模拟处理函数处理
            result_state = mock_handler(state)
            
            # 确保返回AgentState对象而不是字典
            return result_state
            
        return mock_node_handler 