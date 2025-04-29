"""
工作流引擎测试模块
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock

from core.engine.workflowEngine import WorkflowEngine
from core.engine.state import AgentState

class TestWorkflowEngine:
    
    @patch('core.engine.workflowEngine.WorkflowEngine._build_workflow')
    def test_init(self, mock_build_workflow):
        # 模拟_build_workflow返回值
        mock_graph = MagicMock()
        mock_build_workflow.return_value = mock_graph
        
        # 测试初始化
        engine = WorkflowEngine()
        
        # 验证
        assert engine.workflow_name == "ppt_assisstant"
        assert engine.graph is mock_graph
        mock_build_workflow.assert_called_once()
    
    @patch('core.engine.workflowEngine.WorkflowEngine._build_workflow')
    def test_placeholder_node(self, mock_build_workflow):
        # 模拟_build_workflow返回值
        mock_graph = MagicMock()
        mock_build_workflow.return_value = mock_graph
        
        # 创建引擎
        engine = WorkflowEngine()
        
        # 获取占位节点
        node_func = engine._placeholder_node("test_node")
        
        # 调用节点函数
        state = AgentState()
        result = node_func(state)
        
        # 验证
        assert result.current_node == "test_node"
        assert "test_node_completed" in result.checkpoints
    