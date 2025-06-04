from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ModelConfigBase(BaseModel):
    """大模型配置基础模型"""
    name: str = Field(..., description="配置名称")
    model_type: str = Field(..., description="模型类型", pattern="^(llm|vision|deepthink)$")
    api_key: str = Field(..., description="API密钥")
    api_base: str = Field(..., description="API基础URL")
    model_name: str = Field(..., description="模型名称")
    max_tokens: int = Field(default=128000, description="最大token数")
    temperature: float = Field(default=0.7, description="温度参数", ge=0.0, le=2.0)

class ModelConfigCreate(ModelConfigBase):
    """创建大模型配置"""
    pass

class ModelConfigUpdate(BaseModel):
    """更新大模型配置"""
    name: Optional[str] = None
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    model_name: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)

class ModelConfigResponse(ModelConfigBase):
    """大模型配置响应"""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None
    
    class Config:
        from_attributes = True

class ModelConfigListResponse(BaseModel):
    """大模型配置列表响应"""
    total: int
    configs: List[ModelConfigResponse]

class ActiveModelConfigResponse(BaseModel):
    """当前激活的模型配置"""
    llm: Optional[ModelConfigResponse] = None
    vision: Optional[ModelConfigResponse] = None
    deepthink: Optional[ModelConfigResponse] = None

class SetActiveModelRequest(BaseModel):
    """设置激活模型请求"""
    model_type: str = Field(..., pattern="^(llm|vision|deepthink)$")
    config_id: int = Field(..., description="配置ID") 