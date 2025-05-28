from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from apps.api.models import get_db
from apps.api.models.database import GenerationTask, Template
from apps.api.services.file_service import FileService
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/files")
file_service = FileService()

@router.get("/ppt/{task_id}/download")
async def download_ppt(task_id: str, db: Session = Depends(get_db)):
    """下载生成的PPT文件
    
    Args:
        task_id: 任务ID
        db: 数据库会话
        
    Returns:
        PPT文件流
    """
    # 检查任务是否存在并已完成
    task = db.query(GenerationTask).filter(GenerationTask.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在: id={task_id}"
        )
    
    if task.status != "completed" or not task.output_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"任务未完成或输出文件不存在，当前状态: {task.status}"
        )
    
    # 检查文件是否存在
    if not os.path.exists(task.output_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="输出文件不存在"
        )
    
    return FileResponse(
        path=task.output_path,
        filename=f"presentation_{task_id}.pptx",
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )

@router.get("/templates/{template_id}/preview")
async def get_template_preview(template_id: int, slide_index: int = 0, db: Session = Depends(get_db)):
    """获取模板预览图
    
    Args:
        template_id: 模板ID
        slide_index: 幻灯片索引，默认0表示首页
        db: 数据库会话
        
    Returns:
        预览图片流
    """
    # 检查模板是否存在
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"模板不存在: id={template_id}"
        )
    
    # 获取预览图路径
    preview_dir = Path(template.preview_path).parent if template.preview_path else None
    if not preview_dir or not preview_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模板预览图不存在"
        )
    
    # 寻找对应索引的预览图
    preview_file = preview_dir / f"slide_{slide_index}.png"
    if not preview_file.exists():
        preview_file = list(preview_dir.glob("slide_*.png"))[0] if list(preview_dir.glob("slide_*.png")) else None
    
    if not preview_file or not preview_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"幻灯片预览图不存在: index={slide_index}"
        )
    
    return FileResponse(
        path=str(preview_file),
        media_type="image/png"
    )

@router.get("/ppt/{task_id}/slides/{slide_index}")
async def get_slide_preview(task_id: str, slide_index: int, db: Session = Depends(get_db)):
    """获取任务幻灯片预览图
    
    Args:
        task_id: 任务ID
        slide_index: 幻灯片索引
        db: 数据库会话
        
    Returns:
        幻灯片预览图片流
    """
    # 检查任务是否存在
    task = db.query(GenerationTask).filter(GenerationTask.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在: id={task_id}"
        )
    
    # 获取幻灯片预览图路径
    if not task.output_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="任务未完成或输出路径不存在"
        )
    
    slides_dir = Path(task.output_path).parent / "slides"
    if not slides_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="幻灯片预览目录不存在"
        )
    
    # 寻找对应索引的预览图
    preview_file = slides_dir / f"slide_{slide_index}.png"
    if not preview_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"幻灯片预览图不存在: index={slide_index}"
        )
    
    return FileResponse(
        path=str(preview_file),
        media_type="image/png"
    ) 