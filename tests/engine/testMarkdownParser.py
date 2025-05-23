"""
Markdown解析测试模块
"""
import pytest
from pathlib import Path

from core.engine.workflowEngine import WorkflowEngine
from core.engine.state import AgentState

class TestMarkdownParser:
    
    def setup_method(self):
        # 测试文件路径
        self.test_md_path = Path("tests/testfiles/MCP介绍.md")
        assert self.test_md_path.exists(), f"测试文件不存在: {self.test_md_path}"
        
        # 读取测试文件内容
        with open(self.test_md_path, "r", encoding="utf-8") as f:
            self.test_md_content = f.read()
        
    def test_md_file_loading(self):
        """测试Markdown文件加载"""
        # 验证测试文件内容
        assert "MCP协议技术解析与应用实践" in self.test_md_content
        assert "## 一、协议基础认知" in self.test_md_content
        
    @pytest.mark.asyncio
    async def test_workflow_with_md_file(self):
        """测试使用实际Markdown文件运行工作流"""
        # 创建引擎
        engine = WorkflowEngine()
        
        # 准备输入数据
        input_data = {
            "raw_md": self.test_md_content,
            "ppt_template_path": str(Path("tests/testfiles/Iphone16Pro.pptx"))
        }
        
        # 运行工作流
        result = await engine.run_async(**input_data)
        
        # 验证基本处理过程
        assert result.raw_md == self.test_md_content
        assert "markdown_parser_completed" in result.checkpoints
        assert len(result.checkpoints) >= 5  # 验证所有节点都被执行 