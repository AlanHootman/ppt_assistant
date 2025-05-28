from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from apps.api.models import get_db
from apps.api.models.database import User
from apps.api.dependencies.auth import create_access_token
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Dict, Any
from pydantic import BaseModel

router = APIRouter(prefix="/auth")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    created_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True

def verify_password(plain_password, hashed_password):
    """验证密码
    
    Args:
        plain_password: 明文密码
        hashed_password: 加密密码
        
    Returns:
        密码是否匹配
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """获取密码哈希
    
    Args:
        password: 明文密码
        
    Returns:
        加密后的密码
    """
    return pwd_context.hash(password)

def authenticate_user(db: Session, username: str, password: str):
    """验证用户
    
    Args:
        db: 数据库会话
        username: 用户名
        password: 密码
        
    Returns:
        认证成功的用户对象，认证失败则返回False
    """
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return False
    if not verify_password(password, user.password_hash):
        return False
    return user

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """获取访问令牌
    
    Args:
        form_data: 用户登录表单
        db: 数据库会话
        
    Returns:
        访问令牌
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码不正确",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """注册新用户
    
    Args:
        user_data: 用户注册数据
        db: 数据库会话
        
    Returns:
        创建的用户信息
    """
    # 检查用户名是否已存在
    db_user = db.query(User).filter(User.username == user_data.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    # 创建新用户
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        password_hash=hashed_password,
        role=user_data.role,
        created_at=datetime.utcnow(),
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user 