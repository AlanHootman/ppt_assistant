from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from apps.api.models import get_db
from apps.api.models.database import GenerationTask, Template
from apps.api.dependencies.auth import get_current_active_user
from apps.api.services.redis_service import RedisService
from apps.api.tasks.ppt_generation import generate_ppt_task
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import uuid
from datetime import datetime

router = APIRouter(prefix="/ppt")
redis_service = RedisService()

# 标准API响应格式
class ApiResponse(BaseModel):
    code: int = 200
    message: str
    data: Optional[Dict[str, Any]] = None

class GenerationRequest(BaseModel):
    template_id: int
    markdown_content: str
    enable_multimodal_validation: bool = False
    
class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: int = 0
    current_step: Optional[str] = None
    step_description: Optional[str] = None
    file_url: Optional[str] = None
    preview_images: Optional[list] = None
    error: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

@router.post("/generate", response_model=ApiResponse)
async def create_generation_task(
    request: GenerationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """创建PPT生成任务
    
    Args:
        request: 生成请求数据
        background_tasks: 后台任务
        db: 数据库会话
        
    Returns:
        包含任务ID和状态的响应
    """
    # 检查模板是否存在
    template = db.query(Template).filter(Template.id == request.template_id).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"模板不存在: id={request.template_id}"
        )
    
    # 检查模板状态
    if template.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"模板未准备就绪，当前状态: {template.status}"
        )
    
    # 生成任务ID
    task_id = str(uuid.uuid4())
    
    # 创建任务记录
    task = GenerationTask(
        id=task_id,
        template_id=request.template_id,
        markdown_content=request.markdown_content,
        status="pending",
        created_at=datetime.utcnow()
    )
    
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # 更新Redis状态
    redis_service.update_task_status(
        task_id,
        status="pending",
        progress=0,
        current_step="queued",
        step_description="任务已加入队列",
        created_at=task.created_at.isoformat()
    )
    
    # 提交Celery任务，使用API生成的task_id
    generate_ppt_task.apply_async(
        args=[{
            "template_id": request.template_id,
            "markdown_content": request.markdown_content,
            "enable_multimodal_validation": request.enable_multimodal_validation
        }],
        task_id=task_id  # 强制使用API生成的task_id
    )
    
    # 返回标准格式响应
    return ApiResponse(
        code=201,
        message="PPT生成任务已创建",
        data={
            "task_id": task_id,
            "status": "pending",
            "created_at": task.created_at.isoformat()
        }
    )

@router.get("/tasks/{task_id}", response_model=ApiResponse)
async def get_task_status(
    task_id: str,
    db: Session = Depends(get_db)
):
    """获取任务状态
    
    Args:
        task_id: 任务ID
        db: 数据库会话
        
    Returns:
        任务状态信息
    """
    # 检查任务是否存在
    task = db.query(GenerationTask).filter(GenerationTask.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在: id={task_id}"
        )
    
    # 从Redis获取最新状态
    status_data = redis_service.get_task_status(task_id)
    
    if not status_data:
        # 如果Redis中没有状态，使用数据库中的状态
        status_data = {
            "status": task.status,
            "progress": task.progress,
            "current_step": task.current_step,
            "step_description": task.step_description,
            "created_at": task.created_at.isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
    
    # 确保返回的数据包含task_id
    status_data["task_id"] = task_id
    
    # 转换日期字符串为datetime对象用于验证
    created_at = task.created_at
    updated_at = None
    completed_at = None
    
    if "created_at" in status_data and isinstance(status_data["created_at"], str):
        created_at = datetime.fromisoformat(status_data["created_at"])
    
    if "updated_at" in status_data and isinstance(status_data["updated_at"], str):
        updated_at = datetime.fromisoformat(status_data["updated_at"])
    
    if "completed_at" in status_data and isinstance(status_data["completed_at"], str):
        completed_at = datetime.fromisoformat(status_data["completed_at"])
    
    # 准备响应数据
    task_data = {**status_data}
    
    # 转换回字符串格式用于JSON响应
    if created_at:
        task_data["created_at"] = created_at.isoformat()
    if updated_at:
        task_data["updated_at"] = updated_at.isoformat()
    if completed_at:
        task_data["completed_at"] = completed_at.isoformat()
    
    # 返回标准格式响应
    return ApiResponse(
        code=200,
        message="获取任务状态成功",
        data=task_data
    )

@router.delete("/tasks/{task_id}", response_model=ApiResponse)
async def cancel_task(
    task_id: str,
    db: Session = Depends(get_db)
):
    """取消任务
    
    Args:
        task_id: 任务ID
        db: 数据库会话
        
    Returns:
        取消结果
    """
    # 检查任务是否存在
    task = db.query(GenerationTask).filter(GenerationTask.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在: id={task_id}"
        )
    
    # 检查任务是否可以取消
    if task.status in ["completed", "failed", "cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"任务已经 {task.status}，无法取消"
        )
    
    # 更新任务状态
    task.status = "cancelled"
    db.commit()
    
    # 更新Redis状态
    redis_service.update_task_status(
        task_id,
        status="cancelled",
        progress=task.progress,
        current_step="cancelled",
        step_description="任务已取消"
    )
    
    # 发布WebSocket消息
    redis_service.publish_task_update(task_id, {
        "status": "cancelled",
        "progress": task.progress,
        "current_step": "cancelled",
        "step_description": "任务已取消"
    })
    
    # 返回标准格式响应
    return ApiResponse(
        code=200,
        message="任务已取消",
        data={
            "task_id": task_id,
            "status": "cancelled"
        }
    ) 