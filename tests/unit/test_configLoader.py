"""
配置加载器测试模块
"""
import pytest
import os
from pathlib import Path
import yaml
import tempfile

from core.engine.configLoader import ConfigLoader
from config.settings import settings

class TestConfigLoader:
    
    def test_load_yaml_with_valid_file(self):
        # 创建临时配置文件
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp:
            temp.write(b"""
            test:
              value: 123
              nested:
                key: value
            """)
            temp_path = Path(temp.name)
        
        try:
            # 测试加载
            config = ConfigLoader.load_yaml(temp_path)
            
            # 验证
            assert config.get("test") is not None
            assert config["test"]["value"] == 123
            assert config["test"]["nested"]["key"] == "value"
        finally:
            # 清理
            temp_path.unlink(missing_ok=True)
    
    def test_load_yaml_with_missing_file(self):
        # 测试不存在的文件
        config = ConfigLoader.load_yaml(Path("nonexistent.yaml"))
        assert config == {}
    
    def test_resolve_env_vars(self):
        # 设置测试环境变量
        os.environ["TEST_VAR"] = "test_value"
        
        # 测试配置
        test_config = {
            "simple": "${TEST_VAR}",
            "default": "${MISSING_VAR:default_value}",
            "nested": {
                "env": "${TEST_VAR}"
            },
            "list": [
                {"env": "${TEST_VAR}"},
                "plain"
            ]
        }
        
        # 解析环境变量
        resolved = ConfigLoader.resolve_env_vars(test_config)
        
        # 验证
        assert resolved["simple"] == "test_value"
        assert resolved["default"] == "default_value"
        assert resolved["nested"]["env"] == "test_value"
        assert resolved["list"][0]["env"] == "test_value"
        assert resolved["list"][1] == "plain" 