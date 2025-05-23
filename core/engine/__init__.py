"""
工作流引擎初始化模块。
"""

# 更新为引入核心组件
from core.engine.workflowEngine import WorkflowEngine
from core.engine.state import AgentState

__all__ = ["WorkflowEngine", "AgentState"]
