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
    
    def cache_template_list(self, templates: list, expire_seconds: int = 300):
        """缓存模板列表
        
        Args:
            templates: 模板列表
            expire_seconds: 缓存过期时间（秒）
        """
        key = "templates:list"
        self.redis_client.setex(
            key,
            int(expire_seconds),  # 确保过期时间是整数
            json.dumps(templates)
        )
    
    def get_cached_template_list(self) -> Optional[list]:
        """获取缓存的模板列表
        
        Returns:
            模板列表，如果缓存不存在则返回None
        """
        key = "templates:list"
        data = self.redis_client.get(key)
        return json.loads(data) if data else None
    
    def invalidate_template_cache(self):
        """清除模板缓存"""
        pattern = "templates:*"
        keys = self.redis_client.keys(pattern)
        if keys:
            self.redis_client.delete(*keys) 