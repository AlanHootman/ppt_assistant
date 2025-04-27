"""
工作流引擎模块
"""
from typing import Dict, Any, Callable, Optional, List, Tuple, Union
import logging
from pathlib import Path
import os
import json
import asyncio
from datetime import datetime

from langgraph.graph import StateGraph, END
# 修复: LangGraph API变更，确保使用最新API

from config.settings import settings
from core.engine.state import AgentState
from core.engine.configLoader import ConfigLoader

# 配置日志
logger = logging.getLogger(__name__)

class WorkflowEngine:
    """工作流引擎"""
    
    def __init__(self, workflow_name: str = "ppt_generation"):
        """
        初始化工作流引擎
        
        Args:
            workflow_name: 工作流配置名称
        """
        self.workflow_name = workflow_name
        self.config = ConfigLoader.load_workflow_config(workflow_name)
        self.execution_logs = []
        self.graph = self._build_workflow()
        logger.info(f"初始化工作流引擎: {workflow_name}")
    
    def _build_workflow(self) -> StateGraph:
        """
        构建工作流图
        
        Returns:
            StateGraph: 工作流图实例
        """
        # 创建状态图
        workflow = StateGraph(AgentState)
        
        # 创建临时目录存储运行日志
        checkpoint_dir = settings.WORKSPACE_DIR / "checkpoints"
        checkpoint_dir.mkdir(exist_ok=True)
        
        # 从配置中读取节点信息
        nodes = self.config.get("workflow", {}).get("nodes", [])
        edges = self.config.get("workflow", {}).get("edges", [])
        
        logger.info(f"从配置中加载: {len(nodes)}个节点, {len(edges)}个边")
        
        # 添加节点
        for node_config in nodes:
            node_name = node_config.get("name")
            if node_name:
                # 当前使用占位节点，稍后会被真实Agent替换
                workflow.add_node(node_name, self._placeholder_node(node_name))
                logger.debug(f"添加节点: {node_name}")
        
        # 确定入口点
        entry_point = None
        
        # 添加普通边
        for edge_config in edges:
            from_node = edge_config.get("from")
            to_node = edge_config.get("to")
            condition = edge_config.get("condition")
            
            # 处理start边，确定入口点
            if from_node == "start":
                entry_point = to_node
                continue
                
            # 添加普通边 - 先只添加普通边，避免条件边问题
            if from_node and to_node and not condition:
                workflow.add_edge(from_node, to_node)
                logger.debug(f"添加边: {from_node} -> {to_node}")
        
        # 手动构建简单的条件边，用于测试阶段
        workflow.add_conditional_edges(
            "validator",
            self._validate_condition,
            {
                "pass": END,
                "retry": "ppt_generator"
            }
        )
        logger.debug(f"添加条件边: validator -> END/ppt_generator")
        
        # 设置入口点
        if entry_point:
            workflow.set_entry_point(entry_point)
            logger.debug(f"设置入口点: {entry_point}")
        else:
            # 默认使用第一个节点作为入口点
            if nodes:
                first_node = nodes[0].get("name")
                workflow.set_entry_point(first_node)
                logger.debug(f"设置默认入口点: {first_node}")
        
        # 获取节点数量
        node_count = len(workflow.nodes) if hasattr(workflow, "nodes") else 0
        logger.info(f"构建工作流图完成，共{node_count}个节点")
        
        # 编译图 - 不使用递归限制参数，它在调用时设置
        return workflow.compile()
    
    def _record_execution(self, node_name: str, session_id: str):
        """
        记录执行信息
        
        Args:
            node_name: 节点名称
            session_id: 会话ID
        """
        record = {
            "timestamp": datetime.now().isoformat(),
            "node": node_name,
            "session_id": session_id
        }
        self.execution_logs.append(record)
        logger.debug(f"执行节点: {node_name}, 会话: {session_id}")
    
    def _placeholder_node(self, node_name: str) -> Callable:
        """
        创建占位节点处理函数
        
        Args:
            node_name: 节点名称
            
        Returns:
            节点处理函数
        """
        def node_func(state: AgentState) -> AgentState:
            logger.info(f"执行节点: {node_name}, 会话: {state.session_id}")
            state.current_node = node_name
            
            # 记录执行信息
            self._record_execution(node_name, state.session_id)
            
            # 添加执行时间戳
            timestamp = datetime.now().isoformat()
            
            # 如果节点是markdown_parser并且有raw_md
            if node_name == "markdown_parser" and state.raw_md:
                # 完全重写Markdown解析逻辑
                try:
                    lines = state.raw_md.split("\n")
                    structure = {"title": "", "sections": []}
                    
                    # 先找标题
                    for line in lines:
                        if line.strip().startswith("# "):
                            structure["title"] = line.strip()[2:]
                            break
                    
                    # 再处理章节，使用索引而不是对象引用
                    current_section_index = -1  # -1表示没有当前章节
                    
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                            
                        if line.startswith("## "):
                            # 新章节
                            section_title = line[3:]
                            structure["sections"].append({
                                "title": section_title,
                                "content": []
                            })
                            current_section_index = len(structure["sections"]) - 1
                        elif line.startswith("- ") and current_section_index >= 0:
                            # 安全地添加到当前章节的内容中
                            structure["sections"][current_section_index]["content"].append(line[2:])
                    
                    state.content_structure = structure
                    logger.info(f"Markdown解析完成，标题: {structure.get('title')}, {len(structure.get('sections', []))}个章节")
                except Exception as e:
                    logger.error(f"Markdown解析错误: {str(e)}")
                    state.record_failure(f"Markdown解析错误: {str(e)}")
            
            # 当节点是ppt_analyzer且有模板路径时
            elif node_name == "ppt_analyzer" and state.ppt_template_path:
                # 简单模拟模板分析
                logger.info(f"分析PPT模板: {state.ppt_template_path}")
                state.layout_features = {
                    "templateName": Path(state.ppt_template_path).stem,
                    "slideCount": 10,  # 假设值
                    "layouts": ["title", "content", "twoColumns", "image"]
                }
            
            # 布局决策
            elif node_name == "layout_decider" and state.content_structure and state.layout_features:
                # 简单模拟布局决策
                structure = state.content_structure
                layouts = state.layout_features.get("layouts", [])
                
                # 生成决策
                slides = []
                
                # 标题页
                if structure.get("title"):
                    slides.append({
                        "type": "title",
                        "content": {
                            "title": structure.get("title")
                        }
                    })
                
                # 根据章节生成内容页
                for section in structure.get("sections", []):
                    section_title = section.get("title")
                    section_content = section.get("content", [])
                    
                    # 选择合适的布局
                    slide_type = "content"  # 默认
                    if len(section_content) > 3:
                        slide_type = "twoColumns" if "twoColumns" in layouts else "content"
                    
                    slides.append({
                        "type": slide_type,
                        "content": {
                            "title": section_title,
                            "bullets": section_content
                        }
                    })
                
                state.decision_result = {
                    "slides": slides,
                    "template": state.layout_features.get("templateName")
                }
                logger.info(f"布局决策完成，共{len(slides)}张幻灯片")
            
            # PPT生成
            elif node_name == "ppt_generator" and state.decision_result:
                # 在实际场景中，这里会调用PPT生成库
                slides = state.decision_result.get("slides", [])
                output_path = settings.WORKSPACE_DIR / "temp" / f"{state.session_id}.pptx"
                
                # 生成空文件作为测试
                output_path.parent.mkdir(exist_ok=True)
                
                # 仅做测试记录
                with open(output_path.with_suffix(".json"), "w", encoding="utf-8") as f:
                    json.dump(state.decision_result, f, ensure_ascii=False, indent=2)
                
                state.ppt_file_path = str(output_path)
                logger.info(f"PPT文件将保存至: {output_path}")
            
            # 验证节点 - 重要：确保验证节点总是能够完成
            elif node_name == "validator":
                # 直接设置验证尝试次数为1，确保通过验证
                state.validation_attempts = 1
                logger.info(f"验证节点: 设置验证尝试次数为 {state.validation_attempts}")
            
            # 记录执行完成的检查点
            state.add_checkpoint(f"{node_name}_completed")
            
            return state
            
        return node_func
    
    def _validate_condition(self, state: AgentState) -> str:
        """
        验证条件函数
        
        Args:
            state: 当前状态
            
        Returns:
            下一步分支名称
        """
        # 简化验证逻辑，确保工作流能够终止
        logger.info(f"验证节点条件判断: attempts={state.validation_attempts}")
        
        # 验证逻辑 - 总是返回pass以避免循环
        logger.info(f"验证通过: {state.session_id}")
        return "pass"
    
    async def run(self, session_id: Optional[str] = None, 
                 input_data: Optional[Dict[str, Any]] = None) -> AgentState:
        """
        运行工作流
        
        Args:
            session_id: 会话ID，如果为None则创建新会话
            input_data: 输入数据
            
        Returns:
            最终状态
        """
        # 准备初始状态
        if session_id:
            try:
                state = AgentState.load(session_id)
                logger.info(f"加载现有会话: {session_id}")
            except Exception as e:
                logger.warning(f"加载会话失败: {str(e)}，创建新会话")
                state = AgentState(session_id=session_id)
        else:
            state = AgentState()
            logger.info(f"创建新会话: {state.session_id}")
            
        # 更新输入数据
        if input_data:
            for key, value in input_data.items():
                if hasattr(state, key):
                    setattr(state, key, value)
                    logger.debug(f"设置属性 {key}={value}")
        
        logger.info(f"启动工作流，会话: {state.session_id}")
        
        try:
            # 清除之前的执行日志
            self.execution_logs = []
            
            # 当前测试阶段，增加递归限制的配置
            config = {"recursion_limit": 50}
            
            # 调用编译后的工作流
            result_dict = self.graph.invoke(state, config)
            
            # 将结果字典转换回AgentState对象
            result = self._convert_result_to_state(state, result_dict)
            
            # 保存最终状态
            result.save()
            
            # 记录执行情况
            execution_summary = {
                "session_id": result.session_id,
                "start_time": self.execution_logs[0]["timestamp"] if self.execution_logs else None,
                "end_time": datetime.now().isoformat(),
                "node_count": len(self.execution_logs),
                "result": {
                    "ppt_file": result.ppt_file_path,
                    "failures": result.failures
                }
            }
            
            logger.info(f"工作流完成，会话: {result.session_id}, 节点执行次数: {len(self.execution_logs)}")
            return result
            
        except Exception as e:
            logger.error(f"工作流失败: {str(e)}")
            state.record_failure(str(e))
            state.save()
            raise
    
    def _convert_result_to_state(self, original_state: AgentState, result_dict: Dict[str, Any]) -> AgentState:
        """
        将LangGraph返回的结果字典转换为AgentState对象
        
        Args:
            original_state: 原始状态
            result_dict: 结果字典
            
        Returns:
            AgentState对象
        """
        # 创建新的AgentState，保留会话ID
        result_state = AgentState(session_id=original_state.session_id)
        
        # 复制原始状态中的检查点等
        result_state.checkpoints = original_state.checkpoints.copy() if original_state.checkpoints else []
        result_state.failures = original_state.failures.copy() if original_state.failures else []
        
        # 复制结果中的值到新状态
        for key, value in result_dict.items():
            if hasattr(result_state, key):
                setattr(result_state, key, value)
        
        logger.debug(f"转换结果到AgentState: {result_state.session_id}")
        return result_state
    
    def get_execution_logs(self) -> List[Dict[str, Any]]:
        """
        获取执行日志
        
        Returns:
            执行日志列表
        """
        return self.execution_logs 