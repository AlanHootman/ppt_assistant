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

# 设置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="运行PPT自动生成工作流")
    parser.add_argument("--markdown", "-m", type=str, help="Markdown文件路径", 
                        default="tests/testfiles/MCP介绍.md")
    parser.add_argument("--template", "-t", type=str, help="PPT模板文件路径", 
                        default="tests/testfiles/Iphone16Pro.pptx")
    parser.add_argument("--session", "-s", type=str, help="会话ID（可选）")
    args = parser.parse_args()
    
    # 验证文件路径
    md_path = Path(args.markdown)
    ppt_path = Path(args.template)
    
    if not md_path.exists():
        logger.error(f"Markdown文件不存在: {md_path}")
        return 1
    
    if not ppt_path.exists():
        logger.error(f"PPT模板文件不存在: {ppt_path}")
        return 1
    
    # 读取Markdown内容
    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()
    
    logger.info(f"加载Markdown文件: {md_path}")
    logger.info(f"加载PPT模板: {ppt_path}")
    
    # 导入工作流引擎
    from core.engine.workflowEngine import WorkflowEngine
    
    # 初始化引擎
    engine = WorkflowEngine()
    logger.info("工作流引擎初始化完成")
    
    # 准备输入数据
    input_data = {
        "raw_md": md_content,
        "ppt_template_path": str(ppt_path.resolve())
    }
    
    # 运行工作流
    logger.info("开始执行工作流...")
    result = await engine.run(session_id=args.session, input_data=input_data)
    
    # 输出结果
    logger.info("-" * 50)
    logger.info(f"工作流执行完成！")
    logger.info(f"会话ID: {result.session_id}")
    logger.info(f"执行的节点: {len(result.checkpoints)}")
    
    if result.ppt_file_path:
        logger.info(f"生成的PPT文件: {result.ppt_file_path}")
    
    if result.failures:
        logger.error(f"执行过程中发生的错误: {result.failures}")
    
    return 0

if __name__ == "__main__":
    # 添加项目根目录到Python路径
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_root)
    
    # 运行异步主函数
    result = asyncio.run(main())
    
    # 返回结果
    sys.exit(result) 