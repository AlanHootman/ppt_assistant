"""
工作流执行器模块，提供工作流的执行与管理功能。
"""
import os
import json
import time
import asyncio
import logging
import traceback
from typing import Dict, List, Any, Optional, Callable, Type, Union, Tuple
from datetime import datetime
import uuid

from core.engine.workflow import Workflow, WorkflowStep
from core.engine.registry import registry

# 配置日志
logger = logging.getLogger("workflow_executor")

class ExecutionStatus:
    """工作流执行状态常量"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

class StepExecutionResult:
    """步骤执行结果"""
    
    def __init__(self, 
                 step_id: str, 
                 status: str,
                 output: Optional[Dict[str, Any]] = None,
                 error: Optional[str] = None,
                 start_time: Optional[float] = None,
                 end_time: Optional[float] = None):
        """
        初始化步骤执行结果
        
        参数:
            step_id: 步骤ID
            status: 执行状态
            output: 输出数据
            error: 错误信息
            start_time: 开始时间戳
            end_time: 结束时间戳
        """
        self.step_id = step_id
        self.status = status
        self.output = output or {}
        self.error = error
        self.start_time = start_time or time.time()
        self.end_time = end_time or (None if status == ExecutionStatus.RUNNING else time.time())
    
    @property
    def duration(self) -> Optional[float]:
        """获取执行持续时间（秒）"""
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "step_id": self.step_id,
            "status": self.status,
            "output": self.output,
            "error": self.error,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration
        }

class WorkflowExecutionResult:
    """工作流执行结果"""
    
    def __init__(self, 
                 workflow_id: str,
                 workflow_name: str,
                 status: str = ExecutionStatus.PENDING,
                 execution_id: Optional[str] = None):
        """
        初始化工作流执行结果
        
        参数:
            workflow_id: 工作流ID
            workflow_name: 工作流名称
            status: 执行状态
            execution_id: 执行ID（可选，默认生成新ID）
        """
        self.workflow_id = workflow_id
        self.workflow_name = workflow_name
        self.status = status
        self.execution_id = execution_id or str(uuid.uuid4())
        self.start_time = time.time()
        self.end_time = None
        self.step_results: Dict[str, StepExecutionResult] = {}
        self.current_step_id: Optional[str] = None
        self.error: Optional[str] = None
        self.output: Dict[str, Any] = {}
        
        logger.debug(f"创建工作流执行结果: {self.execution_id} (工作流: {workflow_name})")
    
    def mark_step_start(self, step_id: str) -> None:
        """
        标记步骤开始执行
        
        参数:
            step_id: 步骤ID
        """
        self.current_step_id = step_id
        self.step_results[step_id] = StepExecutionResult(
            step_id=step_id,
            status=ExecutionStatus.RUNNING
        )
        logger.debug(f"开始执行步骤: {step_id} (执行ID: {self.execution_id})")
    
    def mark_step_complete(self, step_id: str, output: Dict[str, Any]) -> None:
        """
        标记步骤执行完成
        
        参数:
            step_id: 步骤ID
            output: 输出数据
        """
        # 更新步骤结果
        if step_id in self.step_results:
            result = self.step_results[step_id]
            result.status = ExecutionStatus.COMPLETED
            result.output = output
            result.end_time = time.time()
        else:
            self.step_results[step_id] = StepExecutionResult(
                step_id=step_id,
                status=ExecutionStatus.COMPLETED,
                output=output,
                end_time=time.time()
            )
        
        # 更新工作流输出（合并所有步骤输出）
        self.output.update(output)
        logger.debug(f"步骤执行完成: {step_id} (执行ID: {self.execution_id})")
    
    def mark_step_failed(self, step_id: str, error: str) -> None:
        """
        标记步骤执行失败
        
        参数:
            step_id: 步骤ID
            error: 错误信息
        """
        # 更新步骤结果
        if step_id in self.step_results:
            result = self.step_results[step_id]
            result.status = ExecutionStatus.FAILED
            result.error = error
            result.end_time = time.time()
        else:
            self.step_results[step_id] = StepExecutionResult(
                step_id=step_id,
                status=ExecutionStatus.FAILED,
                error=error,
                end_time=time.time()
            )
        
        logger.debug(f"步骤执行失败: {step_id}, 错误: {error} (执行ID: {self.execution_id})")
    
    def mark_completed(self) -> None:
        """标记工作流执行完成"""
        self.status = ExecutionStatus.COMPLETED
        self.end_time = time.time()
        logger.info(f"工作流执行完成: {self.workflow_name} (执行ID: {self.execution_id})")
    
    def mark_failed(self, error: str) -> None:
        """
        标记工作流执行失败
        
        参数:
            error: 错误信息
        """
        self.status = ExecutionStatus.FAILED
        self.error = error
        self.end_time = time.time()
        logger.error(f"工作流执行失败: {self.workflow_name}, 错误: {error} (执行ID: {self.execution_id})")
    
    def mark_cancelled(self) -> None:
        """标记工作流执行取消"""
        self.status = ExecutionStatus.CANCELLED
        self.end_time = time.time()
        logger.info(f"工作流执行取消: {self.workflow_name} (执行ID: {self.execution_id})")
    
    def mark_timeout(self) -> None:
        """标记工作流执行超时"""
        self.status = ExecutionStatus.TIMEOUT
        self.end_time = time.time()
        logger.warning(f"工作流执行超时: {self.workflow_name} (执行ID: {self.execution_id})")
    
    @property
    def duration(self) -> Optional[float]:
        """获取执行持续时间（秒）"""
        if self.end_time:
            return self.end_time - self.start_time
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "current_step_id": self.current_step_id,
            "error": self.error,
            "output": self.output,
            "steps": {step_id: result.to_dict() for step_id, result in self.step_results.items()}
        }

class WorkflowExecutor:
    """工作流执行器，负责执行工作流"""
    
    def __init__(self):
        """初始化工作流执行器"""
        self._running_workflows: Dict[str, asyncio.Task] = {}
        logger.debug("初始化工作流执行器")
    
    async def execute(self, 
                      workflow: Workflow, 
                      input_data: Dict[str, Any] = None,
                      timeout: Optional[float] = None) -> WorkflowExecutionResult:
        """
        执行工作流
        
        参数:
            workflow: 要执行的工作流
            input_data: 输入数据
            timeout: 超时时间（秒）
            
        返回:
            工作流执行结果
        """
        input_data = input_data or {}
        execution_result = WorkflowExecutionResult(
            workflow_id=workflow.id,
            workflow_name=workflow.name
        )
        execution_result.status = ExecutionStatus.RUNNING
        
        # 检查工作流是否有步骤
        if not workflow.steps:
            execution_result.mark_failed("工作流没有步骤可执行")
            return execution_result
        
        logger.info(f"开始执行工作流: {workflow.name} (ID: {workflow.id})")
        
        # 创建执行任务
        task = asyncio.create_task(
            self._execute_workflow(workflow, input_data, execution_result)
        )
        self._running_workflows[execution_result.execution_id] = task
        
        try:
            # 等待工作流执行完成或超时
            await asyncio.wait_for(task, timeout=timeout)
        except asyncio.TimeoutError:
            # 工作流执行超时
            execution_result.mark_timeout()
            # 取消任务
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        except Exception as e:
            # 工作流执行异常
            error_msg = f"工作流执行异常: {str(e)}\n{traceback.format_exc()}"
            execution_result.mark_failed(error_msg)
        finally:
            # 从运行中的工作流中移除
            if execution_result.execution_id in self._running_workflows:
                del self._running_workflows[execution_result.execution_id]
        
        return execution_result
    
    async def _execute_workflow(self,
                               workflow: Workflow,
                               input_data: Dict[str, Any],
                               execution_result: WorkflowExecutionResult) -> None:
        """
        执行工作流内部实现
        
        参数:
            workflow: 要执行的工作流
            input_data: 输入数据
            execution_result: 工作流执行结果
        """
        # 执行上下文，用于存储每个步骤的输出
        context: Dict[str, Any] = {**input_data}
        
        try:
            # 按顺序执行每个步骤
            for step in workflow.steps.values():
                # 检查是否被取消
                if execution_result.status == ExecutionStatus.CANCELLED:
                    break
                
                # 执行步骤
                step_result = await self._execute_step(step, context, execution_result)
                
                # 如果步骤执行失败，根据错误处理策略决定是否继续
                if step_result.status == ExecutionStatus.FAILED:
                    error_handling = workflow.error_handling.get("strategy", "fail_fast")
                    
                    if error_handling == "fail_fast":
                        # 快速失败策略，整个工作流失败
                        execution_result.mark_failed(f"步骤 '{step.name}' 执行失败: {step_result.error}")
                        return
                    
                    # 继续执行策略，记录错误但继续执行后续步骤
                    logger.warning(f"步骤 '{step.name}' 执行失败，但根据错误处理策略继续执行")
                
                # 更新上下文
                if step_result.status == ExecutionStatus.COMPLETED:
                    context.update(step_result.output)
            
            # 如果所有步骤都执行完成且工作流未被标记为失败或取消，则标记工作流为完成
            if execution_result.status == ExecutionStatus.RUNNING:
                execution_result.mark_completed()
        
        except Exception as e:
            # 捕获执行过程中的任何异常
            error_msg = f"工作流执行异常: {str(e)}\n{traceback.format_exc()}"
            execution_result.mark_failed(error_msg)
    
    async def _execute_step(self,
                           step: WorkflowStep,
                           context: Dict[str, Any],
                           execution_result: WorkflowExecutionResult) -> StepExecutionResult:
        """
        执行单个工作流步骤
        
        参数:
            step: 要执行的步骤
            context: 执行上下文
            execution_result: 工作流执行结果
            
        返回:
            步骤执行结果
        """
        # 标记步骤开始执行
        execution_result.mark_step_start(step.id)
        
        # 准备步骤输入
        step_input = {}
        
        try:
            # 映射输入
            if step.input_mapping:
                for dest_key, source_expr in step.input_mapping.items():
                    if source_expr in context:
                        step_input[dest_key] = context[source_expr]
                    else:
                        logger.warning(f"输入映射键 '{source_expr}' 在上下文中不存在")
            else:
                # 如果没有指定输入映射，使用整个上下文作为输入
                step_input = context.copy()
            
            # 获取函数
            func = None
            if callable(step.func):
                func = step.func
            elif isinstance(step.func, str) and step.func in registry:
                func = registry.get(step.func)
            
            if not func:
                raise ValueError(f"无法找到步骤函数: {step.func}")
            
            # 执行函数，支持同步和异步函数
            logger.debug(f"执行步骤: {step.name} (函数: {func.__name__})")
            if asyncio.iscoroutinefunction(func):
                result = await func(**step_input)
            else:
                # 在线程池中执行同步函数
                result = await asyncio.to_thread(func, **step_input)
            
            # 准备输出
            if not isinstance(result, dict):
                # 如果结果不是字典，将其包装为字典
                result = {"result": result}
            
            # 映射输出
            output = {}
            if step.output_mapping:
                for dest_key, source_key in step.output_mapping.items():
                    if source_key in result:
                        output[dest_key] = result[source_key]
                    else:
                        logger.warning(f"输出映射键 '{source_key}' 在结果中不存在")
            else:
                # 如果没有指定输出映射，使用整个结果作为输出
                output = result
            
            # 标记步骤完成
            execution_result.mark_step_complete(step.id, output)
            
            # 创建并返回步骤执行结果
            return StepExecutionResult(
                step_id=step.id,
                status=ExecutionStatus.COMPLETED,
                output=output,
                start_time=execution_result.step_results[step.id].start_time,
                end_time=time.time()
            )
        
        except Exception as e:
            # 捕获步骤执行异常
            error_msg = f"步骤执行异常: {str(e)}\n{traceback.format_exc()}"
            execution_result.mark_step_failed(step.id, error_msg)
            
            # 创建并返回步骤执行结果
            return StepExecutionResult(
                step_id=step.id,
                status=ExecutionStatus.FAILED,
                error=error_msg,
                start_time=execution_result.step_results[step.id].start_time,
                end_time=time.time()
            )
    
    def cancel_execution(self, execution_id: str) -> bool:
        """
        取消正在执行的工作流
        
        参数:
            execution_id: 执行ID
            
        返回:
            如果成功取消则为True，否则为False
        """
        if execution_id not in self._running_workflows:
            logger.warning(f"尝试取消不存在的工作流执行: {execution_id}")
            return False
        
        # 获取任务并取消
        task = self._running_workflows[execution_id]
        task.cancel()
        
        logger.info(f"取消工作流执行: {execution_id}")
        return True
    
    async def cancel_all_executions(self) -> int:
        """
        取消所有正在执行的工作流
        
        返回:
            取消的工作流数量
        """
        count = len(self._running_workflows)
        
        # 取消所有任务
        for execution_id, task in list(self._running_workflows.items()):
            task.cancel()
            logger.info(f"取消工作流执行: {execution_id}")
        
        # 等待所有任务完成取消
        for task in list(self._running_workflows.values()):
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # 清空运行中的工作流
        self._running_workflows.clear()
        
        logger.info(f"取消所有工作流执行: {count}个")
        return count
    
    def get_running_executions(self) -> List[str]:
        """
        获取所有正在执行的工作流ID
        
        返回:
            执行ID列表
        """
        return list(self._running_workflows.keys())
    
    def is_running(self, execution_id: str) -> bool:
        """
        检查工作流是否正在执行
        
        参数:
            execution_id: 执行ID
            
        返回:
            如果工作流正在执行则为True，否则为False
        """
        return execution_id in self._running_workflows

# 创建全局执行器实例
executor = WorkflowExecutor() 