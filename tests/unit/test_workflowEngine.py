"""
工作流引擎测试模块
"""
import pytest
import asyncio
from unittest.mock import patch

from core.engine.workflowEngine import WorkflowEngine
from core.engine.state import AgentState

class TestWorkflowEngine:
    
    def test_init(self):
        # 测试初始化
        engine = WorkflowEngine()
        
        # 验证
        assert engine.workflow_name == "ppt_generation"
        assert engine.graph is not None
    
    def test_placeholder_node(self):
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
    
    @pytest.mark.asyncio
    async def test_run_workflow(self):
        # 创建引擎
        engine = WorkflowEngine()
        
        # 运行工作流
        input_data = {
            "raw_md": "# Test Markdown",
            "ppt_template_path": "/test/template.pptx"
        }
        
        result = await engine.run(input_data=input_data)
        
        # 验证
        assert result.raw_md == "# Test Markdown"
        assert "markdown_parser_completed" in result.checkpoints
        assert "ppt_analyzer_completed" in result.checkpoints
        assert "layout_decider_completed" in result.checkpoints
        assert "ppt_generator_completed" in result.checkpoints
        assert "validator_completed" in result.checkpoints 