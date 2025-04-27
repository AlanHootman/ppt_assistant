#!/usr/bin/env python
"""
启动MLflow服务器的辅助脚本
"""
import os
import subprocess
import argparse
import logging
import webbrowser
import time
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_mlflow_installed():
    """检查是否安装了MLflow"""
    try:
        import mlflow
        return True
    except ImportError:
        return False

def start_mlflow_server(host="127.0.0.1", port=5000, auto_open=True):
    """
    启动MLflow服务器
    
    Args:
        host: 服务器主机地址
        port: 服务器端口号
        auto_open: 是否自动打开浏览器
    """
    # 检查MLflow是否已安装
    if not check_mlflow_installed():
        logger.error("未安装MLflow，请运行: pip install mlflow")
        return False
        
    # 检查mlruns目录是否存在
    mlruns_dir = Path("./mlruns")
    if not mlruns_dir.exists():
        logger.warning("没有找到MLflow跟踪数据目录，将创建新目录")
        mlruns_dir.mkdir(exist_ok=True)
    
    # 启动MLflow服务器
    logger.info(f"正在启动MLflow服务器，地址 {host}:{port}...")
    try:
        process = subprocess.Popen(
            ["mlflow", "server", "--host", host, "--port", str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # 等待服务器启动
        time.sleep(2)
        
        # 检查进程是否仍在运行
        if process.poll() is not None:
            logger.error("MLflow服务器启动失败！")
            return False
        
        ui_url = f"http://{host}:{port}"
        logger.info(f"MLflow服务器已启动，请访问: {ui_url}")
        
        # 自动打开浏览器
        if auto_open:
            webbrowser.open(ui_url)
            logger.info("已自动打开浏览器")
        
        # 等待用户中断
        print("\n按Ctrl+C停止MLflow服务器...")
        try:
            process.wait()
        except KeyboardInterrupt:
            logger.info("正在停止MLflow服务器...")
            process.terminate()
            process.wait()
            logger.info("MLflow服务器已停止")
            
        return True
    except Exception as e:
        logger.error(f"启动MLflow服务器失败: {str(e)}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='启动MLflow服务器')
    parser.add_argument('--host', type=str, default="127.0.0.1", help='MLflow服务器主机地址')
    parser.add_argument('--port', type=int, default=5000, help='MLflow服务器端口号')
    parser.add_argument('--no-browser', action='store_true', help='不自动打开浏览器')
    
    args = parser.parse_args()
    
    # 启动MLflow服务器
    start_mlflow_server(host=args.host, port=args.port, auto_open=not args.no_browser)

if __name__ == "__main__":
    main() 