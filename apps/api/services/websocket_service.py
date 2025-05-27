from fastapi import WebSocket
from typing import Dict, List
import json
import asyncio
from apps.api.services.redis_service import RedisService

class WebSocketManager:
    """WebSocket连接管理器，处理WebSocket连接和消息分发"""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.redis_service = RedisService()
    
    async def connect(self, websocket: WebSocket, task_id: str):
        """建立WebSocket连接
        
        Args:
            websocket: WebSocket连接对象
            task_id: 任务ID
        """
        await websocket.accept()
        
        if task_id not in self.active_connections:
            self.active_connections[task_id] = []
        
        self.active_connections[task_id].append(websocket)
        
        # 发送当前任务状态
        current_status = self.redis_service.get_task_status(task_id)
        if current_status:
            await websocket.send_text(json.dumps(current_status))
        
        # 启动Redis订阅
        asyncio.create_task(self._listen_redis_updates(task_id))
    
    def disconnect(self, websocket: WebSocket, task_id: str):
        """断开WebSocket连接
        
        Args:
            websocket: WebSocket连接对象
            task_id: 任务ID
        """
        if task_id in self.active_connections:
            if websocket in self.active_connections[task_id]:
                self.active_connections[task_id].remove(websocket)
            
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]
    
    async def send_task_update(self, task_id: str, data: dict):
        """向指定任务的所有连接发送更新
        
        Args:
            task_id: 任务ID
            data: 更新数据
        """
        if task_id in self.active_connections:
            message = json.dumps(data)
            disconnected = []
            
            for websocket in self.active_connections[task_id]:
                try:
                    await websocket.send_text(message)
                except Exception:
                    disconnected.append(websocket)
            
            # 清理断开的连接
            for ws in disconnected:
                if ws in self.active_connections[task_id]:
                    self.active_connections[task_id].remove(ws)
    
    async def _listen_redis_updates(self, task_id: str):
        """监听Redis任务更新
        
        Args:
            task_id: 任务ID
        """
        pubsub = self.redis_service.subscribe_task_updates(task_id)
        
        try:
            for message in pubsub.listen():
                if message['type'] == 'message':
                    data = json.loads(message['data'])
                    await self.send_task_update(task_id, data)
        except Exception as e:
            print(f"Redis subscription error: {e}")
        finally:
            pubsub.unsubscribe()

# 全局WebSocket管理器实例
websocket_manager = WebSocketManager() 