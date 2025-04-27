"""
函数注册表模块，用于注册和管理工作流中使用的函数。
"""
import inspect
import logging
from typing import Dict, Any, Callable, Optional, List, Set, Tuple
from functools import wraps

# 配置日志
logger = logging.getLogger("function_registry")

class FunctionRegistry:
    """函数注册表，用于注册和管理工作流中使用的函数"""
    
    def __init__(self):
        """初始化函数注册表"""
        self._functions: Dict[str, Callable] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._categories: Dict[str, Set[str]] = {}
        
        logger.debug("初始化函数注册表")
    
    def register(self, 
                 func: Optional[Callable] = None, 
                 *,
                 name: Optional[str] = None,
                 category: str = "general",
                 description: str = "",
                 tags: Optional[List[str]] = None,
                 metadata: Optional[Dict[str, Any]] = None) -> Callable:
        """
        注册函数到注册表中
        
        可以作为装饰器使用:
        
        @registry.register
        def my_function():
            pass
            
        @registry.register(name="custom_name", category="data_processing")
        def my_function():
            pass
        
        参数:
            func: 要注册的函数
            name: 自定义函数名称（可选，默认使用函数的原始名称）
            category: 函数类别
            description: 函数描述
            tags: 标签列表
            metadata: 附加元数据
            
        返回:
            装饰器函数或被装饰的函数
        """
        # 作为装饰器使用，无参数
        if func is not None and callable(func):
            return self._register_function(func)
        
        # 作为装饰器使用，有参数
        def decorator(f):
            return self._register_function(
                f, 
                custom_name=name,
                category=category,
                description=description,
                tags=tags or [],
                metadata=metadata or {}
            )
        return decorator
    
    def _register_function(self, 
                          func: Callable, 
                          custom_name: Optional[str] = None,
                          category: str = "general",
                          description: str = "",
                          tags: Optional[List[str]] = None,
                          metadata: Optional[Dict[str, Any]] = None) -> Callable:
        """
        注册函数的内部实现
        
        参数:
            func: 要注册的函数
            custom_name: 自定义函数名称
            category: 函数类别
            description: 函数描述
            tags: 标签列表
            metadata: 附加元数据
            
        返回:
            被装饰的函数
        """
        # 获取函数名称
        func_name = custom_name or func.__name__
        
        # 如果函数名称已存在，发出警告并添加后缀
        original_name = func_name
        counter = 1
        while func_name in self._functions:
            func_name = f"{original_name}_{counter}"
            counter += 1
            logger.warning(f"函数名称 '{original_name}' 已存在，重命名为 '{func_name}'")
        
        # 获取函数签名信息
        sig = inspect.signature(func)
        param_info = []
        for name, param in sig.parameters.items():
            if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.VAR_POSITIONAL, 
                              inspect.Parameter.VAR_KEYWORD):
                continue
            
            default = "N/A"
            if param.default is not inspect.Parameter.empty:
                default = repr(param.default)
            
            param_info.append({
                "name": name,
                "type": str(param.annotation) if param.annotation is not inspect.Parameter.empty else "Any",
                "default": default,
                "required": param.default is inspect.Parameter.empty
            })
        
        # 提取返回值类型
        return_type = "Any"
        if sig.return_annotation is not inspect.Parameter.empty:
            return_type = str(sig.return_annotation)
        
        # 注册函数
        self._functions[func_name] = func
        
        # 存储元数据
        self._metadata[func_name] = {
            "original_name": func.__name__,
            "module": func.__module__,
            "description": description or func.__doc__ or "",
            "category": category,
            "tags": tags or [],
            "parameters": param_info,
            "return_type": return_type,
            "source": inspect.getsource(func) if not func.__module__ == "builtins" else "Built-in function"
        }
        
        if metadata:
            self._metadata[func_name].update(metadata)
        
        # 将函数添加到分类中
        if category not in self._categories:
            self._categories[category] = set()
        self._categories[category].add(func_name)
        
        logger.info(f"注册函数: {func_name} (类别: {category})")
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger.debug(f"调用函数: {func_name}")
            return func(*args, **kwargs)
        
        return wrapper
    
    def get(self, name: str) -> Optional[Callable]:
        """
        获取注册的函数
        
        参数:
            name: 函数名称
            
        返回:
            函数对象或None（如果不存在）
        """
        return self._functions.get(name)
    
    def get_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取函数的元数据
        
        参数:
            name: 函数名称
            
        返回:
            元数据字典或None（如果不存在）
        """
        return self._metadata.get(name)
    
    def list_functions(self, category: Optional[str] = None) -> List[Tuple[str, Dict[str, Any]]]:
        """
        列出注册的函数
        
        参数:
            category: 可选的类别过滤器
            
        返回:
            (函数名, 元数据)的元组列表
        """
        if category:
            # 仅返回特定类别的函数
            if category not in self._categories:
                return []
            return [(name, self._metadata[name]) for name in self._categories[category]]
        
        # 返回所有函数
        return [(name, metadata) for name, metadata in self._metadata.items()]
    
    def list_categories(self) -> List[str]:
        """
        列出所有函数类别
        
        返回:
            类别列表
        """
        return list(self._categories.keys())
    
    def search(self, query: str) -> List[Tuple[str, Dict[str, Any]]]:
        """
        搜索函数
        
        参数:
            query: 搜索查询
            
        返回:
            匹配的(函数名, 元数据)元组列表
        """
        query = query.lower()
        results = []
        
        for name, metadata in self._metadata.items():
            # 检查名称
            if query in name.lower():
                results.append((name, metadata))
                continue
            
            # 检查描述
            if query in metadata.get("description", "").lower():
                results.append((name, metadata))
                continue
                
            # 检查标签
            if any(query in tag.lower() for tag in metadata.get("tags", [])):
                results.append((name, metadata))
                continue
        
        return results
    
    def deregister(self, name: str) -> bool:
        """
        从注册表中移除函数
        
        参数:
            name: 函数名称
            
        返回:
            如果成功删除则为True，否则为False
        """
        if name not in self._functions:
            logger.warning(f"尝试取消注册不存在的函数: {name}")
            return False
        
        # 获取函数的类别
        category = self._metadata[name]["category"]
        
        # 从函数字典中移除
        del self._functions[name]
        
        # 从元数据字典中移除
        del self._metadata[name]
        
        # 从类别集合中移除
        if category in self._categories and name in self._categories[category]:
            self._categories[category].remove(name)
            
            # 如果类别为空，删除类别
            if len(self._categories[category]) == 0:
                del self._categories[category]
        
        logger.info(f"取消注册函数: {name}")
        return True
    
    def clear(self) -> None:
        """清空注册表中的所有函数"""
        self._functions.clear()
        self._metadata.clear()
        self._categories.clear()
        logger.info("清空函数注册表")
    
    def __contains__(self, name: str) -> bool:
        """
        检查函数是否在注册表中
        
        参数:
            name: 函数名称
            
        返回:
            如果函数在注册表中则为True，否则为False
        """
        return name in self._functions
    
    def __getitem__(self, name: str) -> Callable:
        """
        获取注册的函数
        
        参数:
            name: 函数名称
            
        返回:
            函数对象
            
        异常:
            KeyError: 如果函数不存在
        """
        if name not in self._functions:
            raise KeyError(f"函数 '{name}' 不在注册表中")
        return self._functions[name]
    
    def __len__(self) -> int:
        """
        获取注册表中的函数数量
        
        返回:
            函数数量
        """
        return len(self._functions)
    
    def as_dict(self) -> Dict[str, Callable]:
        """
        将注册表作为字典返回
        
        返回:
            {函数名: 函数对象}的字典
        """
        return self._functions.copy()

# 创建全局函数注册表实例
registry = FunctionRegistry()