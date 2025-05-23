"""
工作流引擎文件处理测试模块
"""
import pytest
import json
from pathlib import Path
import shutil
import os
from unittest.mock import patch

from core.engine.workflowEngine import WorkflowEngine
from core.engine.state import AgentState
from config.settings import settings

class TestEngineWithFiles:
    
    def setup_method(self):
        """测试前准备"""
        # 测试文件路径
        self.md_path = Path("tests/testfiles/MCP介绍.md")
        self.ppt_path = Path("tests/testfiles/Iphone16Pro.pptx")
        
        # 验证文件存在
        assert self.md_path.exists(), f"测试文件不存在: {self.md_path}"
        assert self.ppt_path.exists(), f"测试文件不存在: {self.ppt_path}"
        
        # 读取Markdown文件
        with open(self.md_path, "r", encoding="utf-8") as f:
            self.md_content = f.read()
        
        # 清理临时目录
        temp_dir = settings.WORKSPACE_DIR / "temp"
        if temp_dir.exists():
            for item in temp_dir.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
    
    @pytest.mark.asyncio
    async def test_workflow_process_files(self):
        """测试工作流处理实际文件"""
        # 初始化引擎
        engine = WorkflowEngine()
        
        # 运行工作流
        input_data = {
            "raw_md": self.md_content,
            "ppt_template_path": str(self.ppt_path)
        }
        
        result = await engine.run_async(**input_data)
        
        # 验证基本处理结果
        assert result.raw_md == self.md_content
        assert "markdown_parser_completed" in result.checkpoints
        assert result.content_structure is not None
        
        # 验证结构化结果
        assert "title" in result.content_structure
        assert "sections" in result.content_structure
        assert result.content_structure["title"] == "MCP协议技术解析与应用实践"
        assert len(result.content_structure["sections"]) > 0
        
        # 验证布局决策
        assert result.content_plan is not None
        assert len(result.content_plan) > 0
        
        # 验证输出文件
        if result.ppt_file_path:
            json_file = Path(result.ppt_file_path).with_suffix(".json")
            assert json_file.exists()
            
            # 读取JSON文件验证内容
            with open(json_file, "r", encoding="utf-8") as f:
                output_data = json.load(f)
            
            # 验证输出内容
            assert "slides" in output_data
            assert len(output_data["slides"]) > 0
            title_slide = output_data["slides"][0]
            assert title_slide["type"] == "title"
            assert title_slide["content"]["title"] == "MCP协议技术解析与应用实践" 