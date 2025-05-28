from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from apps.api.services.websocket_service import websocket_manager
import logging

logger = logging.getLogger(__name__)

# 创建路由器，指定前缀和标签
router = APIRouter(
    prefix="/ws",
    tags=["websocket"]
)

@router.websocket("/tasks/{task_id}")
async def websocket_task_updates(websocket: WebSocket, task_id: str):
    """任务更新WebSocket端点
    
    Args:
        websocket: WebSocket连接对象
        task_id: 任务ID
    """
    logger.info(f"WebSocket连接请求: task_id={task_id}")
    
    try:
        await websocket_manager.connect(websocket, task_id)
        logger.info(f"WebSocket连接已建立: task_id={task_id}")
        
        while True:
            # 接收任何类型的消息，包括ping
            data = await websocket.receive()
            message_type = data.get("type")
            
            # 根据消息类型处理
            if message_type == "websocket.disconnect":
                logger.info(f"客户端主动断开连接: task_id={task_id}")
                break
            elif message_type == "websocket.receive":
                # 常规消息处理
                if "text" in data:
                    logger.debug(f"收到文本消息: {data['text'][:100]}...")
            elif message_type == "ping":
                # 显式处理ping消息
                logger.debug(f"收到ping消息: task_id={task_id}")
                # FastAPI会自动发送pong响应
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket连接已断开: task_id={task_id}")
        websocket_manager.disconnect(websocket, task_id)
    except Exception as e:
        logger.exception(f"WebSocket错误: {str(e)}")
        websocket_manager.disconnect(websocket, task_id) 