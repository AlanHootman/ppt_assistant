"""
工作流工厂模块，提供工作流创建、注册和管理功能。
"""
import os
import json
import logging
import importlib
from typing import Dict, List, Any, Optional, Callable, Type, Union
from pathlib import Path

from core.engine.workflow import Workflow, WorkflowStep

# 配置日志
logger = logging.getLogger("workflow_factory")

class WorkflowFactory:
    """工作流工厂类，用于创建和管理工作流实例"""
    
    def __init__(self, 
                 workflows_dir: Optional[str] = None,
                 templates_dir: Optional[str] = None,
                 steps_module: Optional[str] = None):
        """
        初始化工作流工厂
        
        参数:
            workflows_dir: 工作流保存目录
            templates_dir: 工作流模板目录
            steps_module: 步骤函数所在的模块路径
        """
        # 设置默认目录
        self.workflows_dir = workflows_dir or os.path.join(os.getcwd(), "workflows")
        self.templates_dir = templates_dir or os.path.join(os.getcwd(), "templates")
        self.steps_module = steps_module
        
        # 确保目录存在
        os.makedirs(self.workflows_dir, exist_ok=True)
        os.makedirs(self.templates_dir, exist_ok=True)
        
        # 初始化缓存
        self._step_functions_cache: Dict[str, Callable] = {}
        self._templates_cache: Dict[str, Dict] = {}
        
        logger.info(f"工作流工厂初始化完成，工作流目录: {self.workflows_dir}, 模板目录: {self.templates_dir}")
    
    def create_workflow(self, 
                       name: str,
                       description: str = "",
                       template_name: Optional[str] = None,
                       **kwargs) -> Workflow:
        """
        创建新的工作流
        
        参数:
            name: 工作流名称
            description: 工作流描述
            template_name: 模板名称，如果提供，将基于模板创建工作流
            **kwargs: 传递给工作流初始化的其他参数
            
        返回:
            创建的工作流实例
        """
        if template_name:
            return self._create_from_template(template_name, name, description, **kwargs)
        
        # 创建新的空工作流
        workflow = Workflow(name=name, description=description, **kwargs)
        logger.info(f"创建新工作流: {name} (ID: {workflow.id})")
        
        return workflow
    
    def _create_from_template(self, 
                             template_name: str, 
                             name: str,
                             description: str = "",
                             **kwargs) -> Workflow:
        """
        从模板创建工作流
        
        参数:
            template_name: 模板名称
            name: 工作流名称
            description: 工作流描述
            **kwargs: 传递给工作流初始化的其他参数
            
        返回:
            创建的工作流实例
        """
        template_path = os.path.join(self.templates_dir, f"{template_name}.json")
        
        if not os.path.exists(template_path):
            logger.error(f"模板不存在: {template_path}")
            raise FileNotFoundError(f"模板不存在: {template_name}")
        
        # 读取模板
        with open(template_path, 'r', encoding='utf-8') as f:
            template = json.load(f)
        
        # 创建工作流
        workflow = Workflow(
            name=name,
            description=description or template.get("description", ""),
            error_handling=template.get("error_handling", "stop"),
            **kwargs
        )
        
        # 添加步骤
        step_functions = self._get_step_functions()
        for step_def in template.get("steps", []):
            func_name = step_def.get("func_name")
            
            if func_name not in step_functions:
                logger.warning(f"找不到步骤函数: {func_name}，跳过该步骤")
                continue
            
            step = WorkflowStep(
                name=step_def.get("name", f"Step_{len(workflow.steps)+1}"),
                func=step_functions[func_name],
                input_mapping=step_def.get("input_mapping", {}),
                output_mapping=step_def.get("output_mapping", {}),
                description=step_def.get("description", ""),
                timeout=step_def.get("timeout")
            )
            
            workflow.add_step(step)
        
        logger.info(f"从模板 '{template_name}' 创建工作流: {name} (ID: {workflow.id})")
        return workflow
    
    def save_workflow(self, workflow: Workflow, as_template: bool = False) -> str:
        """
        保存工作流
        
        参数:
            workflow: 要保存的工作流
            as_template: 是否作为模板保存
            
        返回:
            保存的文件路径
        """
        if as_template:
            file_path = os.path.join(self.templates_dir, f"{workflow.name}.json")
            logger.info(f"将工作流 '{workflow.name}' 保存为模板")
        else:
            file_path = os.path.join(self.workflows_dir, f"{workflow.id}.json")
        
        workflow.save(file_path)
        return file_path
    
    def load_workflow(self, workflow_id: str) -> Workflow:
        """
        加载工作流
        
        参数:
            workflow_id: 工作流ID
            
        返回:
            加载的工作流实例
        """
        file_path = os.path.join(self.workflows_dir, f"{workflow_id}.json")
        
        if not os.path.exists(file_path):
            logger.error(f"工作流不存在: {file_path}")
            raise FileNotFoundError(f"工作流不存在: {workflow_id}")
        
        step_functions = self._get_step_functions()
        return Workflow.load(file_path, step_functions)
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """
        列出所有保存的工作流
        
        返回:
            工作流信息列表
        """
        workflows = []
        
        for filename in os.listdir(self.workflows_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(self.workflows_dir, filename)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        workflow_data = json.load(f)
                    
                    workflows.append({
                        "id": workflow_data.get("id"),
                        "name": workflow_data.get("name"),
                        "description": workflow_data.get("description", ""),
                        "created_at": workflow_data.get("created_at"),
                        "updated_at": workflow_data.get("updated_at"),
                        "steps_count": len(workflow_data.get("steps", [])),
                        "file_path": file_path
                    })
                except Exception as e:
                    logger.warning(f"读取工作流文件失败: {file_path}, 错误: {str(e)}")
        
        return workflows
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """
        列出所有可用的工作流模板
        
        返回:
            模板信息列表
        """
        templates = []
        
        for filename in os.listdir(self.templates_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(self.templates_dir, filename)
                template_name = os.path.splitext(filename)[0]
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        template_data = json.load(f)
                    
                    templates.append({
                        "name": template_name,
                        "description": template_data.get("description", ""),
                        "steps_count": len(template_data.get("steps", [])),
                        "file_path": file_path
                    })
                except Exception as e:
                    logger.warning(f"读取模板文件失败: {file_path}, 错误: {str(e)}")
        
        return templates
    
    def save_as_template(self, workflow: Workflow, template_name: Optional[str] = None) -> str:
        """
        将工作流保存为模板
        
        参数:
            workflow: 要保存的工作流
            template_name: 模板名称，如果不提供则使用工作流名称
            
        返回:
            保存的模板文件路径
        """
        name = template_name or workflow.name
        template_path = os.path.join(self.templates_dir, f"{name}.json")
        
        # 创建模板数据
        template_data = {
            "name": name,
            "description": workflow.description,
            "error_handling": workflow.error_handling,
            "steps": [step.to_dict() for step in workflow.steps]
        }
        
        # 保存到文件
        with open(template_path, 'w', encoding='utf-8') as f:
            json.dump(template_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"工作流 '{workflow.name}' 已保存为模板: {name}")
        return template_path
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """
        删除工作流
        
        参数:
            workflow_id: 工作流ID
            
        返回:
            是否成功删除
        """
        file_path = os.path.join(self.workflows_dir, f"{workflow_id}.json")
        
        if not os.path.exists(file_path):
            logger.warning(f"要删除的工作流不存在: {workflow_id}")
            return False
        
        try:
            os.remove(file_path)
            logger.info(f"已删除工作流: {workflow_id}")
            return True
        except Exception as e:
            logger.error(f"删除工作流失败: {workflow_id}, 错误: {str(e)}")
            return False
    
    def delete_template(self, template_name: str) -> bool:
        """
        删除模板
        
        参数:
            template_name: 模板名称
            
        返回:
            是否成功删除
        """
        file_path = os.path.join(self.templates_dir, f"{template_name}.json")
        
        if not os.path.exists(file_path):
            logger.warning(f"要删除的模板不存在: {template_name}")
            return False
        
        try:
            os.remove(file_path)
            logger.info(f"已删除模板: {template_name}")
            return True
        except Exception as e:
            logger.error(f"删除模板失败: {template_name}, 错误: {str(e)}")
            return False
    
    def _get_step_functions(self) -> Dict[str, Callable]:
        """
        获取步骤函数字典
        
        返回:
            函数名到函数对象的映射
        """
        # 如果已有缓存，直接返回
        if self._step_functions_cache:
            return self._step_functions_cache
        
        functions = {}
        
        # 如果指定了步骤模块，尝试导入
        if self.steps_module:
            try:
                module = importlib.import_module(self.steps_module)
                
                # 获取所有可能的函数
                for name in dir(module):
                    if name.startswith('_'):
                        continue
                    
                    attr = getattr(module, name)
                    if callable(attr):
                        functions[name] = attr
                
                logger.info(f"从模块 '{self.steps_module}' 加载了 {len(functions)} 个步骤函数")
            except ImportError as e:
                logger.error(f"导入步骤模块失败: {self.steps_module}, 错误: {str(e)}")
        
        # 缓存结果
        self._step_functions_cache = functions
        return functions
    
    def register_step_function(self, func: Callable) -> None:
        """
        注册步骤函数
        
        参数:
            func: 要注册的函数
        """
        self._step_functions_cache[func.__name__] = func
        logger.info(f"注册步骤函数: {func.__name__}")
    
    def get_workflow_file_path(self, workflow_id: str) -> str:
        """
        获取工作流文件路径
        
        参数:
            workflow_id: 工作流ID
            
        返回:
            文件路径
        """
        return os.path.join(self.workflows_dir, f"{workflow_id}.json")
    
    def get_template_file_path(self, template_name: str) -> str:
        """
        获取模板文件路径
        
        参数:
            template_name: 模板名称
            
        返回:
            文件路径
        """
        return os.path.join(self.templates_dir, f"{template_name}.json") 