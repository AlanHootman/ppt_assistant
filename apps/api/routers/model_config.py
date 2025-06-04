from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from ..dependencies.auth import get_current_user
from ..dependencies.database import get_db
from ..models.database import User
from ..models.model_config import (
    ModelConfigCreate, 
    ModelConfigUpdate, 
    ModelConfigResponse, 
    ModelConfigListResponse,
    ActiveModelConfigResponse,
    SetActiveModelRequest
)
from ..services.model_config_service import ModelConfigService

router = APIRouter(prefix="/model-configs", tags=["model-configs"])


@router.post("/", response_model=ModelConfigResponse)
async def create_model_config(
    config_data: ModelConfigCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建大模型配置"""
    service = ModelConfigService(db)
    
    try:
        config = service.create_config(config_data, current_user.id)
        return config
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"创建配置失败: {str(e)}"
        )


@router.get("/", response_model=ModelConfigListResponse)
async def get_model_configs(
    model_type: Optional[str] = None,
    page: int = 1,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取大模型配置列表"""
    service = ModelConfigService(db)
    
    # 验证model_type参数
    if model_type and model_type not in ["llm", "vision", "deepthink"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="model_type必须是llm、vision或deepthink之一"
        )
    
    configs, total = service.get_configs(model_type, page, limit)
    
    return ModelConfigListResponse(
        total=total,
        configs=configs
    )


@router.get("/active", response_model=ActiveModelConfigResponse)
async def get_active_configs(
    db: Session = Depends(get_db)
):
    """获取当前激活的大模型配置（无需认证，供前端使用）"""
    service = ModelConfigService(db)
    active_configs = service.get_active_configs()
    
    return ActiveModelConfigResponse(
        llm=active_configs["llm"],
        vision=active_configs["vision"],
        deepthink=active_configs["deepthink"]
    )


@router.get("/{config_id}", response_model=ModelConfigResponse)
async def get_model_config(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取指定ID的大模型配置"""
    service = ModelConfigService(db)
    config = service.get_config_by_id(config_id)
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配置不存在"
        )
    
    return config


@router.put("/{config_id}", response_model=ModelConfigResponse)
async def update_model_config(
    config_id: int,
    config_data: ModelConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新大模型配置"""
    service = ModelConfigService(db)
    
    config = service.update_config(config_id, config_data)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配置不存在"
        )
    
    return config


@router.delete("/{config_id}")
async def delete_model_config(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除大模型配置"""
    service = ModelConfigService(db)
    
    try:
        success = service.delete_config(config_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="配置不存在"
            )
        
        return {"message": "配置删除成功"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/set-active")
async def set_active_model(
    request: SetActiveModelRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """设置激活的大模型配置"""
    service = ModelConfigService(db)
    
    success = service.set_active_config(request.model_type, request.config_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="设置激活配置失败，请检查配置ID和模型类型是否匹配"
        )
    
    return {"message": f"{request.model_type}模型配置已切换成功"} 