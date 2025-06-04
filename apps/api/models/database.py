from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="admin")
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class Template(Base):
    """PPT模板模型"""
    __tablename__ = "templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    file_path = Column(String(255), nullable=False)
    preview_path = Column(String(255))
    analysis_path = Column(String(255))
    status = Column(String(20), default="uploading")  # uploading, analyzing, ready, failed
    tags = Column(Text)  # JSON格式存储标签
    upload_time = Column(DateTime, default=datetime.utcnow)
    analysis_time = Column(DateTime)
    created_by = Column(Integer, ForeignKey("users.id"))
    
    creator = relationship("User", back_populates="templates")

class GenerationTask(Base):
    """PPT生成任务模型"""
    __tablename__ = "generation_tasks"
    
    id = Column(String(36), primary_key=True)  # UUID
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=False)
    markdown_content = Column(Text, nullable=False)
    status = Column(String(20), default="pending")  # pending, processing, completed, failed, cancelled
    progress = Column(Integer, default=0)
    current_step = Column(String(50))
    step_description = Column(String(255))
    output_path = Column(String(255))
    error_message = Column(Text)
    can_retry = Column(Boolean, default=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    template = relationship("Template")

class ModelConfig(Base):
    """大模型配置表"""
    __tablename__ = "model_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # 配置名称，如 "GPT-4"
    model_type = Column(String(20), nullable=False)  # 模型类型：llm, vision, deepthink
    api_key = Column(String(255), nullable=False)  # API密钥
    api_base = Column(String(255), nullable=False)  # API基础URL
    model_name = Column(String(100), nullable=False)  # 模型名称，如 "gpt-4"
    max_tokens = Column(Integer, default=128000)  # 最大token数
    temperature = Column(Float, default=0.7)  # 温度参数
    is_active = Column(Boolean, default=False)  # 是否为当前激活的配置
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"))
    
    creator = relationship("User")

# 添加关系
User.templates = relationship("Template", back_populates="creator") 