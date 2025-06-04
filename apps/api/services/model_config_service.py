from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..models.database import ModelConfig
from ..models.model_config import ModelConfigCreate, ModelConfigUpdate


class ModelConfigService:
    """大模型配置服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_config(self, config_data: ModelConfigCreate, user_id: int) -> ModelConfig:
        """创建大模型配置"""
        db_config = ModelConfig(
            name=config_data.name,
            model_type=config_data.model_type,
            api_key=config_data.api_key,
            api_base=config_data.api_base,
            model_name=config_data.model_name,
            max_tokens=config_data.max_tokens,
            temperature=config_data.temperature,
            created_by=user_id
        )
        self.db.add(db_config)
        self.db.commit()
        self.db.refresh(db_config)
        return db_config
    
    def get_configs(self, model_type: Optional[str] = None, page: int = 1, limit: int = 100) -> tuple[List[ModelConfig], int]:
        """获取大模型配置列表"""
        query = self.db.query(ModelConfig)
        
        if model_type:
            query = query.filter(ModelConfig.model_type == model_type)
        
        total = query.count()
        
        configs = query.offset((page - 1) * limit).limit(limit).all()
        
        return configs, total
    
    def get_config_by_id(self, config_id: int) -> Optional[ModelConfig]:
        """根据ID获取配置"""
        return self.db.query(ModelConfig).filter(ModelConfig.id == config_id).first()
    
    def update_config(self, config_id: int, config_data: ModelConfigUpdate) -> Optional[ModelConfig]:
        """更新大模型配置"""
        db_config = self.get_config_by_id(config_id)
        if not db_config:
            return None
        
        update_data = config_data.dict(exclude_unset=True)
        if update_data:
            update_data['updated_at'] = datetime.utcnow()
            for field, value in update_data.items():
                setattr(db_config, field, value)
            
            self.db.commit()
            self.db.refresh(db_config)
        
        return db_config
    
    def delete_config(self, config_id: int) -> bool:
        """删除大模型配置"""
        db_config = self.get_config_by_id(config_id)
        if not db_config:
            return False
        
        # 如果是激活状态的配置，不允许删除
        if db_config.is_active:
            raise ValueError("无法删除激活状态的配置，请先切换到其他配置")
        
        self.db.delete(db_config)
        self.db.commit()
        return True
    
    def set_active_config(self, model_type: str, config_id: int) -> bool:
        """设置激活的配置"""
        # 先取消同类型的所有激活状态
        self.db.query(ModelConfig).filter(
            and_(
                ModelConfig.model_type == model_type,
                ModelConfig.is_active == True
            )
        ).update({"is_active": False, "updated_at": datetime.utcnow()})
        
        # 设置新的激活配置
        target_config = self.get_config_by_id(config_id)
        if not target_config or target_config.model_type != model_type:
            return False
        
        target_config.is_active = True
        target_config.updated_at = datetime.utcnow()
        
        self.db.commit()
        return True
    
    def get_active_configs(self) -> Dict[str, Optional[ModelConfig]]:
        """获取当前激活的配置"""
        active_configs = self.db.query(ModelConfig).filter(ModelConfig.is_active == True).all()
        
        result = {
            "llm": None,
            "vision": None,
            "deepthink": None
        }
        
        for config in active_configs:
            result[config.model_type] = config
        
        return result
    
    def get_active_config_by_type(self, model_type: str) -> Optional[ModelConfig]:
        """获取指定类型的激活配置"""
        return self.db.query(ModelConfig).filter(
            and_(
                ModelConfig.model_type == model_type,
                ModelConfig.is_active == True
            )
        ).first() 