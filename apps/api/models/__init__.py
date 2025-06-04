from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from apps.api.config import settings
from apps.api.models.database import Base, User, Template, GenerationTask, ModelConfig
import logging

logger = logging.getLogger(__name__)

# 创建SQLAlchemy引擎
engine = create_engine(
    settings.DATABASE_URL, connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)

# 创建SessionLocal类
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 导入模型以便使用Base.metadata.create_all()
from apps.api.models.database import Base, User, Template, GenerationTask, ModelConfig

# 创建数据库表
def init_db():
    """初始化数据库表结构和默认数据"""
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    # 初始化默认数据
    db = SessionLocal()
    try:
        # 1. 初始化默认管理员用户
        admin_user = db.query(User).filter(User.id == 1).first()
        if not admin_user:
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
            logger.info("创建默认管理员用户: admin/admin123")
        
        # 2. 初始化默认模型配置
        existing_configs = db.query(ModelConfig).count()
        if existing_configs == 0:
            # 创建示例LLM配置
            llm_config = ModelConfig(
                name="GPT-4 默认配置",
                model_type="llm",
                api_key="your-openai-api-key-here",
                api_base="https://api.openai.com/v1",
                model_name="gpt-4",
                max_tokens=8192,
                temperature=0.2,
                is_active=True,
                created_by=admin_user.id
            )
            db.add(llm_config)
            
            # 创建示例Vision配置
            vision_config = ModelConfig(
                name="GPT-4V 默认配置",
                model_type="vision",
                api_key="your-openai-api-key-here",
                api_base="https://api.openai.com/v1",
                model_name="gpt-4-vision-preview",
                max_tokens=8192,
                temperature=0.2,
                is_active=True,
                created_by=admin_user.id
            )
            db.add(vision_config)
            
            # 创建示例DeepThink配置
            deepthink_config = ModelConfig(
                name="DeepSeek 默认配置",
                model_type="deepthink",
                api_key="your-deepseek-api-key-here",
                api_base="https://api.deepseek.com/v1",
                model_name="deepseek-chat",
                max_tokens=65536,
                temperature=1.0,
                is_active=True,
                created_by=admin_user.id
            )
            db.add(deepthink_config)
            
            db.commit()
            logger.info("创建默认模型配置")
            
    except Exception as e:
        logger.exception(f"初始化默认数据失败: {str(e)}")
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