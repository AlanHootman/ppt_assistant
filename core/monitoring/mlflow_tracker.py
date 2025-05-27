#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MLflow监控模块

提供基于MLflow的工作流监控功能，记录和可视化LangGraph工作流的执行过程。
"""

import os
import json
import logging
import mlflow
import mlflow.openai  # 导入OpenAI集成
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
import time

from core.engine.state import AgentState

logger = logging.getLogger(__name__)

class MLflowTracker:
    """MLflow跟踪器用于记录工作流执行数据"""
    
    def __init__(self, tracking_uri=None, experiment_name="workflow_executions"):
        """初始化MLflow跟踪器
        
        Args:
            tracking_uri: MLflow跟踪服务器URI，如未指定则从环境变量获取
            experiment_name: 实验名称
        """
        # 从环境变量获取tracking_uri（如果未指定），默认为http://127.0.0.1:5000
        self.tracking_uri = tracking_uri or os.environ.get("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
        self.experiment_name = experiment_name
        self.active_run = None
        
        # 设置MLflow跟踪URI
        mlflow.set_tracking_uri(self.tracking_uri)
        mlflow.set_experiment(experiment_name)
        
        # 启用OpenAI自动跟踪
        mlflow.openai.autolog()
        
        logger.info(f"MLflow跟踪器已初始化: URI={self.tracking_uri}, 实验={experiment_name}")
    
    def start_workflow_run(self, session_id=None, workflow_name=None):
        """开始工作流运行
        
        Args:
            session_id: 会话ID
            workflow_name: 工作流名称
        """
        # 结束之前的运行（如果有）
        if self.active_run:
            self.end_workflow_run("interrupted")
        
        # 创建新的运行
        tags = {
            "session_id": session_id or "unknown",
            "workflow_name": workflow_name or "unknown"
        }
        
        self.active_run = mlflow.start_run(run_name=f"workflow_{int(time.time())}", tags=tags)
        self.start_time = time.time()
        
        # 记录工作流开始
        mlflow.log_param("workflow_start_time", self.start_time)
        mlflow.log_param("workflow_name", workflow_name)
        
        logger.info(f"工作流运行已开始: {self.active_run.info.run_id}")
        return self.active_run
    
    def end_workflow_run(self, status="FINISHED"):
        """结束工作流运行
        
        Args:
            status: 运行状态 (FINISHED, FAILED, KILLED, RUNNING, SCHEDULED)
            MLflow仅支持这些状态值，不支持其他自定义值
        """
        if not self.active_run:
            logger.warning("没有活动的工作流运行可结束")
            return
        
        # 记录总运行时间
        end_time = time.time()
        duration = end_time - self.start_time
        
        mlflow.log_param("workflow_end_time", end_time)
        mlflow.log_metric("workflow_duration", duration)
        mlflow.log_param("workflow_status", status)
        
        # 结束运行
        mlflow.end_run(status=status)
        logger.info(f"工作流运行已结束: 状态={status}, 持续时间={duration:.2f}秒")
        self.active_run = None
    
    def log_node_execution(self, node_name, node_type, inputs, outputs, state_before, state_after, artifacts=None):
        """记录节点执行
        
        Args:
            node_name: 节点名称
            node_type: 节点类型
            inputs: 输入参数
            outputs: 输出结果
            state_before: 执行前状态
            state_after: 执行后状态
            artifacts: 生成的制品 (文件路径或内容)
        """
        if not self.active_run:
            logger.warning(f"无法记录节点执行 {node_name}: 没有活动运行")
            return
        
        # 记录执行时间
        execution_time = time.time()
        
        # 记录节点参数
        node_params = {
            f"node.{node_name}.type": node_type,
            f"node.{node_name}.execution_time": execution_time
        }
        mlflow.log_params(node_params)
        
        # 记录执行指标
        state_changes = {}
        if state_before and state_after:
            # 计算状态变化数量
            try:
                before_keys = set(state_before.keys())
                after_keys = set(state_after.keys())
                added_keys = after_keys - before_keys
                changed_keys = {k for k in before_keys.intersection(after_keys) 
                               if state_before[k] != state_after[k]}
                state_changes = {
                    f"node.{node_name}.added_keys": len(added_keys),
                    f"node.{node_name}.changed_keys": len(changed_keys)
                }
                mlflow.log_metrics(state_changes)
            except (AttributeError, TypeError):
                pass
        
        # 记录制品
        if artifacts:
            for name, artifact in artifacts.items():
                artifact_path = f"artifacts/{node_name}/{name}"
                if isinstance(artifact, str) and os.path.isfile(artifact):
                    # 文件路径
                    mlflow.log_artifact(artifact, artifact_path)
                else:
                    # 内容
                    try:
                        content = json.dumps(artifact, indent=2)
                        temp_path = f"/tmp/{name}.json"
                        with open(temp_path, "w") as f:
                            f.write(content)
                        mlflow.log_artifact(temp_path, artifact_path)
                        os.remove(temp_path)
                    except:
                        logger.warning(f"无法记录制品 {name} 用于节点 {node_name}")

def register_with_langgraph(tracker, graph):
    """向LangGraph注册MLflow跟踪器
    
    Args:
        tracker: MLflowTracker实例
        graph: LangGraph StateGraph实例
    """
    def on_node_execution_completed(run_id, node_name, state_before, state_after):
        """节点执行完成时的回调函数"""
        # 提取节点类型和输入/输出
        node_type = "unknown"
        inputs = {}
        outputs = {}
        
        try:
            # 尝试从状态中提取更多信息
            if hasattr(state_after, "get"):
                if state_after.get("node_outputs"):
                    outputs = state_after.get("node_outputs", {}).get(node_name, {})
                if state_after.get("node_inputs"):
                    inputs = state_after.get("node_inputs", {}).get(node_name, {})
        except:
            pass
        
        # 记录节点执行
        tracker.log_node_execution(
            node_name=node_name,
            node_type=node_type,
            inputs=inputs,
            outputs=outputs,
            state_before=state_before,
            state_after=state_after
        )
    
    # 注册回调
    if hasattr(graph, "on_node_execution_completed"):
        graph.on_node_execution_completed(on_node_execution_completed)
    else:
        # 尝试使用旧API
        try:
            handler = lambda config: on_node_execution_completed(
                config["run_id"],
                config["node_name"],
                config["state_before"],
                config["state_after"]
            )
            graph.add_node_run_handler(handler)
        except:
            raise ValueError("无法注册MLflow处理器: 不支持的Graph API")
    
    return graph

# 为向后兼容保留旧API
def create_mlflow_handler(tracker: MLflowTracker) -> Callable:
    """
    创建可用于LangGraph的MLflow处理器 (旧API，保留兼容性)
    
    Args:
        tracker: MLflow跟踪器实例
        
    Returns:
        处理器函数
    """
    def mlflow_handler(state, config=None, node_name=None, **kwargs):
        """
        LangGraph事件处理器
        
        Args:
            state: 节点状态
            config: 配置
            node_name: 节点名称
        """
        if not node_name or node_name == "":
            return
        
        # 确保状态是AgentState类型
        agent_state = state
        if not isinstance(state, AgentState) and isinstance(state, dict):
            # 如果是字典，尝试转换为AgentState
            try:
                agent_state = AgentState.from_dict(state)
            except Exception as e:
                logger.error(f"无法将状态转换为AgentState: {str(e)}")
                return
        
        # 记录节点执行
        tracker.log_node_execution(node_name, "unknown", {}, {}, None, agent_state)
        
    return mlflow_handler 