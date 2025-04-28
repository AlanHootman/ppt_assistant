#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
核心Agent测试脚本

测试开发的四个核心Agent功能。
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from core.engine.state import AgentState
from core.agents.markdown_agent import MarkdownAgent
from core.agents.ppt_analysis_agent import PPTAnalysisAgent
from core.agents.layout_decision_agent import LayoutDecisionAgent
from core.agents.ppt_generator_agent import PPTGeneratorAgent
from core.agents.validator_agent import ValidatorAgent

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_markdown_agent():
    """测试Markdown解析Agent"""
    logger.info("===== 测试Markdown解析Agent =====")
    
    # 创建测试状态
    state = AgentState()
    
    # 设置测试Markdown内容
    state.raw_md = """# 示例PPT标题
    
## 第一章节
- 这是第一章的第一点
- 这是第一章的第二点
- 这是带有图片的内容

## 第二章节
- 列表项1
- 列表项2
- 列表项3
- 列表项4
- 列表项5

## 总结
- 总结要点1
- 总结要点2
    """
    
    # 创建Agent
    agent = MarkdownAgent({"llm_model": "gpt-4"})
    
    # 执行Agent
    result_state = await agent.run(state)
    
    # 检查结果
    if result_state.content_structure:
        logger.info(f"Markdown解析成功，标题: {result_state.content_structure.get('title', '无标题')}")
        logger.info(f"章节数量: {len(result_state.content_structure.get('sections', []))}")
    else:
        logger.error("Markdown解析失败!")
    
    return result_state

async def test_ppt_analysis_agent(state=None):
    """测试PPT模板分析Agent"""
    logger.info("===== 测试PPT模板分析Agent =====")
    
    # 如果没有提供状态，创建新的
    if state is None:
        state = AgentState()
    
    # 设置测试PPT模板路径 - 修正路径问题
    template_path = Path(__file__).parent.parent.parent / "libs" / "ppt_manager" / "test" / "testfiles" / "Iphone16Pro.pptx"
    if not template_path.exists():
        logger.error(f"测试模板文件不存在: {template_path}")
        return state
    
    state.ppt_template_path = str(template_path)
    
    # 创建Agent
    agent = PPTAnalysisAgent({"vision_model": "gpt-4-vision"})
    
    # 执行Agent
    result_state = await agent.run(state)
    
    # 检查结果
    if result_state.layout_features:
        logger.info(f"PPT模板分析成功，模板名称: {result_state.layout_features.get('templateName', '未知')}")
        layouts = result_state.layout_features.get('layouts', [])
        logger.info(f"布局数量: {len(layouts) if isinstance(layouts, list) else '未知'}")
    else:
        logger.error("PPT模板分析失败!")
    
    return result_state

async def test_layout_decision_agent(state=None):
    """测试布局决策Agent"""
    logger.info("===== 测试布局决策Agent =====")
    
    # 如果没有提供状态，尝试运行前面的Agent
    if state is None or not state.content_structure or not state.layout_features:
        logger.info("需要先运行Markdown解析和PPT模板分析")
        state = await test_markdown_agent()
        state = await test_ppt_analysis_agent(state)
    
    # 创建Agent
    agent = LayoutDecisionAgent({"embedding_model": "text-embedding-3-large"})
    
    # 执行Agent
    result_state = await agent.run(state)
    
    # 检查结果
    if result_state.decision_result:
        slides = result_state.decision_result.get('slides', [])
        logger.info(f"布局决策成功，幻灯片数量: {len(slides)}")
        
        # 打印每张幻灯片的类型
        for i, slide in enumerate(slides):
            logger.info(f"  幻灯片{i+1}: {slide.get('type', '未知')}")
    else:
        logger.error("布局决策失败!")
    
    return result_state

async def test_ppt_generator_agent(state=None):
    """测试PPT生成Agent"""
    logger.info("===== 测试PPT生成Agent =====")
    
    # 如果没有提供状态，尝试运行前面的Agent
    if state is None or not state.decision_result:
        logger.info("需要先运行布局决策")
        state = await test_layout_decision_agent()
    
    # 创建Agent
    agent = PPTGeneratorAgent({})
    
    # 执行Agent
    result_state = await agent.run(state)
    
    # 检查结果 - 使用output_ppt_path而不是ppt_file_path
    if hasattr(result_state, 'output_ppt_path') and result_state.output_ppt_path:
        logger.info(f"PPT生成成功，文件保存至: {result_state.output_ppt_path}")
        
        # 检查文件是否存在
        if os.path.exists(result_state.output_ppt_path):
            file_size = os.path.getsize(result_state.output_ppt_path)
            logger.info(f"文件大小: {file_size} 字节")
        else:
            logger.error(f"文件不存在: {result_state.output_ppt_path}")
    else:
        logger.error("PPT生成失败!")
    
    return result_state

async def test_validator_agent(state=None):
    """测试验证Agent"""
    logger.info("===== 测试验证Agent =====")
    
    # 如果没有提供状态，尝试运行前面的Agent
    if state is None or not hasattr(state, 'output_ppt_path') or not state.output_ppt_path:
        logger.info("需要先运行PPT生成")
        state = await test_ppt_generator_agent()
    
    # 创建Agent
    agent = ValidatorAgent({})
    
    # 执行Agent
    result_state = await agent.run(state)
    
    # 检查结果
    logger.info(f"验证尝试次数: {result_state.validation_attempts}")
    
    # 检查是否有失败记录
    failures = result_state.failures
    if failures:
        logger.error(f"验证发现{len(failures)}个问题:")
        for failure in failures:
            logger.error(f"  - {failure}")
    else:
        logger.info("验证通过，未发现问题")
    
    return result_state

async def test_full_workflow():
    """测试完整工作流"""
    logger.info("===== 测试完整工作流 =====")
    
    # 按顺序执行所有Agent
    state = await test_markdown_agent()
    state = await test_ppt_analysis_agent(state)
    state = await test_layout_decision_agent(state)
    state = await test_ppt_generator_agent(state)
    state = await test_validator_agent(state)
    
    logger.info("===== 工作流测试完成 =====")
    
    # 打印最终状态的会话ID和检查点
    logger.info(f"会话ID: {state.session_id}")
    logger.info(f"检查点: {state.checkpoints}")
    
    return state

if __name__ == "__main__":
    # 创建工作空间目录
    from config.settings import settings
    
    # 运行测试
    test_function = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    if test_function == "markdown":
        asyncio.run(test_markdown_agent())
    elif test_function == "ppt_analysis":
        asyncio.run(test_ppt_analysis_agent())
    elif test_function == "layout_decision":
        asyncio.run(test_layout_decision_agent())
    elif test_function == "ppt_generator":
        asyncio.run(test_ppt_generator_agent())
    elif test_function == "validator":
        asyncio.run(test_validator_agent())
    else:
        # 默认测试完整工作流
        asyncio.run(test_full_workflow()) 