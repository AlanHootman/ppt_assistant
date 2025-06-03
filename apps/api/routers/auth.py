from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from apps.api.models import get_db
from apps.api.models.database import User
from apps.api.dependencies.auth import create_access_token, get_current_user
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/auth")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

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

class LoginRequest(BaseModel):
    username: str
    password: str

class UserInfo(BaseModel):
    id: int
    username: str
    role: str

class LoginResponse(BaseModel):
    token: str
    expires_in: int
    user: UserInfo

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

@router.post("/login", response_model=dict)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """用户登录
    
    Args:
        request: 登录请求数据
        db: 数据库会话
        
    Returns:
        访问令牌和用户信息
    """
    user = authenticate_user(db, request.username, request.password)
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
    
    return {
        "code": 200,
        "message": "登录成功",
        "data": {
            "token": access_token,
            "expires_in": 1800,  # 30分钟 = 1800秒
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role
            }
        }
    }

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

@router.get("/verify", response_model=dict)
async def verify_token(current_user: User = Depends(get_current_user)):
    """验证令牌有效性
    
    Args:
        current_user: 当前用户(通过依赖注入)
        
    Returns:
        用户信息
    """
    return {
        "code": 200,
        "message": "令牌有效",
        "data": {
            "user": {
                "id": current_user.id,
                "username": current_user.username,
                "role": current_user.role
            }
        }
    }

@router.post("/logout", response_model=dict)
async def logout(current_user: User = Depends(get_current_user)):
    """退出登录
    
    Args:
        current_user: 当前用户(通过依赖注入)
        
    Returns:
        成功退出消息
    """
    # 这里可以添加令牌黑名单等逻辑，本示例简单返回成功
    return {
        "code": 200,
        "message": "已成功退出登录",
        "data": {}
    } 