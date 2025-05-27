from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from apps.api.config import settings

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
    Base.metadata.create_all(bind=engine)

# 数据库会话依赖
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 