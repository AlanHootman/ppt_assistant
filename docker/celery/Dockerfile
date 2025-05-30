FROM python:3.10-slim

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
    libreoffice \
    libreoffice-writer \
    libreoffice-impress \
    libreoffice-calc \
    fonts-dejavu \
    fonts-liberation \
    fonts-noto-cjk \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# 1.3 创建专用用户
RUN adduser --disabled-password --gecos "" appuser

# 1.4 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Shanghai
ENV PYTHONPATH=/app
ENV WORKING_DIR=/app/workspace

# 1.5 LibreOffice 环境配置
ENV DISPLAY=:99
ENV LIBREOFFICE_HEADLESS=1

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

# 4. 创建目录并设置权限
RUN mkdir -p /app/workspace/templates \
    /app/workspace/output \
    /app/workspace/logs \
    /app/workspace/mlflow \
    /app/workspace/redis \
    && chown -R appuser:appuser /app/workspace \
    && chown -R appuser:appuser /app

# 4.1 配置LibreOffice
RUN mkdir -p /home/appuser/.config/libreoffice/4/user \
    && chown -R appuser:appuser /home/appuser/.config \
    && echo '#!/bin/bash\nsoffice --headless --nologo --nofirststartwizard --accept="socket,host=127.0.0.1,port=2002;urp;" --norestore "$@"' > /usr/local/bin/soffice-headless \
    && chmod +x /usr/local/bin/soffice-headless

# 4.2 验证LibreOffice安装
RUN soffice --version || (echo "LibreOffice installation failed" && exit 1)

# 5. 切换到应用用户
USER appuser

# 6. 健康检查 (检查Celery进程和LibreOffice)
HEALTHCHECK --interval=60s --timeout=30s --start-period=30s --retries=3 \
    CMD celery -A apps.api.celery_app inspect ping && soffice --version > /dev/null || exit 1

# 7. 默认启动命令
CMD ["celery", "-A", "apps.api.celery_app", "worker", "--loglevel=INFO", "--concurrency=2", "-Q", "ppt_generation,template_analysis"] 