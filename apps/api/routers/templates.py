from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from apps.api.models import get_db
from apps.api.models.database import Template, User
from apps.api.dependencies.auth import get_current_active_user
from apps.api.services.redis_service import RedisService
from apps.api.services.file_service import FileService
from apps.api.tasks.template_analysis import analyze_template_task
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import json
from datetime import datetime

router = APIRouter()
redis_service = RedisService()
file_service = FileService()

class TemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    tags: Optional[str] = None  # JSON格式的标签列表

class TemplateResponse(TemplateBase):
    id: int
    file_path: str
    preview_path: Optional[str] = None
    analysis_path: Optional[str] = None
    status: str
    upload_time: datetime
    analysis_time: Optional[datetime] = None
    
    class Config:
        from_attributes = True

@router.post("/", response_model=TemplateResponse)
async def upload_template(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    file: UploadFile = File(...),
    enable_tracking: bool = Form(False),
    db: Session = Depends(get_db)
):
    """上传PPT模板
    
    Args:
        name: 模板名称
        description: 模板描述
        tags: 模板标签（以逗号分隔）
        file: 上传的模板文件
        enable_tracking: 是否启用MLflow跟踪功能
        db: 数据库会话
        
    Returns:
        创建的模板信息
    """
    # 检查文件类型
    if not file.filename.endswith('.pptx'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只支持.pptx格式的文件"
        )
    
    # 创建模板记录
    template = Template(
        name=name,
        description=description,
        tags=tags,
        file_path="",  # 临时路径，稍后更新
        status="uploading",
        upload_time=datetime.utcnow(),
        created_by=1  # 固定为ID为1的用户
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    try:
        # 保存文件
        file_info = await file_service.save_template_file(file, template.id)
        
        # 更新模板路径
        template.file_path = file_info["file_path"]
        template.status = "uploaded"
        db.commit()
        
        # 清除模板缓存
        redis_service.invalidate_template_cache()
        
        # 触发模板分析任务
        template.status = "analyzing"
        db.commit()
        
        analyze_template_task.delay({
            "template_id": template.id,
            "file_path": template.file_path,
            "enable_tracking": enable_tracking
        })
        
        return template
    
    except Exception as e:
        # 发生异常时，将模板状态设为失败
        template.status = "failed"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"模板上传失败: {str(e)}"
        )

@router.get("/", response_model=List[TemplateResponse])
async def list_templates(
    skip: int = 0, 
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取模板列表
    
    Args:
        skip: 分页起始位置
        limit: 分页大小
        status: 模板状态过滤
        db: 数据库会话
        
    Returns:
        模板列表
    """
    # 尝试从缓存获取
    if not status and skip == 0 and limit == 100:
        cached_templates = redis_service.get_cached_template_list()
        if cached_templates:
            return cached_templates
    
    # 构建查询
    query = db.query(Template)
    
    # 应用状态过滤
    if status:
        query = query.filter(Template.status == status)
    
    # 执行查询
    templates = query.offset(skip).limit(limit).all()
    
    # 如果是默认查询，缓存结果
    if not status and skip == 0 and limit == 100:
        redis_service.cache_template_list(templates)
    
    return templates

@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    """获取模板详情
    
    Args:
        template_id: 模板ID
        db: 数据库会话
        
    Returns:
        模板详情
    """
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"模板不存在: id={template_id}"
        )
    
    return template

@router.delete("/{template_id}")
async def delete_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    """删除模板
    
    Args:
        template_id: 模板ID
        db: 数据库会话
        
    Returns:
        删除结果
    """
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"模板不存在: id={template_id}"
        )
    
    # 删除文件
    file_service.delete_template_files(template_id)
    
    # 删除数据库记录
    db.delete(template)
    db.commit()
    
    # 清除缓存
    redis_service.invalidate_template_cache()
    
    return {"message": "模板已删除"}

@router.get("/{template_id}/analysis")
async def get_template_analysis(
    template_id: int,
    db: Session = Depends(get_db)
):
    """获取模板分析结果
    
    Args:
        template_id: 模板ID
        db: 数据库会话
        
    Returns:
        模板分析结果
    """
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"模板不存在: id={template_id}"
        )
    
    if template.status != "ready" or not template.analysis_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"模板分析未完成，当前状态: {template.status}"
        )
    
    # 读取分析结果
    try:
        with open(template.analysis_path, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        return analysis_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"读取分析结果失败: {str(e)}"
        )

@router.post("/{template_id}/analyze")
async def request_template_analysis(
    template_id: int,
    enable_tracking: bool = Query(False, description="是否启用MLflow跟踪功能"),
    db: Session = Depends(get_db)
):
    """请求分析模板
    
    Args:
        template_id: 模板ID
        enable_tracking: 是否启用MLflow跟踪功能
        db: 数据库会话
        
    Returns:
        分析任务信息
    """
    # 检查模板是否存在
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"模板不存在: id={template_id}"
        )
    
    # 更新模板状态
    template.status = "analyzing"
    db.commit()
    
    # 触发分析任务
    task = analyze_template_task.delay({
        "template_id": template_id,
        "file_path": template.file_path,
        "enable_tracking": enable_tracking
    })
    
    return {
        "task_id": task.id,
        "template_id": template_id,
        "status": "analyzing",
        "message": "模板分析任务已提交"
    } 