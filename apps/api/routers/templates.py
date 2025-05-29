from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form, Query, BackgroundTasks
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
import logging

# 创建路由器，指定前缀和标签
router = APIRouter(
    prefix="/templates",
    tags=["templates"]
)

redis_service = RedisService()
file_service = FileService()

logger = logging.getLogger(__name__)

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

class ApiResponse(BaseModel):
    code: int = 200
    message: str
    data: Optional[Dict[str, Any]] = None

@router.post("/", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
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
        
        task = analyze_template_task.delay({
            "template_id": template.id,
            "file_path": template.file_path,
            "enable_tracking": enable_tracking
        })
        
        return ApiResponse(
            code=201,
            message="模板上传成功，正在进行分析",
            data={
                "template_id": template.id,
                "name": template.name,
                "status": template.status,
                "task_id": task.id
            }
        )
    
    except Exception as e:
        # 发生异常时，将模板状态设为失败
        template.status = "failed"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"模板上传失败: {str(e)}"
        )

# 添加别名路由，支持/upload端点
@router.post("/upload", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def upload_template_alias(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    file: UploadFile = File(...),
    enable_tracking: bool = Form(False),
    db: Session = Depends(get_db)
):
    """上传模板的别名路由，保持与测试用例兼容"""
    return await upload_template(name, description, tags, file, enable_tracking, db)

@router.get("/", response_model=ApiResponse)
async def list_templates(
    skip: int = 0, 
    limit: int = 100,
    status_filter: Optional[str] = Query("ready", description="模板状态过滤，多个状态用逗号分隔，例如'ready,analyzing'，传入all表示不过滤"),
    db: Session = Depends(get_db)
):
    """获取模板列表
    
    Args:
        skip: 分页起始位置
        limit: 分页大小
        status_filter: 模板状态过滤，多个状态用逗号分隔，例如'ready,analyzing'，传入all表示不过滤
        db: 数据库会话
        
    Returns:
        模板列表
    """
    try:
        # 解析状态过滤参数
        filter_statuses = None
        if status_filter and status_filter.lower() != "all":
            filter_statuses = [s.strip() for s in status_filter.split(",")]
        
        # 尝试从缓存获取（只有在请求ready状态模板且使用默认分页时）
        if filter_statuses == ["ready"] and skip == 0 and limit == 100:
            cached_templates = redis_service.get_cached_template_list(status_filter="ready")
            if cached_templates:
                logger.info("从缓存中获取模板列表")
                return ApiResponse(
                    code=200,
                    message="获取成功",
                    data={
                        "total": len(cached_templates),
                        "page": 1,
                        "limit": limit,
                        "templates": cached_templates
                    }
                )
        
        # 构建查询
        query = db.query(Template)
        
        # 应用状态过滤
        if filter_statuses:
            query = query.filter(Template.status.in_(filter_statuses))
        
        # 获取总数
        total = query.count()
        
        # 执行查询
        templates = query.offset(skip).limit(limit).all()
        
        # 序列化模板对象
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
                        logger.warning(f"解析模板标签失败，使用空列表: template_id={template.id}, tags={template.tags}")
                
                template_dict = {
                    "id": template.id,
                    "name": template.name,
                    "description": template.description,
                    "file_url": template.file_path,
                    "preview_url": template.preview_path,
                    "status": template.status,
                    "tags": tags,
                    "upload_time": template.upload_time.isoformat() if template.upload_time else None,
                }
                serializable_templates.append(template_dict)
            except Exception as e:
                logger.error(f"序列化模板对象失败: template_id={template.id}, error={str(e)}")
                # 继续处理下一个模板，不中断整个列表的获取
        
        # 如果是请求ready状态的模板且使用默认分页，缓存结果
        if filter_statuses == ["ready"] and skip == 0 and limit == 100:
            redis_service.cache_template_list(templates, status_filter="ready")
        
        return ApiResponse(
            code=200,
            message="获取成功",
            data={
                "total": total,
                "page": skip // limit + 1 if limit > 0 else 1,
                "limit": limit,
                "templates": serializable_templates
            }
        )
    except Exception as e:
        # 记录详细错误信息
        logger.error(f"获取模板列表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取模板列表失败: {str(e)}"
        )

@router.get("/{template_id}", response_model=ApiResponse)
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
    try:
        template = db.query(Template).filter(Template.id == template_id).first()
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"模板不存在: id={template_id}"
            )
        
        # 构造响应数据，确保模板对象能够正确序列化
        tags = []
        if template.tags:
            try:
                if template.tags.strip():
                    tags = json.loads(template.tags)
            except json.JSONDecodeError:
                # 如果JSON解析失败，使用空列表
                logger.warning(f"解析模板标签失败，使用空列表: template_id={template.id}, tags={template.tags}")
                
        template_data = {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "file_url": template.file_path,
            "preview_url": template.preview_path,
            "status": template.status,
            "tags": tags,
            "upload_time": template.upload_time.isoformat() if template.upload_time else None,
        }
        
        return ApiResponse(
            code=200,
            message="获取成功",
            data={
                "template": template_data
            }
        )
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        # 记录详细错误信息
        logger.error(f"获取模板详情失败: template_id={template_id}, 错误: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取模板详情失败: {str(e)}"
        )

