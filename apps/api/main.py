from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
from apps.api.config import settings
from apps.api.models import init_db
from apps.api.routers import auth, templates, generation, websocket
import os
import time

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(settings.LOG_DIR, "api.log"))
    ]
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="PPT Assistant API",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制允许的源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加请求处理时间中间件
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"全局异常: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "内部服务器错误", "message": str(exc)}
    )

# 挂载静态文件
app.mount("/static", StaticFiles(directory=str(settings.STATIC_DIR)), name="static")

# 路由前缀
api_prefix = "/api"

# 注册路由
app.include_router(auth.router, prefix=f"{api_prefix}/auth", tags=["认证"])
app.include_router(templates.router, prefix=f"{api_prefix}/templates", tags=["模板"])
app.include_router(generation.router, prefix=f"{api_prefix}/generation", tags=["生成"])
app.include_router(websocket.router, tags=["WebSocket"])

@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    logger.info("初始化数据库...")
    init_db()
    logger.info("应用启动完成")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    logger.info("应用关闭")

@app.get("/", tags=["根"])
async def root():
    """根路径"""
    return {"message": "PPT Assistant API", "docs": "/api/docs"}

@app.get(f"{api_prefix}/health", tags=["健康检查"])
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "version": settings.VERSION,
        "timestamp": time.time()
    } 