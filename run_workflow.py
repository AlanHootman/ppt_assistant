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

from core.engine.workflowEngine import WorkflowEngine

# 设置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    """主函数 - 处理命令行参数并执行工作流"""
    parser = argparse.ArgumentParser(description='运行PPT生成工作流')
    parser.add_argument('--md_file', type=str, required=True, help='输入的Markdown文件路径')
    parser.add_argument('--ppt_template', type=str, required=True, help='PPT模板文件路径')
    parser.add_argument('--output_dir', type=str, default='workspace/output', help='输出目录')
    
    args = parser.parse_args()
    
    # 检查输入文件
    if not os.path.exists(args.md_file):
        logger.error(f"找不到Markdown文件: {args.md_file}")
        return 1
        
    if not os.path.exists(args.ppt_template):
        logger.error(f"找不到PPT模板文件: {args.ppt_template}")
        return 1
        
    # 确保输出目录存在
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 读取Markdown文件内容
    with open(args.md_file, 'r', encoding='utf-8') as file:
        md_content = file.read()
    
    try:
        # 初始化工作流引擎 - 使用默认的工作流名称"ppt_generation"
        engine = WorkflowEngine()
        
        # 执行工作流
        result = await engine.run_async(
            raw_md=md_content,
            ppt_template_path=args.ppt_template,
            output_dir=args.output_dir
        )
        
        # 输出结果
        output_path = result.get('output_ppt_path', '')
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