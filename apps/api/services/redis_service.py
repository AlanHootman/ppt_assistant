import redis
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from apps.api.config import settings

class RedisService:
    """Redis服务类，用于任务状态管理和WebSocket通信"""
    
    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL)
        self.pubsub = self.redis_client.pubsub()
    
    def update_task_status(self, task_id: str, **kwargs):
        """更新任务状态
        
        Args:
            task_id: 任务ID
            **kwargs: 状态数据，如status, progress, current_step等
        """
        key = f"task:{task_id}:status"
        current_data = self.get_task_status(task_id) or {}
        current_data.update(kwargs)
        current_data["updated_at"] = datetime.utcnow().isoformat()
        
        self.redis_client.setex(
            key, 
            int(timedelta(hours=24).total_seconds()),  # 24小时过期，转换为整数
            json.dumps(current_data)
        )
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态数据，如果任务不存在则返回None
        """
        key = f"task:{task_id}:status"
        data = self.redis_client.get(key)
        return json.loads(data) if data else None
    
    def publish_task_update(self, task_id: str, data: Dict[str, Any]):
        """发布任务更新消息
        
        Args:
            task_id: 任务ID
            data: 更新数据
        """
        channel = f"task_updates:{task_id}"
        self.redis_client.publish(channel, json.dumps(data))
    
    def subscribe_task_updates(self, task_id: str):
        """订阅任务更新
        
        Args:
            task_id: 任务ID
            
        Returns:
            Redis PubSub对象
        """
        channel = f"task_updates:{task_id}"
        self.pubsub.subscribe(channel)
        return self.pubsub
    
    def cache_template_list(self, templates: list, status_filter: str = "ready", expire_seconds: int = 300):
        """缓存模板列表
        
        Args:
            templates: 模板列表
            status_filter: 模板状态过滤器，默认为 ready
            expire_seconds: 缓存过期时间（秒）
        """
        # 根据状态过滤器确定缓存键
        key = f"templates:list:{status_filter}"
        
        # 将ORM对象转换为可序列化的字典
        serializable_templates = []
        for template in templates:
            try:
                # 解析标签，处理各种可能的异常情况
                tags = []
                if template.tags:
                    try:
                        if template.tags.strip():
                            tags = json.loads(template.tags)
                    except json.JSONDecodeError:
                        # 如果JSON解析失败，使用空列表
                        pass
                
                template_dict = {
                    "id": template.id,
                    "name": template.name,
                    "description": template.description,
                    "tags": tags,
                    "file_url": template.file_path,
                    "preview_url": template.preview_path,
                    "status": template.status,
                    "upload_time": template.upload_time.isoformat() if template.upload_time else None,
                }
                serializable_templates.append(template_dict)
            except Exception:
                # 忽略序列化失败的模板
                continue
        
        self.redis_client.setex(
            key,
            int(expire_seconds),  # 确保过期时间是整数
            json.dumps(serializable_templates)
        )
    
    def get_cached_template_list(self, status_filter: str = "ready") -> Optional[list]:
        """获取缓存的模板列表
        
        Args:
            status_filter: 模板状态过滤器，默认为 ready
            
        Returns:
            模板列表，如果缓存不存在则返回None
        """
        key = f"templates:list:{status_filter}"
        data = self.redis_client.get(key)
        
        if not data:
            return None
            
        # 解析JSON数据
        templates_data = json.loads(data)
        
        # 处理日期时间字段
        for template in templates_data:
            # 将ISO格式字符串转回datetime对象
            if template.get('upload_time'):
                template['upload_time'] = datetime.fromisoformat(template['upload_time'])
            if template.get('analysis_time') and template['analysis_time']:
                template['analysis_time'] = datetime.fromisoformat(template['analysis_time'])
                
        return templates_data
    
    def invalidate_template_cache(self, status_filter: str = None):
        """清除模板列表缓存
        
        Args:
            status_filter: 特定状态的缓存，如果为 None，则清除所有状态的缓存
        """
        if status_filter:
            key = f"templates:list:{status_filter}"
            self.redis_client.delete(key)
        else:
            # 获取所有模板缓存键
            pattern = "templates:list:*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
    
    def get_template_analysis_task_id(self, template_id: int) -> Optional[str]:
        """获取模板分析任务ID
        
        Args:
            template_id: 模板ID
            
        Returns:
            任务ID，如果不存在则返回None
        """
        key = f"template:{template_id}:analysis_task"
        return self.redis_client.get(key)
    
    def save_template_analysis_task_id(self, template_id: int, task_id: str):
        """保存模板ID和分析任务ID的关联
        
        Args:
            template_id: 模板ID
            task_id: 任务ID
        """
        key = f"template:{template_id}:analysis_task"
        self.redis_client.set(key, task_id)
    
    def clear_template_analysis_task_id(self, template_id: int):
        """清理模板分析任务ID关联
        
        Args:
            template_id: 模板ID
        """
        key = f"template:{template_id}:analysis_task"
        self.redis_client.delete(key) 