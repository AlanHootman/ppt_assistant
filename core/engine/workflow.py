"""
工作流模块，定义工作流和工作流步骤的数据结构。
"""
import os
import json
import time
import uuid
import logging
from typing import Dict, List, Any, Optional, Callable, Union, Set
from datetime import datetime
from pydantic import BaseModel, Field
from copy import deepcopy

# 配置日志
logger = logging.getLogger("workflow")

class WorkflowStep:
    """工作流步骤，定义工作流中的一个执行单元"""
    
    def __init__(self, 
                 name: str,
                 func: Union[Callable, str],
                 input_mapping: Optional[Dict[str, str]] = None,
                 output_mapping: Optional[Dict[str, str]] = None,
                 description: Optional[str] = None,
                 step_id: Optional[str] = None,
                 retry: Optional[Dict[str, Any]] = None,
                 timeout: Optional[float] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        """
        初始化工作流步骤
        
        参数:
            name: 步骤名称
            func: 步骤函数，可以是可调用对象或注册函数的名称
            input_mapping: 输入映射，将上下文数据映射到函数参数（目标参数名：源字段名）
            output_mapping: 输出映射，将函数输出映射到上下文数据（目标字段名：源输出名）
            description: 步骤描述
            step_id: 步骤ID，如果未提供则自动生成
            retry: 重试策略
            timeout: 超时时间（秒）
            metadata: 元数据
        """
        self.id = step_id or str(uuid.uuid4())
        self.name = name
        self.func = func
        self.input_mapping = input_mapping or {}
        self.output_mapping = output_mapping or {}
        self.description = description or f"执行步骤: {name}"
        self.retry = retry or {"max_attempts": 1}
        self.timeout = timeout
        self.metadata = metadata or {}
        
        logger.debug(f"创建工作流步骤: {name} (ID: {self.id})")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将步骤转换为字典表示（用于序列化）
        
        返回:
            步骤的字典表示
        """
        func_name = self.func.__name__ if callable(self.func) else self.func
        
        return {
            "id": self.id,
            "name": self.name,
            "func": func_name,
            "description": self.description,
            "input_mapping": self.input_mapping,
            "output_mapping": self.output_mapping,
            "retry": self.retry,
            "timeout": self.timeout,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, step_data: Dict[str, Any], func_registry=None) -> 'WorkflowStep':
        """
        从字典创建步骤（用于反序列化）
        
        参数:
            step_data: 步骤的数据字典
            func_registry: 函数注册表，用于解析函数名
            
        返回:
            步骤实例
        """
        # 处理函数引用
        func = step_data["func"]
        if isinstance(func, str) and func_registry and func in func_registry:
            func = func_registry.get(func)
        
        return cls(
            name=step_data["name"],
            func=func,
            input_mapping=step_data.get("input_mapping"),
            output_mapping=step_data.get("output_mapping"),
            description=step_data.get("description"),
            step_id=step_data.get("id"),
            retry=step_data.get("retry"),
            timeout=step_data.get("timeout"),
            metadata=step_data.get("metadata"),
        )


class Workflow:
    """工作流，由一系列步骤组成的可执行流程"""
    
    def __init__(self, 
                 name: str,
                 description: str = "",
                 version: str = "1.0.0",
                 error_handling: str = "stop",
                 id: Optional[str] = None):
        """
        初始化工作流
        
        参数:
            name: 工作流名称
            description: 工作流描述
            version: 工作流版本
            error_handling: 错误处理策略 (stop, continue, skip_remaining)
            id: 工作流ID，如果不提供则自动生成
        """
        self.name = name
        self.description = description
        self.version = version
        self.error_handling = error_handling
        self.id = id or str(uuid.uuid4())
        
        self.steps: Dict[str, WorkflowStep] = {}
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.metadata: Dict[str, Any] = {}
        self.status = "draft"  # draft, active, deprecated
        
        # 生成对象ID
        logger.info(f"创建工作流: {name} (ID: {self.id})")
    
    def add_step(self, step: WorkflowStep) -> 'Workflow':
        """
        添加工作流步骤
        
        参数:
            step: 工作流步骤
            
        返回:
            工作流实例（用于链式调用）
        """
        if step.id in self.steps:
            logger.warning(f"覆盖已存在的步骤ID: {step.id}")
        
        self.steps[step.id] = step
        self.updated_at = datetime.now()
        logger.debug(f"添加步骤 '{step.name}' 到工作流 '{self.name}'")
        return self
    
    def add_steps(self, steps: List[WorkflowStep]) -> None:
        """
        批量添加工作流步骤
        
        参数:
            steps: 工作流步骤列表
        """
        for step in steps:
            self.add_step(step)
    
    def remove_step(self, step_id: str) -> Optional[WorkflowStep]:
        """
        移除工作流步骤
        
        参数:
            step_id: 步骤ID
            
        返回:
            被移除的步骤，如果不存在则返回None
        """
        if step_id not in self.steps:
            logger.warning(f"尝试移除不存在的步骤ID: {step_id}")
            return None
        
        step = self.steps.pop(step_id)
        self.updated_at = datetime.now()
        logger.debug(f"从工作流 '{self.name}' 中移除步骤 '{step.name}'")
        return step
    
    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        """
        获取步骤
        
        参数:
            step_id: 步骤ID
            
        返回:
            工作流步骤，如果不存在则返回None
        """
        return self.steps.get(step_id)
    
    def get_steps(self) -> List[WorkflowStep]:
        """
        获取所有步骤
        
        返回:
            工作流步骤列表
        """
        return list(self.steps.values())
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将工作流转换为字典表示（用于序列化）
        
        返回:
            工作流的字典表示
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "error_handling": self.error_handling,
            "steps": {step_id: step.to_dict() for step_id, step in self.steps.items()},
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
            "status": self.status
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], function_registry: Dict[str, Callable]) -> 'Workflow':
        """
        从字典创建工作流（用于反序列化）
        
        参数:
            data: 工作流的字典表示
            function_registry: 函数注册表 {函数名: 函数对象}
            
        返回:
            工作流实例
        """
        workflow = cls(
            name=data.get("name"),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            error_handling=data.get("error_handling", "stop"),
            id=data.get("id")
        )
        
        # 设置时间戳
        if "created_at" in data:
            workflow.created_at = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data:
            workflow.updated_at = datetime.fromisoformat(data["updated_at"])
        
        # 设置元数据和状态
        workflow.metadata = data.get("metadata", {})
        workflow.status = data.get("status", "draft")
        
        # 添加步骤
        for step_id, step_data in data.get("steps", {}).items():
            try:
                step = WorkflowStep.from_dict(step_data, function_registry)
                workflow.add_step(step)
            except Exception as e:
                logger.error(f"加载步骤失败: {step_data.get('name')} - {str(e)}")
        
        return workflow
    
    def save(self, file_path: str) -> None:
        """
        保存工作流到文件
        
        参数:
            file_path: 文件路径
        """
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
                
            logger.info(f"工作流已保存: {file_path}")
        except Exception as e:
            logger.error(f"保存工作流失败: {file_path} - {str(e)}")
            raise
    
    @classmethod
    def load(cls, file_path: str, function_registry: Dict[str, Callable]) -> 'Workflow':
        """
        从文件加载工作流
        
        参数:
            file_path: 文件路径
            function_registry: 函数注册表 {函数名: 函数对象}
            
        返回:
            工作流实例
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            workflow = cls.from_dict(data, function_registry)
            logger.info(f"工作流已加载: {file_path}")
            return workflow
        except Exception as e:
            logger.error(f"加载工作流失败: {file_path} - {str(e)}")
            raise
    
    def set_metadata(self, key: str, value: Any) -> None:
        """
        设置元数据
        
        参数:
            key: 元数据键
            value: 元数据值
        """
        self.metadata[key] = value
        self.updated_at = datetime.now()
    
    def set_status(self, status: str) -> None:
        """
        设置工作流状态
        
        参数:
            status: 状态字符串 (draft, active, deprecated)
        """
        valid_statuses = ["draft", "active", "deprecated"]
        if status not in valid_statuses:
            raise ValueError(f"无效的工作流状态: {status}，有效值: {', '.join(valid_statuses)}")
        
        self.status = status
        self.updated_at = datetime.now()
        logger.info(f"工作流 '{self.name}' 状态已更新为: {status}")
    
    def clone(self) -> 'Workflow':
        """
        克隆工作流
        
        返回:
            工作流的克隆副本
        """
        # 创建一个新的工作流字典
        workflow_dict = self.to_dict()
        # 生成新的ID
        workflow_dict["id"] = str(uuid.uuid4())
        # 更新时间
        now = datetime.now()
        workflow_dict["created_at"] = now.isoformat()
        workflow_dict["updated_at"] = now.isoformat()
        
        # 从字典创建新的工作流实例
        cloned = Workflow.from_dict(workflow_dict, function_registry={})
        return cloned


class WorkflowTemplateModel(BaseModel):
    """工作流模板模型，用于工作流模板的标准化表示"""
    
    name: str = Field(..., description="模板名称")
    description: str = Field("", description="模板描述")
    version: str = Field("1.0.0", description="模板版本")
    category: str = Field("general", description="模板分类")
    tags: List[str] = Field(default_factory=list, description="模板标签")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="创建时间")
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="更新时间")
    author: str = Field("system", description="作者")
    steps_count: int = Field(0, description="步骤数量")
    thumbnail: Optional[str] = Field(None, description="缩略图URL")
    difficulty: str = Field("medium", description="难度级别 (easy, medium, hard)")
    estimated_time: Optional[int] = Field(None, description="预计完成时间(分钟)")
    
    class Config:
        arbitrary_types_allowed = True 