@router.delete("/{template_id}", response_model=ApiResponse)
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
    
    return ApiResponse(
        code=200,
        message="模板删除成功",
        data={}
    )

@router.get("/{template_id}/analysis", response_model=ApiResponse)
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
        
        return ApiResponse(
            code=200,
            message="获取成功",
            data={
                "analysis": analysis_data
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"读取分析结果失败: {str(e)}"
        )

@router.post("/{template_id}/analyze", response_model=ApiResponse)
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
    
    return ApiResponse(
        code=200,
        message="模板分析任务已提交",
        data={
            "task_id": task.id,
            "template_id": template_id,
            "status": "analyzing"
        }
    )

@router.get("/{template_id}/status", response_model=ApiResponse)
async def get_template_status(
    template_id: int,
    db: Session = Depends(get_db)
):
    """获取模板分析状态
    
    Args:
        template_id: 模板ID
        db: 数据库会话
        
    Returns:
        模板分析状态
    """
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"模板不存在: id={template_id}"
        )
    
    # 获取分析任务状态
    task_status = None
    if template.status == "analyzing":
        # 查找最近的分析任务
        task_id = redis_service.get_template_analysis_task_id(template_id)
        if task_id:
            task_status = redis_service.get_task_status(task_id)
    
    return ApiResponse(
        code=200,
        message="获取成功",
        data={
            "template_id": template_id,
            "status": template.status,
            "progress": task_status.get("progress", 0) if task_status else 100,
            "message": task_status.get("message", "") if task_status else "模板分析完成" if template.status == "ready" else ""
        }
    )

@router.put("/{template_id}", response_model=ApiResponse)
async def update_template(
    template_id: int,
    template_data: TemplateBase,
    db: Session = Depends(get_db)
):
    """更新模板信息
    
    Args:
        template_id: 模板ID
        template_data: 要更新的模板数据
        db: 数据库会话
        
    Returns:
        更新后的模板信息
    """
    try:
        # 查询模板
        template = db.query(Template).filter(Template.id == template_id).first()
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"模板不存在: id={template_id}"
            )
        
        # 更新模板信息
        if template_data.name is not None:
            template.name = template_data.name
        if template_data.description is not None:
            template.description = template_data.description
        if template_data.tags is not None:
            template.tags = template_data.tags
        
        # 保存更新
        db.commit()
        db.refresh(template)
        
        # 清除缓存
        redis_service.invalidate_template_cache()
        
        # 构造响应数据
        template_data = {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "file_path": template.file_path,
            "preview_path": template.preview_path,
            "analysis_path": template.analysis_path,
            "status": template.status,
            "tags": template.tags,
            "upload_time": template.upload_time.isoformat() if template.upload_time else None,
            "analysis_time": template.analysis_time.isoformat() if template.analysis_time else None,
        }
        
        return ApiResponse(
            code=200,
            message="模板信息更新成功",
            data={
                "template": template_data
            }
        )
    except Exception as e:
        # 记录详细错误信息
        logger.error(f"更新模板信息失败: template_id={template_id}, 错误: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"更新模板信息失败: {str(e)}"
        ) 