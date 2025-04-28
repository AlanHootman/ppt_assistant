#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
工作流引擎异步执行测试模块
"""
import pytest
import asyncio
import os
from unittest.mock import patch, MagicMock

from core.engine.workflowEngine import WorkflowEngine
from core.engine.state import AgentState

@pytest.mark.asyncio
class TestWorkflowAsync:
    
    @patch('core.engine.workflowEngine.WorkflowEngine._build_workflow')
    async def test_run_async_basic(self, mock_build_workflow):
        """测试基本的异步工作流执行"""
        # 模拟_build_workflow返回值
        mock_graph = MagicMock()
        mock_build_workflow.return_value = mock_graph
        
        # 创建引擎
        engine = WorkflowEngine()
        
        # 运行工作流
        raw_md = "# Test Markdown\n\n## Section 1\n- Point 1\n- Point 2\n\n## Section 2\n- Point 3\n- Point 4"
        ppt_template_path = "libs/ppt_manager/test/testfiles/Iphone16Pro.pptx"
        test_output_dir = "workspace/test_output"
        os.makedirs(test_output_dir, exist_ok=True)
        
        # 模拟MarkdownAgent.run方法，避免实际调用LLM
        with patch('core.agents.markdown_agent.MarkdownAgent.run') as mock_run:
            # 设置模拟返回值
            mock_state = AgentState()
            mock_state.content_structure = {
                "title": "Test Markdown",
                "sections": [
                    {"title": "Section 1", "content": ["Point 1", "Point 2"]},
                    {"title": "Section 2", "content": ["Point 3", "Point 4"]}
                ]
            }
            mock_run.return_value = mock_state
            
            # 执行异步工作流
            result = await engine.run_async(
                raw_md=raw_md,
                ppt_template_path=ppt_template_path,
                output_dir=test_output_dir
            )
            
            # 验证结果
            assert isinstance(result, dict)
            assert "error" not in result
            
            # 验证模拟方法被调用
            mock_run.assert_called_once()
    
    @patch('core.engine.workflowEngine.WorkflowEngine._build_workflow')
    async def test_run_async_error_handling(self, mock_build_workflow):
        """测试异步工作流错误处理"""
        # 模拟_build_workflow返回值
        mock_graph = MagicMock()
        mock_build_workflow.return_value = mock_graph
        
        # 创建引擎
        engine = WorkflowEngine()
        
        # 不提供必要参数，应该返回错误
        result = await engine.run_async()
        
        # 验证返回错误
        assert isinstance(result, dict)
        assert "error" in result
    
    @patch('core.engine.workflowEngine.WorkflowEngine._build_workflow')
    async def test_run_async_full_workflow(self, mock_build_workflow):
        """测试完整的异步工作流执行过程"""
        # 模拟_build_workflow返回值
        mock_graph = MagicMock()
        mock_build_workflow.return_value = mock_graph
        
        # 创建引擎
        engine = WorkflowEngine()
        
        # 准备测试数据
        raw_md = "# Test Presentation\n\n## First Slide\n- Content for first slide\n\n## Second Slide\n- Content for second slide"
        ppt_template_path = "libs/ppt_manager/test/testfiles/Iphone16Pro.pptx"
        test_output_dir = "workspace/test_output"
        os.makedirs(test_output_dir, exist_ok=True)
        
        # 模拟MarkdownAgent.run方法
        with patch('core.agents.markdown_agent.MarkdownAgent.run') as mock_run:
            # 设置模拟返回值
            mock_state = AgentState()
            mock_state.content_structure = {
                "title": "Test Presentation",
                "sections": [
                    {"title": "First Slide", "content": ["Content for first slide"]},
                    {"title": "Second Slide", "content": ["Content for second slide"]}
                ]
            }
            mock_run.return_value = mock_state
            
            # 执行异步工作流
            result = await engine.run_async(
                raw_md=raw_md,
                ppt_template_path=ppt_template_path,
                output_dir=test_output_dir
            )
            
            # 验证结果
            assert isinstance(result, dict)
            assert result.get("current_section_index") >= 2  # 应该处理完两个章节
            assert "generated_slides" in result
            assert len(result.get("generated_slides", [])) >= 2  # 至少生成两张幻灯片
            assert "output_ppt_path" in result
            assert os.path.exists(result.get("output_ppt_path") + ".log")  # 检查日志文件是否生成
            
            # 验证模拟方法被调用
            mock_run.assert_called_once()

if __name__ == "__main__":
    pytest.main() 