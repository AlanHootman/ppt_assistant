from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from config.settings import settings

# 构建数据库URL
db_path = settings.DB_DIR / "app.db"
DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Session:
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 