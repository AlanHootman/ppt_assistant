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
import signal
import psutil
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

def find_process_by_port(port):
    """
    根据端口号查找进程
    
    Args:
        port: 端口号
        
    Returns:
        list: 使用该端口的进程列表
    """
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            for conn in proc.connections():
                if conn.laddr.port == port:
                    processes.append(proc)
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return processes

def find_mlflow_processes():
    """
    查找所有MLflow相关进程
    
    Returns:
        list: MLflow进程列表
    """
    mlflow_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and any('mlflow' in cmd for cmd in cmdline):
                # 检查是否是MLflow server进程
                if 'server' in cmdline:
                    mlflow_processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return mlflow_processes

def stop_mlflow_server(port=5000, force=False):
    """
    停止MLflow服务器
    
    Args:
        port: 要停止的服务端口号
        force: 是否强制终止进程
        
    Returns:
        bool: 是否成功停止服务
    """
    logger.info(f"正在查找端口 {port} 上的MLflow服务...")
    
    # 先查找特定端口上的进程
    port_processes = find_process_by_port(port)
    
    # 再查找所有MLflow进程
    mlflow_processes = find_mlflow_processes()
    
    # 合并进程列表，去重
    all_processes = []
    process_pids = set()
    
    for proc in port_processes + mlflow_processes:
        if proc.pid not in process_pids:
            all_processes.append(proc)
            process_pids.add(proc.pid)
    
    if not all_processes:
        logger.info("没有找到运行中的MLflow服务")
        return True
    
    # 显示找到的进程
    logger.info(f"找到 {len(all_processes)} 个MLflow相关进程:")
    for proc in all_processes:
        try:
            cmdline = ' '.join(proc.cmdline())
            logger.info(f"  PID: {proc.pid}, 命令: {cmdline[:100]}...")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            logger.info(f"  PID: {proc.pid}, 命令: <无法获取>")
    
    # 停止进程
    stopped_count = 0
    for proc in all_processes:
        try:
            logger.info(f"正在停止进程 {proc.pid}...")
            
            if force:
                # 强制终止
                proc.kill()
                logger.info(f"已强制终止进程 {proc.pid}")
            else:
                # 优雅停止
                proc.terminate()
                
                # 等待进程结束
                try:
                    proc.wait(timeout=10)
                    logger.info(f"进程 {proc.pid} 已优雅停止")
                except psutil.TimeoutExpired:
                    logger.warning(f"进程 {proc.pid} 未在10秒内响应，强制终止...")
                    proc.kill()
                    logger.info(f"已强制终止进程 {proc.pid}")
            
            stopped_count += 1
            
        except psutil.NoSuchProcess:
            logger.info(f"进程 {proc.pid} 已经不存在")
            stopped_count += 1
        except psutil.AccessDenied:
            logger.error(f"没有权限终止进程 {proc.pid}")
        except Exception as e:
            logger.error(f"停止进程 {proc.pid} 时出错: {str(e)}")
    
    if stopped_count > 0:
        logger.info(f"成功停止了 {stopped_count} 个进程")
        
        # 再次检查端口是否已释放
        time.sleep(2)
        remaining_processes = find_process_by_port(port)
        if not remaining_processes:
            logger.info(f"端口 {port} 已释放")
            return True
        else:
            logger.warning(f"端口 {port} 上仍有进程运行")
            return False
    else:
        logger.error("没有成功停止任何进程")
        return False

def check_port_available(port):
    """
    检查端口是否可用
    
    Args:
        port: 端口号
        
    Returns:
        bool: 端口是否可用
    """
    processes = find_process_by_port(port)
    return len(processes) == 0

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
    
    # 检查端口是否已被占用
    if not check_port_available(port):
        logger.error(f"端口 {port} 已被占用！")
        logger.info(f"您可以运行以下命令停止现有服务:")
        logger.info(f"  python {__file__} --stop --port {port}")
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

def list_mlflow_services():
    """列出所有运行中的MLflow服务"""
    logger.info("正在查找运行中的MLflow服务...")
    
    mlflow_processes = find_mlflow_processes()
    
    if not mlflow_processes:
        logger.info("没有找到运行中的MLflow服务")
        return
    
    logger.info(f"找到 {len(mlflow_processes)} 个运行中的MLflow服务:")
    for proc in mlflow_processes:
        try:
            cmdline = ' '.join(proc.cmdline())
            # 尝试从命令行中提取端口信息
            port_info = ""
            if "--port" in cmdline:
                parts = cmdline.split("--port")
                if len(parts) > 1:
                    port_part = parts[1].split()[0]
                    port_info = f", 端口: {port_part}"
            
            logger.info(f"  PID: {proc.pid}{port_info}")
            logger.info(f"    命令: {cmdline}")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            logger.info(f"  PID: {proc.pid}, 命令: <无法获取>")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='MLflow服务器管理工具')
    parser.add_argument('--host', type=str, default="127.0.0.1", help='MLflow服务器主机地址')
    parser.add_argument('--port', type=int, default=5001, help='MLflow服务器端口号')
    parser.add_argument('--no-browser', action='store_true', help='不自动打开浏览器')
    parser.add_argument('--stop', action='store_true', help='停止MLflow服务器')
    parser.add_argument('--force', action='store_true', help='强制停止进程（配合--stop使用）')
    parser.add_argument('--list', action='store_true', help='列出所有运行中的MLflow服务')
    
    args = parser.parse_args()
    
    if args.list:
        # 列出服务
        list_mlflow_services()
    elif args.stop:
        # 停止服务
        success = stop_mlflow_server(port=args.port, force=args.force)
        if not success:
            exit(1)
    else:
        # 启动服务
        success = start_mlflow_server(host=args.host, port=args.port, auto_open=not args.no_browser)
        if not success:
            exit(1)

if __name__ == "__main__":
    main()