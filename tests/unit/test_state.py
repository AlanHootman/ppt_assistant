"""
状态管理测试模块
"""
import pytest
import json
from pathlib import Path

from core.engine.state import AgentState
from config.settings import settings

class TestAgentState:
    
    def test_state_initialization(self):
        # 测试初始化
        state = AgentState()
        
        # 验证基本属性
        assert state.session_id is not None
        assert len(state.session_id) > 0
        assert state.failures == []
        assert state.checkpoints == []
        assert state.validation_attempts == 0
    
    def test_add_checkpoint(self):
        # 创建状态
        state = AgentState()
        
        # 添加检查点
        state.add_checkpoint("test_checkpoint")
        
        # 验证
        assert "test_checkpoint" in state.checkpoints
    
    def test_record_failure(self):
        # 创建状态
        state = AgentState()
        
        # 记录失败
        state.record_failure("test error")
        
        # 验证
        assert "test error" in state.failures
    
    def test_save_and_load(self, tmp_path):
        # 临时修改保存路径
        original_session_dir = settings.SESSION_DIR
        settings.SESSION_DIR = tmp_path
        
        try:
            # 创建测试状态
            state = AgentState(
                raw_md="# Test",
                ppt_template_path="/test/path.pptx",
                content_structure={"slides": [{"title": "Test"}]}
            )
            
            # 保存
            state.save()
            
            # 验证文件创建
            state_file = tmp_path / state.session_id / "state.json"
            assert state_file.exists()
            
            # 加载
            loaded_state = AgentState.load(state.session_id)
            
            # 验证数据一致性
            assert loaded_state.session_id == state.session_id
            assert loaded_state.raw_md == "# Test"
            
            # 修复: 使用更安全的验证方式
            content = loaded_state.content_structure or {}
            assert "slides" in content
            assert isinstance(content["slides"], list) and len(content["slides"]) > 0
            assert content["slides"][0].get("title") == "Test"
            
        finally:
            # 恢复原始设置
            settings.SESSION_DIR = original_session_dir 