#!/usr/bin/env python
"""
测试运行脚本
"""
import os
import sys
import pytest

if __name__ == "__main__":
    # 添加项目根目录到Python路径
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    
    # 运行测试 - 使用相对于项目根目录的路径
    result = pytest.main(["tests/unit", "-v"])
    
    # 返回测试结果
    sys.exit(result) 