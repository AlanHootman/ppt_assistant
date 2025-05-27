from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from apps.api.services.websocket_service import websocket_manager
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.websocket("/ws/tasks/{task_id}")
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
            # 保持连接活跃，处理心跳
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info(f"WebSocket连接已断开: task_id={task_id}")
        websocket_manager.disconnect(websocket, task_id)
    except Exception as e:
        logger.exception(f"WebSocket错误: {str(e)}")
        websocket_manager.disconnect(websocket, task_id) 