from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from apps.api.config import settings
from apps.api.models.database import Base, User, Template, GenerationTask
import logging

logger = logging.getLogger(__name__)

# 创建SQLAlchemy引擎
engine = create_engine(
    settings.DATABASE_URL, connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)

# 创建SessionLocal类
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 导入模型以便使用Base.metadata.create_all()
from apps.api.models.database import Base, User, Template, GenerationTask

# 创建数据库表
def init_db():
    """初始化数据库表结构和默认数据"""
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    # 初始化默认用户
    db = SessionLocal()
    try:
        # 检查是否存在ID为1的用户
        admin_user = db.query(User).filter(User.id == 1).first()
        if not admin_user:
            # 创建默认管理员用户
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            
            admin_user = User(
                id=1,
                username="admin",
                password_hash=pwd_context.hash("admin123"),
                role="admin",
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            logger.info("创建默认管理员用户: admin")
    except Exception as e:
        logger.exception(f"初始化默认用户失败: {str(e)}")
        db.rollback()
    finally:
        db.close()

# 数据库会话依赖
def get_db():
    """依赖函数：获取数据库会话
    
    Returns:
        数据库会话对象
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 