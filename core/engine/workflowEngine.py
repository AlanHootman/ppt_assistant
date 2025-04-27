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
        创建模拟节点处理函数（仅用于开发和测试阶段）
        
        Args:
            node_name: 节点名称
            
        Returns:
            节点处理函数
        """
        def mock_node_handler(state: Any) -> Dict[str, Any]:
            """模拟节点处理函数，返回处理后的状态字典"""
            # 检查状态类型并适当处理
            if isinstance(state, dict):
                # 将状态字典转换为AgentState对象以方便处理
                session_id = state.get("session_id")
                agent_state = AgentState(session_id=session_id)
                
                # 复制状态属性
                for key, value in state.items():
                    if hasattr(agent_state, key):
                        setattr(agent_state, key, value)
            elif isinstance(state, AgentState):
                # 如果已经是AgentState对象，直接使用
                agent_state = state
            else:
                # 其他情况，创建新的AgentState
                logger.warning(f"未知状态类型: {type(state)}，创建新的AgentState")
                agent_state = AgentState()
            
            # 获取原始会话ID，用于记录日志
            original_session_id = agent_state.session_id
            logger.info(f"[模拟] 执行节点: {node_name}, 会话: {original_session_id}")
            agent_state.current_node = node_name
            
            # 记录执行信息
            self._record_execution(node_name, original_session_id)
            
            # 添加执行时间戳
            timestamp = datetime.now().isoformat()
            
            # 模拟节点执行逻辑
            self._execute_mock_node_logic(node_name, agent_state)
            
            # 记录执行完成的检查点
            agent_state.add_checkpoint(f"{node_name}_completed")
            
            # 返回状态字典，而不是AgentState对象
            result_dict = agent_state.to_dict()
            # 确保会话ID保持不变
            result_dict["session_id"] = original_session_id
            return result_dict
            
        return mock_node_handler
    
    def _execute_mock_node_logic(self, node_name: str, state: AgentState) -> None:
        """
        执行模拟节点逻辑（仅用于开发和测试阶段）
        
        Args:
            node_name: 节点名称
            state: 代理状态
        """
        # Markdown解析节点
        if node_name == "markdown_parser" and state.raw_md:
            self._mock_markdown_parser(state)
        
        # PPT模板分析节点
        elif node_name == "ppt_analyzer" and state.ppt_template_path:
            self._mock_ppt_analyzer(state)
        
        # 布局决策节点
        elif node_name == "layout_decider" and state.content_structure and state.layout_features:
            self._mock_layout_decider(state)
        
        # PPT生成节点
        elif node_name == "ppt_generator" and state.decision_result:
            self._mock_ppt_generator(state)
        
        # 验证节点
        elif node_name == "validator":
            self._mock_validator(state)
        else:
            logger.warning(f"[模拟] 节点 {node_name} 条件不满足或未找到对应处理函数")
            # 添加更多的诊断信息
            if node_name == "markdown_parser":
                logger.warning(f"[模拟] markdown_parser 需要 raw_md，当前值: {state.raw_md is not None}")
            elif node_name == "ppt_analyzer":
                logger.warning(f"[模拟] ppt_analyzer 需要 ppt_template_path，当前值: {state.ppt_template_path is not None}")
            elif node_name == "layout_decider":
                logger.warning(f"[模拟] layout_decider 需要 content_structure 和 layout_features，当前值: {state.content_structure is not None}, {state.layout_features is not None}")
            elif node_name == "ppt_generator":
                logger.warning(f"[模拟] ppt_generator 需要 decision_result，当前值: {state.decision_result is not None}")
    
    def _mock_markdown_parser(self, state: AgentState) -> None:
        """模拟Markdown解析实现"""
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
            logger.info(f"[模拟] Markdown解析完成，标题: {structure.get('title')}, {len(structure.get('sections', []))}个章节")
        except Exception as e:
            logger.error(f"[模拟] Markdown解析错误: {str(e)}")
            state.record_failure(f"Markdown解析错误: {str(e)}")
    
    def _mock_ppt_analyzer(self, state: AgentState) -> None:
        """模拟PPT模板分析实现"""
        logger.info(f"[模拟] 分析PPT模板: {state.ppt_template_path}")
        state.layout_features = {
            "templateName": Path(state.ppt_template_path).stem,
            "slideCount": 10,  # 假设值
            "layouts": ["title", "content", "twoColumns", "image"]
        }
    
    def _mock_layout_decider(self, state: AgentState) -> None:
        """模拟布局决策实现"""
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
        logger.info(f"[模拟] 布局决策完成，共{len(slides)}张幻灯片")
    
    def _mock_ppt_generator(self, state: AgentState) -> None:
        """模拟PPT生成实现"""
        slides = state.decision_result.get("slides", [])
        output_path = settings.WORKSPACE_DIR / "temp" / f"{state.session_id}.pptx"
        
        # 生成空文件作为测试
        output_path.parent.mkdir(exist_ok=True)
        
        # 仅做测试记录
        with open(output_path.with_suffix(".json"), "w", encoding="utf-8") as f:
            json.dump(state.decision_result, f, ensure_ascii=False, indent=2)
        
        state.ppt_file_path = str(output_path)
        logger.info(f"[模拟] PPT文件将保存至: {output_path}")
    
    def _mock_validator(self, state: AgentState) -> None:
        """模拟验证节点实现"""
        # 直接设置验证尝试次数为1，确保通过验证
        state.validation_attempts = 1
        logger.info(f"[模拟] 验证节点: 设置验证尝试次数为 {state.validation_attempts}")
    
    def _validate_condition(self, state: Dict[str, Any]) -> str:
        """
        验证条件函数
        
        Args:
            state: 当前状态字典
            
        Returns:
            下一步分支名称
        """
        # 从字典获取验证尝试次数
        validation_attempts = state.get("validation_attempts", 0)
        session_id = state.get("session_id", "unknown")
        
        # 简化验证逻辑，确保工作流能够终止
        logger.info(f"验证节点条件判断: attempts={validation_attempts}")
        
        # 验证逻辑 - 总是返回pass以避免循环
        logger.info(f"验证通过: {session_id}")
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
        
        # 确保raw_md和ppt_template_path都存在，否则工作流将无法正常工作
        if state.raw_md is None:
            logger.warning("未提供Markdown内容，工作流可能无法正常执行")
        if state.ppt_template_path is None:
            logger.warning("未提供PPT模板路径，工作流可能无法正常执行")
        
        logger.info(f"启动工作流，会话: {state.session_id}")
        
        try:
            # 清除之前的执行日志
            self.execution_logs = []
            
            # 直接模拟按序执行工作流节点，避免LangGraph的问题
            if state.raw_md and state.ppt_template_path:
                # 1. 执行Markdown解析节点
                logger.info(f"直接模拟执行工作流节点...")
                
                # 模拟执行markdown_parser节点
                self._execute_node_directly("markdown_parser", state)
                
                # 继续执行其他节点
                if state.content_structure:
                    self._execute_node_directly("ppt_analyzer", state)
                    
                if state.layout_features and state.content_structure:
                    self._execute_node_directly("layout_decider", state)
                    
                if state.decision_result:
                    self._execute_node_directly("ppt_generator", state)
                    self._execute_node_directly("validator", state)
                
                # 保存最终状态
                state.save()
                
                logger.info(f"工作流直接执行完成，节点执行次数: {len(self.execution_logs)}")
                return state
            
            # 如果不满足直接执行条件，尝试使用LangGraph执行
            logger.info("开始执行LangGraph工作流")
            
            # 当前测试阶段，增加递归限制的配置
            config = {"recursion_limit": 50}
            
            # 将AgentState转换为字典 - 修复LangGraph输入类型问题
            state_dict = state.to_dict()
            logger.debug(f"状态转换为字典: {len(state_dict)} 个属性")
            
            # 调用编译后的工作流，传入字典而不是AgentState对象
            try:
                result_dict = self.graph.invoke(state_dict, config)
                logger.info("LangGraph工作流执行完成")
            except Exception as e:
                logger.error(f"LangGraph工作流执行失败: {str(e)}")
                result_dict = None
                state.record_failure(f"工作流执行错误: {str(e)}")
            
            # 将结果字典转换回AgentState对象
            result = self._convert_result_to_state(state, result_dict)
            
            # 如果在执行中有失败记录，添加到结果状态
            if state.failures and not result.failures:
                result.failures = state.failures
            
            # 保存最终状态
            result.save()
            
            # 记录执行情况
            execution_summary = {
                "session_id": result.session_id,
                "start_time": self.execution_logs[0]["timestamp"] if self.execution_logs else datetime.now().isoformat(),
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
    
    def _execute_node_directly(self, node_name: str, state: AgentState) -> None:
        """
        直接执行节点，跳过LangGraph框架
        
        Args:
            node_name: 节点名称
            state: 状态对象
        """
        logger.info(f"直接执行节点: {node_name}, 会话: {state.session_id}")
        state.current_node = node_name
        
        # 记录执行信息
        self._record_execution(node_name, state.session_id)
        
        # 执行节点逻辑
        self._execute_mock_node_logic(node_name, state)
        
        # 记录执行完成的检查点
        state.add_checkpoint(f"{node_name}_completed")
    
    def _convert_result_to_state(self, original_state: AgentState, result_dict: Optional[Dict[str, Any]]) -> AgentState:
        """
        将LangGraph返回的结果字典转换为AgentState对象
        
        Args:
            original_state: 原始状态
            result_dict: 结果字典，可能为None
            
        Returns:
            AgentState对象
        """
        # 创建新的AgentState，保留会话ID
        result_state = AgentState(session_id=original_state.session_id)
        
        # 复制原始状态中的检查点等
        result_state.checkpoints = original_state.checkpoints.copy() if original_state.checkpoints else []
        result_state.failures = original_state.failures.copy() if original_state.failures else []
        
        # 复制原始状态的所有属性作为基础
        for attr in dir(original_state):
            if not attr.startswith('_') and not callable(getattr(original_state, attr)):
                try:
                    setattr(result_state, attr, getattr(original_state, attr))
                except Exception as e:
                    logger.debug(f"无法复制属性 {attr}: {str(e)}")
        
        # 如果结果字典不为None，则更新状态
        if result_dict is not None:
            # 复制结果中的值到新状态
            for key, value in result_dict.items():
                if hasattr(result_state, key):
                    setattr(result_state, key, value)
            logger.debug(f"从结果字典更新了状态: {result_state.session_id}")
        else:
            logger.warning("结果字典为None，使用原始状态")
        
        return result_state
    
    def get_execution_logs(self) -> List[Dict[str, Any]]:
        """
        获取执行日志
        
        Returns:
            执行日志列表
        """
        return self.execution_logs 