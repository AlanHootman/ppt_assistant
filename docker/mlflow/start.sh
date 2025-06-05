#!/bin/bash
set -e

# 安装必要的工具
apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# 创建必要的目录
mkdir -p /app/mlflow_data/mlruns /app/mlflow_data/mlartifacts
chmod -R 755 /app/mlflow_data

# 安装MLflow
pip install --no-cache-dir mlflow -i https://pypi.tuna.tsinghua.edu.cn/simple

# 启动MLflow服务器
exec mlflow server \
  --host 0.0.0.0 \
  --port 5001 \
  --backend-store-uri file:///app/mlflow_data/mlruns \
  --artifacts-destination file:///app/mlflow_data/mlartifacts \
  --serve-artifacts 