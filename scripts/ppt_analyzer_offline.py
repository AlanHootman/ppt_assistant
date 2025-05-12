#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PPT离线解析工具

用于预先解析PPT模板，将解析结果保存为JSON文件，以便后续使用
支持单文件分析和批量分析
"""

import os
import sys
import json
import argparse
import asyncio
import logging
import glob
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import List

# 添加项目根目录到系统路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ppt_analyzer_offline")

# 导入所需模块
from core.agents.ppt_analysis_agent import PPTAnalysisAgent
from core.engine.state import AgentState
from config.settings import settings

async def analyze_template(template_path: str, output_dir: str = None, force: bool = False) -> str:
    """
    分析PPT模板并保存结果
    
    Args:
        template_path: PPT模板路径
        output_dir: 输出目录，默认为workspace/ppt_cache
        force: 是否强制重新分析
        
    Returns:
        输出文件路径，失败返回None
    """
    # 验证模板文件是否存在
    if not os.path.exists(template_path):
        logger.error(f"模板文件不存在: {template_path}")
        return None
    
    # 确定输出目录
    if not output_dir:
        output_dir = str(settings.PPT_CACHE_DIR)
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成输出文件路径 - 使用模板文件名作为基础
    template_name = Path(template_path).stem
    output_path = os.path.join(output_dir, f"{template_name}_layout_features.json")
    
    # 检查是否已存在且不强制更新
    if os.path.exists(output_path) and not force:
        logger.info(f"分析结果已存在: {output_path}，跳过分析 (使用--force强制重新分析)")
        return output_path
    
    logger.info(f"开始分析PPT模板: {template_path}")
    
    try:
        # 创建临时状态对象
        session_id = f"offline_analysis_{template_name}"
        state = AgentState(
            session_id=session_id,
            ppt_template_path=template_path
        )
        
        # 创建PPT分析代理
        agent_config = {"model_type": "vision"}
        ppt_analyzer = PPTAnalysisAgent(agent_config)
        
        # 分析PPT模板
        await ppt_analyzer.run(state)
        
        # 检查是否成功分析
        if state.layout_features:
            # 保存分析结果
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(state.layout_features, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功保存分析结果到: {output_path}")
            
            # 打印布局摘要
            slides_count = len(state.layout_features.get("slideLayouts", []))
            logger.info(f"模板名称: {state.layout_features.get('templateName')}")
            logger.info(f"幻灯片数量: {state.layout_features.get('slideCount')}")
            logger.info(f"分析的布局数量: {slides_count}")
            
            return output_path
        else:
            logger.error("PPT模板分析失败，没有获取到布局特征")
            return None
    
    except Exception as e:
        logger.error(f"分析过程出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

async def batch_analyze(template_dir: str, pattern: str = "*.pptx", output_dir: str = None, force: bool = False) -> List[str]:
    """
    批量分析目录中的PPT模板
    
    Args:
        template_dir: 包含PPT模板的目录
        pattern: 文件匹配模式，默认为*.pptx
        output_dir: 输出目录，默认为workspace/ppt_cache
        force: 是否强制重新分析
        
    Returns:
        成功分析的文件路径列表
    """
    if not os.path.isdir(template_dir):
        logger.error(f"模板目录不存在: {template_dir}")
        return []
    
    # 查找所有匹配的PPT文件
    search_pattern = os.path.join(template_dir, pattern)
    template_files = glob.glob(search_pattern)
    
    if not template_files:
        logger.warning(f"在目录 {template_dir} 中没有找到匹配 {pattern} 的文件")
        return []
    
    logger.info(f"找到 {len(template_files)} 个PPT模板文件，开始批量分析")
    
    # 分析结果列表
    results = []
    
    # 逐个分析文件
    for template_path in template_files:
        result = await analyze_template(template_path, output_dir, force)
        if result:
            results.append(result)
    
    logger.info(f"批量分析完成，成功: {len(results)}/{len(template_files)}")
    
    return results

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='PPT模板离线分析工具')
    
    # 子命令解析器
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # 单文件分析命令
    analyze_parser = subparsers.add_parser('analyze', help='分析单个PPT模板')
    analyze_parser.add_argument('template_path', help='PPT模板文件路径')
    analyze_parser.add_argument('-o', '--output_dir', help='输出目录路径')
    analyze_parser.add_argument('-f', '--force', action='store_true', help='强制重新分析，即使缓存已存在')
    
    # 批量分析命令
    batch_parser = subparsers.add_parser('batch', help='批量分析PPT模板')
    batch_parser.add_argument('template_dir', help='包含PPT模板的目录')
    batch_parser.add_argument('-p', '--pattern', default='*.pptx', help='文件匹配模式，默认为*.pptx')
    batch_parser.add_argument('-o', '--output_dir', help='输出目录路径')
    batch_parser.add_argument('-f', '--force', action='store_true', help='强制重新分析，即使缓存已存在')
    
    # 列出缓存命令
    list_parser = subparsers.add_parser('list', help='列出已缓存的PPT模板分析结果')
    
    args = parser.parse_args()
    
    # 如果没有提供命令，显示帮助
    if not args.command:
        parser.print_help()
        return
    
    # 执行相应命令
    if args.command == 'analyze':
        # 分析单个PPT模板
        asyncio.run(analyze_template(args.template_path, args.output_dir, args.force))
    
    elif args.command == 'batch':
        # 批量分析PPT模板
        asyncio.run(batch_analyze(args.template_dir, args.pattern, args.output_dir, args.force))
    
    elif args.command == 'list':
        # 列出已缓存的PPT模板分析结果
        cache_dir = settings.PPT_CACHE_DIR
        json_files = glob.glob(os.path.join(cache_dir, "*_layout_features.json"))
        
        if not json_files:
            print("缓存目录中没有找到PPT模板分析结果")
            return
        
        print(f"找到 {len(json_files)} 个缓存的PPT模板分析结果:")
        for json_file in sorted(json_files):
            file_name = os.path.basename(json_file)
            template_name = file_name.replace("_layout_features.json", "")
            print(f" - {template_name}")

if __name__ == "__main__":
    main() 