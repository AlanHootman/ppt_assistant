FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 1. 前置操作及环境准备
# 1.1 配置 Debian 华为云镜像源
RUN echo "deb https://mirrors.huaweicloud.com/debian/ bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list \
 && echo "deb https://mirrors.huaweicloud.com/debian/ bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list \
 && echo "deb https://mirrors.huaweicloud.com/debian-security bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list

# 1.2 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    cmake \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# 1.3 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Shanghai
ENV PYTHONPATH=/app
ENV WORKING_DIR=/app/workspace

# 2. 复制项目文件
# 2.1 复制requirements文件
COPY requirements.txt .

# 2.2 复制项目核心文件
COPY apps/api /app/apps/api
COPY core /app/core
COPY config /app/config
COPY apps/__init__.py /app/apps/__init__.py

# 3. 安装依赖
# 3.1 升级pip并安装项目依赖
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 4. 创建必要的目录
RUN mkdir -p /app/workspace/templates \
    /app/workspace/output \
    /app/workspace/logs \
    /app/workspace/mlflow \
    /app/workspace/redis

# 5. 设置权限
RUN chmod -R 755 /app/workspace

# 6. 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 7. 暴露端口
EXPOSE 8000

# 8. 启动命令
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"] 