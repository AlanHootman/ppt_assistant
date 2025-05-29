from fastapi import WebSocket
from typing import Dict, List
import json
import asyncio
import logging
from apps.api.services.redis_service import RedisService

logger = logging.getLogger(__name__)

class WebSocketManager:
    """WebSocket连接管理器，处理WebSocket连接和消息分发"""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.redis_service = RedisService()
        self.task_listeners: Dict[str, asyncio.Task] = {}
        logger.info("WebSocket管理器初始化完成")
    
    async def connect(self, websocket: WebSocket, task_id: str):
        """建立WebSocket连接
        
        Args:
            websocket: WebSocket连接对象
            task_id: 任务ID
        """
        await websocket.accept()
        logger.info(f"WebSocket连接已接受: task_id={task_id}")
        
        if task_id not in self.active_connections:
            self.active_connections[task_id] = []
            # 启动Redis订阅，每个任务只需一个监听器
            if task_id not in self.task_listeners or self.task_listeners[task_id].done():
                logger.info(f"启动Redis订阅: task_id={task_id}")
                self.task_listeners[task_id] = asyncio.create_task(self._listen_redis_updates(task_id))
        
        self.active_connections[task_id].append(websocket)
        logger.info(f"WebSocket连接已注册: task_id={task_id}, 当前连接数: {len(self.active_connections[task_id])}")
        
        # 发送当前任务状态
        current_status = self.redis_service.get_task_status(task_id)
        if current_status:
            await websocket.send_json(current_status)
            logger.info(f"已发送当前状态: task_id={task_id}, status={current_status.get('status', 'unknown')}")
    
    def disconnect(self, websocket: WebSocket, task_id: str):
        """断开WebSocket连接
        
        Args:
            websocket: WebSocket连接对象
            task_id: 任务ID
        """
        if task_id in self.active_connections:
            if websocket in self.active_connections[task_id]:
                self.active_connections[task_id].remove(websocket)
                logger.info(f"WebSocket连接已移除: task_id={task_id}, 剩余连接数: {len(self.active_connections[task_id])}")
            
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]
                # 取消Redis监听任务
                if task_id in self.task_listeners and not self.task_listeners[task_id].done():
                    self.task_listeners[task_id].cancel()
                    del self.task_listeners[task_id]
                logger.info(f"任务的所有WebSocket连接已清空: task_id={task_id}")
    
    async def send_task_update(self, task_id: str, data: dict):
        """向指定任务的所有连接发送更新
        
        Args:
            task_id: 任务ID
            data: 更新数据
        """
        if task_id in self.active_connections:
            logger.info(f"准备发送任务更新: task_id={task_id}, status={data.get('status', 'unknown')}, progress={data.get('progress', 'unknown')}")
            
            disconnected = []
            success_count = 0
            
            for websocket in self.active_connections[task_id]:
                try:
                    await websocket.send_json(data)
                    success_count += 1
                except Exception as e:
                    logger.error(f"发送WebSocket消息失败: task_id={task_id}, error={str(e)}")
                    disconnected.append(websocket)
            
            # 清理断开的连接
            for ws in disconnected:
                if ws in self.active_connections[task_id]:
                    self.active_connections[task_id].remove(ws)
            
            if disconnected:
                logger.warning(f"清理了 {len(disconnected)} 个断开的连接: task_id={task_id}")
            
            logger.info(f"任务更新已发送给 {success_count} 个连接: task_id={task_id}")
        else:
            logger.warning(f"没有活跃的WebSocket连接可发送更新: task_id={task_id}")
    
    async def _listen_redis_updates(self, task_id: str):
        """监听Redis任务更新
        
        Args:
            task_id: 任务ID
        """
        pubsub = self.redis_service.subscribe_task_updates(task_id)
        logger.info(f"已订阅Redis任务更新: task_id={task_id}")
        
        try:
            # 创建轮询循环，避免阻塞事件循环
            while True:
                # 非阻塞方式获取消息
                message = pubsub.get_message(timeout=0.01)
                if message:
                    logger.debug(f"收到Redis消息: task_id={task_id}, type={message.get('type')}")
                    
                    if message['type'] == 'message':
                        try:
                            data = json.loads(message['data'])
                            logger.info(f"收到任务更新: task_id={task_id}, status={data.get('status', 'unknown')}, progress={data.get('progress', 'unknown')}")
                            await self.send_task_update(task_id, data)
                        except Exception as e:
                            logger.error(f"处理消息时出错: task_id={task_id}, error={str(e)}")
                
                # 短暂等待避免CPU过度占用
                await asyncio.sleep(0.1)
                
                # 如果没有连接，停止监听
                if task_id not in self.active_connections or not self.active_connections[task_id]:
                    logger.info(f"没有活跃连接，停止Redis监听: task_id={task_id}")
                    break
        except asyncio.CancelledError:
            logger.info(f"Redis监听任务已取消: task_id={task_id}")
        except Exception as e:
            logger.error(f"Redis订阅出错: task_id={task_id}, error={str(e)}")
        finally:
            pubsub.unsubscribe()
            logger.info(f"已取消Redis订阅: task_id={task_id}")

# 全局WebSocket管理器实例
websocket_manager = WebSocketManager() 