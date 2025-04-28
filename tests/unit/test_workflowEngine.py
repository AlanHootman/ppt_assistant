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
        assert engine.workflow_name == "ppt_generation"
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
    
    # @pytest.mark.asyncio
    # async def test_run_workflow(self):
    #     # 创建引擎
    #     engine = WorkflowEngine()
        
    #     # 运行工作流
    #     input_data = {
    #         "raw_md": "# Test Markdown",
    #         "ppt_template_path": "/test/template.pptx"
    #     }
        
    #     result = await engine.run(input_data=input_data)
        
    #     # 验证 - 根据当前LangGraph实现，我们预期验证节点不会被执行
    #     # 因为我们直接从ppt_generator节点直接结束了工作流
    #     assert result.raw_md == "# Test Markdown"
    #     assert "markdown_parser_completed" in result.checkpoints
    #     assert "ppt_analyzer_completed" in result.checkpoints
    #     assert "layout_decider_completed" in result.checkpoints
    #     assert "ppt_generator_completed" in result.checkpoints
        
    #     # 验证内容结构
    #     assert result.content_structure is not None
    #     assert result.content_structure.get("title") == "Test Markdown"
        
    #     # 验证决策结果
    #     assert result.decision_result is not None
    #     assert "slides" in result.decision_result
    #     assert len(result.decision_result["slides"]) > 0
        
    #     # 验证文件路径
    #     assert result.ppt_file_path is not None 