#!/bin/sh

# 等待上游服务启动的脚本

echo "等待上游服务启动..."

# 等待API服务
until nc -z ppt_api 8000; do
    echo "等待API服务 (ppt_api:8000)..."
    sleep 2
done
echo "API服务已启动"

# 等待Web服务
until nc -z ppt_web 5173; do
    echo "等待Web服务 (ppt_web:5173)..."
    sleep 2
done
echo "Web服务已启动"

# 等待MLflow服务
until nc -z ppt_mlflow 5000; do
    echo "等待MLflow服务 (ppt_mlflow:5000)..."
    sleep 2
done
echo "MLflow服务已启动"

echo "所有上游服务已启动，启动Nginx..."
exec nginx -g "daemon off;" 