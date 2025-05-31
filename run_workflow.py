#!/usr/bin/env python
"""
工作流运行示例脚本
"""
import asyncio
import logging
import os
import sys
from pathlib import Path
import argparse
import traceback
import subprocess

from core.engine.workflowEngine import WorkflowEngine

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

def start_mlflow_server(port=5001, host="127.0.0.1"):
    """启动MLflow服务器"""
    try:
        # 检查mlruns目录是否存在
        if not os.path.exists("mlruns"):
            logger.warning("没有找到MLflow跟踪数据，将在生成新数据后再显示")
        
        # 启动MLflow服务器
        logger.info(f"正在启动MLflow服务器，地址 {host}:{port}...")
        subprocess.Popen(
            ["mlflow", "server", "--host", host, "--port", str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        logger.info(f"MLflow服务器已启动，请访问: http://{host}:{port}")
    except Exception as e:
        logger.error(f"启动MLflow服务器失败: {str(e)}")

async def main():
    """主函数 - 处理命令行参数并执行工作流"""
    parser = argparse.ArgumentParser(description='运行PPT生成工作流')
    parser.add_argument('--markdown', type=str, required=True, help='输入的Markdown文件路径')
    parser.add_argument('--template', type=str, required=True, help='PPT模板文件路径')
    parser.add_argument('--output_dir', type=str, default='workspace/output', help='输出目录')
    parser.add_argument('--trace', action='store_true', help='启用MLflow跟踪')
    
    args = parser.parse_args()
    
    # 检查MLflow
    has_mlflow = check_mlflow_installed()
    if args.trace and not has_mlflow:
        logger.warning("未安装MLflow，将无法使用工作流跟踪功能。请运行: pip install mlflow")
        args.trace = False
    
    # 检查输入文件
    if not os.path.exists(args.markdown):
        logger.error(f"找不到Markdown文件: {args.markdown}")
        return 1
        
    if not os.path.exists(args.template):
        logger.error(f"找不到PPT模板文件: {args.template}")
        return 1
        
    # 确保输出目录存在
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 读取Markdown文件内容
    with open(args.markdown, 'r', encoding='utf-8') as file:
        md_content = file.read()
    
    try:
        # 初始化工作流引擎 - 使用默认的工作流名称"ppt_generation"，并启用跟踪（如果请求）
        engine = WorkflowEngine(enable_tracking=args.trace)
        
        # 执行工作流
        result = await engine.run_async(
            raw_md=md_content,
            ppt_template_path=args.template,
            output_dir=args.output_dir
        )
        
        # 输出结果
        output_path = getattr(result, 'output_ppt_path', '')
        if output_path and os.path.exists(output_path):
            logger.info(f"PPT生成成功: {output_path}")
            print(f"\nPPT文件已生成: {output_path}")
            
        else:
            logger.error("PPT生成失败，未找到输出文件")
            return 1
            
        return 0
        
    except Exception as e:
        logger.error(f"工作流执行出错: {str(e)}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    # 执行异步主函数
    sys.exit(asyncio.run(main())) 