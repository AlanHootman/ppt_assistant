#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
幻灯片生成Agent模块

负责根据内容规划生成具体的幻灯片内容，包括标题、文本、图片等元素。
使用PPTManager在已有PPTX模板上进行操作，不直接生成幻灯片内容。
同时集成了验证功能，直接对生成的幻灯片进行质量验证。
"""

import logging
import json
from typing import Dict, Any, List, Optional, Tuple
import datetime
from pathlib import Path
import asyncio

from core.agents.base_agent import BaseAgent
from core.engine.state import AgentState
from core.llm.model_manager import ModelManager
from core.utils.model_helper import ModelHelper
from core.utils.ppt_agent_helper import PPTAgentHelper, EnumEncoder
from core.utils.ppt_operations import PPTOperationExecutor
from config.prompts.slide_generator_prompts import (
    LLM_PPT_ELEMENT_MATCHING_PROMPT
)
from config.settings import settings

logger = logging.getLogger(__name__)

class SlideGeneratorAgent(BaseAgent):
    """幻灯片生成Agent，负责基于PPT模板生成具体的幻灯片内容，并进行自验证"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化幻灯片生成Agent
        
        Args:
            config: Agent配置
        """
        super().__init__(config)
        # 初始化模型管理器和辅助工具
        self.model_manager = ModelManager()
        self.model_helper = ModelHelper(self.model_manager)
        
        # 获取模型配置
        model_config = self.model_helper.get_model_config(config, "text")
        self.llm_model = model_config.get("model")
        self.temperature = model_config.get("temperature")
        self.max_tokens = model_config.get("max_tokens")
        self.max_retries = model_config.get("max_retries", 3)
        
        # 多协程处理配置 - 优先使用配置参数，如果没有则使用环境变量设置
        self.use_parallel = config.get("use_parallel_generation", settings.USE_PARALLEL_GENERATION)
        self.max_workers = config.get("generation_max_workers", settings.GENERATION_MAX_WORKERS)
        
        # 初始化PPT管理器
        self.ppt_manager = PPTAgentHelper.init_ppt_manager()
        if not self.ppt_manager:
            raise ImportError("无法初始化PPT管理器，请确保PPT Manager已正确安装")
        
        # 初始化PPT操作执行器
        self.ppt_operation_executor = PPTOperationExecutor(
            ppt_manager=self.ppt_manager,
            agent_name="SlideGeneratorAgent"
        )
        
        logger.info(f"初始化SlideGeneratorAgent，使用模型: {self.llm_model}，最大重试次数: {self.max_retries}, "
                   f"并行处理: {'启用' if self.use_parallel else '禁用'}, "
                   f"最大协程数: {self.max_workers or '自动'}")
    
    async def run(self, state: AgentState) -> AgentState:
        """
        执行幻灯片生成逻辑，生成所有规划的幻灯片

        Args:
            state: 工作流引擎状态

        Returns:
            更新后的工作流引擎状态
        """
        logger.info("开始生成所有规划的幻灯片")
        
        try:
            # 第一步：准备工作 - 加载和检查必要资源
            presentation = await self._prepare_presentation(state)
            
            # 检查内容计划
            if not self._check_content_plan(state):
                return state
            
            # 根据配置决定使用串行或并行处理
            if self.use_parallel:
                logger.info("使用并行处理生成幻灯片")
                await self._generate_all_slides_parallel(state, presentation)
            else:
                logger.info("使用串行处理生成幻灯片")
                await self._generate_all_slides(state, presentation)
            
            # 更新状态
            state.presentation = presentation
            state.has_more_content = False  # 标记所有内容已处理完毕
            
            # 记录完成信息
            total_sections = len(state.content_plan)
            logger.info(f"已完成所有 {len(state.generated_slides)}/{total_sections} 张幻灯片的生成")
            
            return state
            
        except Exception as e:
            error_msg = f"幻灯片生成流程失败: {str(e)}"
            logger.error(error_msg)
            logger.exception(e)
            state.record_failure(error_msg)
            raise RuntimeError(error_msg)
    
    async def _prepare_presentation(self, state: AgentState) -> Any:
        """
        准备演示文稿对象
        
        Args:
            state: 当前状态
            
        Returns:
            演示文稿对象
        """
        # 获取PPT模板路径
        template_path = getattr(state, 'template_path', None) or getattr(state, 'ppt_template_path', None)
        
        # 获取或加载presentation
        presentation = getattr(state, 'presentation', None)
        if not presentation:
            logger.info(f"加载PPT模板: {template_path}")
            presentation = self.ppt_manager.load_presentation(template_path)
        
        return presentation
    
    def _check_content_plan(self, state: AgentState) -> bool:
        """
        检查状态中是否有有效的内容计划
        
        Args:
            state: 工作流状态
            
        Returns:
            内容计划是否有效
        """
        if not hasattr(state, 'content_plan') or not state.content_plan:
            error_msg = "无法生成幻灯片：找不到内容计划"
            logger.error(error_msg)
            state.record_failure(error_msg)
            return False
            
        # 初始化存储生成幻灯片的列表
        state.generated_slides = []
        return True
    
    async def _generate_all_slides(self, state: AgentState, presentation: Any) -> None:
        """
        生成所有规划的幻灯片
        
        Args:
            state: 工作流状态
            presentation: 演示文稿对象
        """
        # 用于跟踪已经使用过的幻灯片索引
        used_slide_indices = set()
        
        # 循环处理所有章节内容
        total_sections = len(state.content_plan)
        logger.info(f"开始生成 {total_sections} 张幻灯片")
        
        for section_index, current_section in enumerate(state.content_plan):
            logger.info(f"生成第 {section_index + 1}/{total_sections} 张幻灯片: {current_section.get('slide_type', '未知类型')}")
            
            try:
                # 1. 更新当前章节索引
                state.current_section_index = section_index
                
                # 2. 生成单个幻灯片
                slide_index, updated_presentation = await self._generate_single_slide(
                    state, presentation, current_section, used_slide_indices
                )
                presentation = updated_presentation
                
                # 3. 标记该幻灯片索引已使用
                used_slide_indices.add(slide_index)
                
                # 4. 添加slide_id到幻灯片备注中
                await self._add_slide_id_to_notes(presentation, slide_index, current_section)
                
                # 5. 执行幻灯片内容填充操作
                operations = await self._plan_and_execute_content_operations(
                    presentation, slide_index, current_section
                )
                
                # 6. 记录生成的幻灯片信息
                self._record_generated_slide(state, section_index, slide_index, current_section, operations)
                
            except Exception as e:
                error_msg = f"生成第 {section_index + 1} 张幻灯片失败: {str(e)}"
                logger.error(error_msg)
                logger.exception(e)
                state.record_failure(error_msg)
                # 继续生成其他幻灯片，不中断整个过程
    
    async def _generate_single_slide(self, state: AgentState, presentation: Any, 
                                   current_section: Dict[str, Any], 
                                   used_slide_indices: set) -> Tuple[int, Any]:
        """
        生成单个幻灯片
        
        Args:
            state: 工作流状态
            presentation: 演示文稿对象
            current_section: 当前处理的章节信息
            used_slide_indices: 已使用的幻灯片索引集合
            
        Returns:
            幻灯片索引和更新后的演示文稿
        """
        # 获取模板信息
        template_info = current_section.get("template", {})
        template_slide_index = template_info.get("slide_index")
        template_layout = template_info.get("layout", "")
        
        # 生成幻灯片
        slide_index = -1
        
        # 核心业务逻辑1：如果有指定的slide_index且未被使用过，直接使用该幻灯片
        if template_slide_index is not None and template_slide_index not in used_slide_indices:
            slide_index = template_slide_index
            logger.info(f"使用content_plan中指定的幻灯片: 索引={slide_index}")
        else:
            # 核心业务逻辑2：否则，根据layout创建新幻灯片
            if template_layout:
                logger.info(f"根据layout '{template_layout}' 创建新幻灯片")
                result = self.ppt_manager.create_slide_with_layout(
                    presentation=presentation,
                    layout_name=template_layout
                )
                if result.get("success", False):
                    slide_index = result.get("slide_index")
                    # 使用更新后的演示文稿对象
                    presentation = result.get("presentation", presentation)
                    logger.info(f"创建新幻灯片成功，索引: {slide_index}")
                else:
                    logger.warning(f"根据layout创建幻灯片失败: {result.get('message', '未知错误')}")
            
            # 核心业务逻辑3：如果没有layout或创建失败，尝试使用_find_template_slide查找匹配的布局
            if slide_index == -1:
                logger.info("尝试查找匹配的布局创建幻灯片")
                slide_index, presentation = await self._find_template_slide(state, presentation, current_section)
        
        return slide_index, presentation
    
    def _record_generated_slide(self, state: AgentState, section_index: int, slide_index: int, 
                              current_section: Dict[str, Any], operations: List[Dict[str, Any]]) -> None:
        """
        记录生成的幻灯片信息
        
        Args:
            state: 工作流状态
            section_index: 章节索引
            slide_index: 幻灯片索引
            current_section: 当前处理的章节信息
            operations: 执行的操作列表
        """
        slide_info = {
            "section_index": section_index,
            "slide_index": slide_index,
            "slide_type": current_section.get("slide_type", ""),
            "template_info": current_section.get("template", {}),
            "section_content": current_section,
            "operations": operations,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # 将幻灯片信息添加到已生成列表
        state.generated_slides.append(slide_info)
        logger.info(f"成功生成第 {section_index + 1} 张幻灯片，索引: {slide_index}")
    
    async def _get_operations_from_llm(self, context: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        从LLM获取操作指令
        
        Args:
            context: 上下文字典
            
        Returns:
            操作指令列表
        """
        # 渲染提示词
        prompt = self.model_manager.render_template(LLM_PPT_ELEMENT_MATCHING_PROMPT, context)
        
        try:
            # 调用LLM获取匹配结果，使用重试机制
            response = await self.model_helper.generate_text_with_retry(
                model=self.llm_model,
                prompt=prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                max_retries=self.max_retries
            )
            
            # 解析LLM响应
            parsed_response = self.model_helper.parse_json_response(response, {})
            
            # 处理可能的响应格式：直接操作列表或嵌套在operations字段中
            operations = []
            if isinstance(parsed_response, list):
                # 直接是操作列表
                operations = parsed_response
            elif isinstance(parsed_response, dict) and "operations" in parsed_response:
                # 操作列表嵌套在operations字段中
                operations = parsed_response.get("operations", [])
                if not isinstance(operations, list):
                    logger.warning(f"LLM返回的operations字段不是列表: {operations}")
                    operations = []
            else:
                logger.warning(f"LLM响应格式不符合预期: {parsed_response}")
            
            # 验证每个操作是否是字典
            validated_operations = []
            for op in operations:
                if isinstance(op, dict):
                    validated_operations.append(op)
                else:
                    logger.warning(f"跳过无效的操作: {op}")
            
            if not validated_operations:
                logger.warning("LLM未返回有效的操作指令")
                return []
            
            logger.info(f"成功从LLM获取 {len(validated_operations)} 条操作指令")
            return validated_operations
            
        except Exception as e:
            logger.error(f"从LLM获取操作指令失败: {str(e)}")
            return []
    
    def _build_operation_context(self, slide_elements: List[Dict[str, Any]], current_section: Dict[str, Any]) -> Dict[str, str]:
        """
        构建提示词上下文
        
        Args:
            slide_elements: 幻灯片元素列表
            current_section: 当前处理的章节信息
            
        Returns:
            上下文字典
        """
        return {
            "slide_elements_json": json.dumps(slide_elements, ensure_ascii=False, indent=2, cls=EnumEncoder),
            "content_json": json.dumps(current_section, ensure_ascii=False, indent=2, cls=EnumEncoder)
        }
    
    async def _add_slide_id_to_notes(self, presentation: Any, slide_index: int, current_section: Dict[str, Any]) -> None:
        """
        为幻灯片添加唯一标识符到备注中
        
        Args:
            presentation: 演示文稿对象
            slide_index: 幻灯片索引
            current_section: 当前处理的章节信息
        """
        # 从章节信息中获取slide_id，如果没有则生成新的
        slide_id = current_section.get("slide_id", None)
        if not slide_id:
            slide_id = f"slide_{str(slide_index).zfill(6)}"
            current_section["slide_id"] = slide_id
        
        # 获取幻灯片对象
        try:
            # 获取幻灯片和当前备注
            existing_notes = self.ppt_manager.get_slide_notes(
                presentation=presentation,
                slide_index=slide_index
            )
            
            # 添加或更新备注
            # 处理existing_notes可能是字典或字符串的情况
            if existing_notes is None:
                new_notes = f"slide_id: {slide_id}"
            elif isinstance(existing_notes, dict):
                # 如果是字典，可能需要提取其中的文本内容，或者直接使用新的备注
                logger.info(f"获取到的备注是字典格式: {existing_notes}")
                # 尝试从字典中提取notes或text字段
                notes_text = existing_notes.get('notes', '') or existing_notes.get('text', '')
                if notes_text and isinstance(notes_text, str):
                    new_notes = f"{notes_text}\nslide_id: {slide_id}"
                else:
                    new_notes = f"slide_id: {slide_id}"
            else:
                # 假设是字符串
                new_notes = f"{existing_notes}\nslide_id: {slide_id}" if existing_notes else f"slide_id: {slide_id}"
            
            self.ppt_manager.update_slide_notes(
                presentation=presentation,
                slide_index=slide_index,
                notes=new_notes
            )
            logger.info(f"为幻灯片 {slide_index} 添加ID: {slide_id}")
        except Exception as e:
            logger.error(f"为幻灯片添加ID时出错: {str(e)}")
            logger.exception(e)  # 添加详细的异常信息用于调试
    
    async def _plan_and_execute_content_operations(
        self, presentation: Any, slide_index: int, current_section: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        规划并执行幻灯片内容填充操作
        
        Args:
            presentation: 演示文稿对象
            slide_index: 幻灯片索引
            current_section: 当前处理的章节信息
            
        Returns:
            执行的操作列表
        """
        # 获取幻灯片中的元素
        logger.info(f"获取幻灯片 {slide_index} 的元素信息")
        slide_elements = self.ppt_manager.get_slide_json(
            presentation=presentation,
            slide_index=slide_index
        )
        
        # 规划幻灯片操作
        logger.info("根据内容和布局规划幻灯片操作")
        operations = await self._plan_slide_operations(slide_elements, current_section)
        
        # 执行操作
        if operations:
            logger.info(f"执行 {len(operations)} 个幻灯片操作")
            success = await self._execute_operations(presentation, slide_index, operations)
            if not success:
                logger.warning("执行幻灯片操作时出现问题")
        else:
            logger.warning("没有需要执行的幻灯片操作")
        
        return operations
    
    async def _plan_slide_operations(self, slide_elements: List[Dict[str, Any]], current_section: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        根据幻灯片元素和当前章节内容规划幻灯片操作
        
        Args:
            slide_elements: 幻灯片元素列表
            current_section: 当前处理的章节信息
            
        Returns:
            幻灯片操作列表
        """
        # 构建上下文
        context = self._build_operation_context(slide_elements, current_section)
        
        # 从LLM获取操作指令
        logger.info("从LLM获取幻灯片操作指令")
        operations = await self._get_operations_from_llm(context)
        
        if not operations:
            logger.warning("LLM未返回有效的操作指令")
            return []
        
        logger.info(f"成功获取 {len(operations)} 条操作指令")
        return operations
    
    async def _execute_operations(self, presentation: Any, slide_index: int, operations: List[Dict[str, Any]]) -> bool:
        """
        执行幻灯片操作
        
        Args:
            presentation: 演示文稿对象
            slide_index: 幻灯片索引
            operations: 操作列表
            
        Returns:
            操作是否全部成功
        """
        if not operations:
            logger.warning("没有操作需要执行")
            return True
            
        # 确保operations是列表
        if not isinstance(operations, list):
            logger.error(f"operations不是列表类型: {type(operations)}")
            return False
        
        # 过滤掉非字典类型的操作
        valid_operations = []
        for op in operations:
            if isinstance(op, dict):
                valid_operations.append(op)
            else:
                logger.warning(f"跳过无效的操作类型: {type(op)}, 值: {op}")
        
        if not valid_operations:
            logger.warning("没有有效的操作需要执行")
            return True
            
        # 使用 execute_batch_operations 方法执行所有操作
        try:
            result = await self.ppt_operation_executor.execute_batch_operations(
                presentation=presentation,
                slide_index=slide_index,
                operations=valid_operations
            )
            
            success = result.get("success", False)
            if not success:
                logger.warning("执行幻灯片操作时出现问题")
            
            return success
        except Exception as e:
            logger.error(f"执行操作时发生异常: {str(e)}")
            logger.exception(e)
            return False
    
    async def _create_new_slide_with_same_layout(self, presentation: Any, slide_index: int, current_section: Optional[Dict[str, Any]] = None) -> Tuple[int, Any]:
        """
        创建一个与指定幻灯片具有相同布局的新幻灯片
        
        Args:
            presentation: 演示文稿对象
            slide_index: 参考幻灯片索引
            current_section: 当前处理的章节信息
            
        Returns:
            (新幻灯片索引, 更新后的演示文稿)
        """
        try:
            # 获取参考幻灯片的布局
            layout_json = self.ppt_manager.get_slide_layout_json(
                presentation=presentation,
                slide_index=slide_index
            )
            layout_name = layout_json.get("layout_name", "")
            logger.info(f"从幻灯片 {slide_index} 获取布局: {layout_name}")
            
            # 创建新幻灯片
            result = self.ppt_manager.create_slide_with_layout(
                presentation=presentation,
                layout_name=layout_name
            )
            
            if result.get("success", False):
                new_slide_index = result.get("slide_index")
                # 使用更新后的演示文稿对象
                presentation = result.get("presentation", presentation)
                logger.info(f"创建新幻灯片，索引: {new_slide_index}，使用布局: {layout_name}")
                
                # 如果提供了章节信息，将slide_id添加到幻灯片备注中
                if current_section is not None:
                    await self._add_slide_id_to_notes(presentation, new_slide_index, current_section)
                
                return new_slide_index, presentation
            else:
                logger.error(f"创建新幻灯片失败: {result.get('message', '未知错误')}")
                return -1, presentation
            
        except Exception as e:
            logger.error(f"创建与幻灯片 {slide_index} 相同布局的新幻灯片时出错: {str(e)}")
            # 返回非法的索引和原始演示文稿
            return -1, presentation
    
    async def _find_template_slide(self, state: AgentState, presentation: Any, current_section: Dict[str, Any]) -> Tuple[int, Any]:
        """
        根据内容类型查找合适的模板幻灯片
        
        Args:
            state: 工作流状态
            presentation: 演示文稿对象
            current_section: 当前处理的章节信息
            
        Returns:
            (幻灯片索引, 更新后的演示文稿)
        """
        logger.info(f"查找适合的幻灯片布局")
        
        # 尝试查找匹配的布局
        layout_found = False
        slide_index = -1
        
        try:
            # 获取PPT的JSON结构
            ppt_json = self.ppt_manager.get_presentation_json(presentation, include_details=False)
            slides_count = ppt_json.get("slide_count", 0)
            slide_layouts = []
            
            # 获取所有幻灯片的布局名称
            for i in range(slides_count):
                layout_json = self.ppt_manager.get_slide_layout_json(
                    presentation=presentation,
                    slide_index=i
                )
                layout_name = layout_json.get("layout_name", "")
                slide_layouts.append({"index": i, "layout": layout_name.lower()})
            
            # 查找"title_content"或"标题和内容"布局
            for slide_layout in slide_layouts:
                layout_name = slide_layout["layout"]
                if "title" in layout_name and "content" in layout_name:
                    slide_index = slide_layout["index"]
                    layout_found = True
                    logger.info(f"找到标题和内容布局: 索引={slide_index}, 布局={layout_name}")
                    break
            
            # 如果找不到匹配的布局，使用默认布局（通常是索引为1的布局，即内容页）
            if not layout_found:
                logger.warning(f"找不到标题和内容布局，将使用默认布局")
                # 使用默认布局（通常是索引为1的布局，即内容页）
                default_index = 1 if slides_count > 1 else 0
                slide_index = default_index
                layout_found = True
                layout_name = slide_layouts[slide_index]["layout"] if slide_index < len(slide_layouts) else "未知"
                logger.info(f"使用默认布局: 索引={slide_index}, 布局={layout_name}")
            
            # 以找到的幻灯片为模板创建新幻灯片
            slide_index, presentation = await self._create_new_slide_with_same_layout(
                presentation, slide_index, current_section
            )
            
            return slide_index, presentation
            
        except Exception as e:
            logger.error(f"查找模板幻灯片时出错: {str(e)}")
            raise RuntimeError(f"无法找到或创建模板幻灯片: {str(e)}")
          
    def add_checkpoint(self, state: AgentState) -> None:
        """
        添加工作流检查点
        
        Args:
            state: 工作流状态
        """
        state.add_checkpoint("slide_generator_completed")
        logger.info("添加检查点: slide_generator_completed")
    
    async def _generate_all_slides_parallel(self, state: AgentState, presentation: Any) -> None:
        """
        并行生成所有规划的幻灯片
        
        Args:
            state: 工作流状态
            presentation: 演示文稿对象
        """
        # 用于跟踪已经使用过的幻灯片索引
        used_slide_indices = set()
        
        # 获取内容计划数量
        total_sections = len(state.content_plan)
        logger.info(f"开始并行生成 {total_sections} 张幻灯片")
        
        try:
            # 第一阶段：准备所有幻灯片（创建或找到合适的布局）
            slide_preparation_results = await self._prepare_all_slides_parallel(
                state, presentation, used_slide_indices
            )
            
            # 第二阶段：并行规划所有幻灯片的内容操作
            operations_results = await self._plan_all_slides_content_parallel(
                state, presentation, slide_preparation_results
            )
            
            # 第三阶段：串行执行所有幻灯片的操作（避免并发操作同一个PPTX文件）
            await self._execute_all_slides_operations(
                state, presentation, operations_results
            )
            
        except Exception as e:
            error_msg = f"并行生成幻灯片过程中出错: {str(e)}"
            logger.error(error_msg)
            logger.exception(e)
            state.record_failure(error_msg)
            raise RuntimeError(error_msg)
    
    async def _prepare_all_slides_parallel(self, state: AgentState, presentation: Any, 
                                        used_slide_indices: set) -> List[Dict[str, Any]]:
        """
        并行准备所有幻灯片
        
        Args:
            state: 工作流状态
            presentation: 演示文稿对象
            used_slide_indices: 已使用的幻灯片索引集合
            
        Returns:
            幻灯片准备结果列表
        """
        # 配置最大协程数
        max_workers = self.max_workers or len(state.content_plan)
        max_workers = min(max_workers, len(state.content_plan))
        
        logger.info(f"使用 {max_workers} 个协程并行准备幻灯片")
        
        # 创建准备任务
        preparation_tasks = []
        
        for section_index, current_section in enumerate(state.content_plan):
            # 创建幻灯片准备任务（只查找合适的布局，不实际创建幻灯片）
            task = self._prepare_single_slide_task(
                state, presentation, current_section, section_index, used_slide_indices
            )
            preparation_tasks.append(task)
        
        # 并行执行所有准备任务
        results = []
        for i in range(0, len(preparation_tasks), max_workers):
            batch = preparation_tasks[i:i+max_workers]
            logger.info(f"执行第 {i//max_workers + 1} 批幻灯片准备任务，共 {len(batch)} 个任务")
            batch_results = await asyncio.gather(*batch)
            results.extend(batch_results)
        
        logger.info(f"完成 {len(results)} 个幻灯片的准备")
        return results
    
    async def _prepare_single_slide_task(self, state: AgentState, presentation: Any, 
                                      current_section: Dict[str, Any], section_index: int,
                                      used_slide_indices: set) -> Dict[str, Any]:
        """
        准备单个幻灯片任务（查找合适的布局）
        
        Args:
            state: 工作流状态
            presentation: 演示文稿对象
            current_section: 当前处理的章节信息
            section_index: 章节索引
            used_slide_indices: 已使用的幻灯片索引集合
            
        Returns:
            幻灯片准备结果
        """
        logger.info(f"准备第 {section_index + 1} 张幻灯片: {current_section.get('slide_type', '未知类型')}")
        
        # 获取模板信息
        template_info = current_section.get("template", {})
        template_slide_index = template_info.get("slide_index")
        template_layout = template_info.get("layout", "")
        
        # 确定使用的幻灯片布局
        slide_layout_info = None
        layout_method = ""
        
        # 策略1：如果有指定的slide_index且未被使用过
        if template_slide_index is not None and template_slide_index not in used_slide_indices:
            slide_layout_info = {
                "slide_index": template_slide_index,
                "layout_name": "指定索引",
                "method": "template_index"
            }
            layout_method = "使用content_plan中指定的幻灯片索引"
            
        # 策略2：如果有指定的layout
        elif template_layout:
            # 这里不实际创建幻灯片，只返回layout信息
            slide_layout_info = {
                "layout_name": template_layout,
                "method": "template_layout"
            }
            layout_method = f"使用layout '{template_layout}'"
            
        # 策略3：查找匹配的布局
        else:
            # 查找布局信息，但不实际创建幻灯片
            layout_info = await self._find_suitable_layout(presentation)
            if layout_info:
                slide_layout_info = {
                    "layout_name": layout_info.get("layout_name", ""),
                    "reference_index": layout_info.get("index"),
                    "method": "find_layout"
                }
                layout_method = f"使用找到的布局 '{layout_info.get('layout_name', '')}'"
            else:
                # 如果找不到合适的布局，使用默认布局
                slide_layout_info = {
                    "layout_name": "默认布局",
                    "method": "default_layout"
                }
                layout_method = "使用默认布局"
        
        # 返回准备结果
        return {
            "section_index": section_index,
            "section_content": current_section,
            "slide_layout_info": slide_layout_info,
            "layout_method": layout_method
        }
    
    async def _find_suitable_layout(self, presentation: Any) -> Optional[Dict[str, Any]]:
        """
        查找合适的幻灯片布局
        
        Args:
            presentation: 演示文稿对象
            
        Returns:
            布局信息
        """
        try:
            # 获取PPT的JSON结构
            ppt_json = self.ppt_manager.get_presentation_json(presentation, include_details=False)
            slides_count = ppt_json.get("slide_count", 0)
            slide_layouts = []
            
            # 获取所有幻灯片的布局名称
            for i in range(slides_count):
                layout_json = self.ppt_manager.get_slide_layout_json(
                    presentation=presentation,
                    slide_index=i
                )
                layout_name = layout_json.get("layout_name", "")
                slide_layouts.append({"index": i, "layout_name": layout_name.lower()})
            
            # 查找"title_content"或"标题和内容"布局
            for slide_layout in slide_layouts:
                layout_name = slide_layout["layout_name"]
                if "title" in layout_name and "content" in layout_name:
                    return slide_layout
            
            # 如果找不到匹配的布局，使用默认布局（通常是索引为1的布局，即内容页）
            default_index = 1 if slides_count > 1 else 0
            return slide_layouts[default_index] if default_index < len(slide_layouts) else None
            
        except Exception as e:
            logger.error(f"查找合适布局时出错: {str(e)}")
            return None
    
    async def _plan_all_slides_content_parallel(self, state: AgentState, presentation: Any, 
                                             slide_preparation_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        并行规划所有幻灯片的内容操作
        
        Args:
            state: 工作流状态
            presentation: 演示文稿对象
            slide_preparation_results: 幻灯片准备结果列表
            
        Returns:
            幻灯片内容规划结果列表
        """
        # 配置最大协程数
        max_workers = self.max_workers or len(slide_preparation_results)
        max_workers = min(max_workers, len(slide_preparation_results))
        
        logger.info(f"使用 {max_workers} 个协程并行规划幻灯片内容")
        
        # 第一步：创建实际的幻灯片（串行操作，避免并发修改PPTX）
        # 创建幻灯片并收集实际的索引
        slides_info = await self._create_all_slides(state, presentation, slide_preparation_results)
        
        # 第二步：并行规划每个幻灯片的内容操作
        content_planning_tasks = []
        
        for slide_info in slides_info:
            slide_index = slide_info["slide_index"]
            current_section = slide_info["section_content"]
            section_index = slide_info["section_index"]
            
            # 为每个幻灯片创建内容规划任务
            task = self._plan_slide_content_task(
                presentation, slide_index, current_section, section_index
            )
            content_planning_tasks.append(task)
        
        # 并行执行所有内容规划任务
        results = []
        for i in range(0, len(content_planning_tasks), max_workers):
            batch = content_planning_tasks[i:i+max_workers]
            logger.info(f"执行第 {i//max_workers + 1} 批幻灯片内容规划任务，共 {len(batch)} 个任务")
            batch_results = await asyncio.gather(*batch)
            results.extend(batch_results)
        
        logger.info(f"完成 {len(results)} 个幻灯片的内容规划")
        
        # 合并slides_info和规划结果
        for i, result in enumerate(results):
            if i < len(slides_info):
                slides_info[i]["operations"] = result.get("operations", [])
        
        return slides_info
    
    async def _create_all_slides(self, state: AgentState, presentation: Any, 
                              slide_preparation_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        创建所有幻灯片（串行操作）
        
        Args:
            state: 工作流状态
            presentation: 演示文稿对象
            slide_preparation_results: 幻灯片准备结果列表
            
        Returns:
            创建的幻灯片信息列表
        """
        used_slide_indices = set()
        slides_info = []
        
        for result in slide_preparation_results:
            section_index = result["section_index"]
            current_section = result["section_content"]
            slide_layout_info = result["slide_layout_info"]
            layout_method = result["layout_method"]
            
            try:
                # 根据准备结果创建幻灯片
                slide_index = -1
                
                # 使用指定索引
                if slide_layout_info["method"] == "template_index":
                    slide_index = slide_layout_info["slide_index"]
                    logger.info(f"使用指定幻灯片索引: {slide_index}")
                
                # 使用指定布局创建幻灯片
                elif slide_layout_info["method"] == "template_layout":
                    layout_name = slide_layout_info["layout_name"]
                    logger.info(f"使用指定布局创建幻灯片: {layout_name}")
                    result = self.ppt_manager.create_slide_with_layout(
                        presentation=presentation,
                        layout_name=layout_name
                    )
                    if result.get("success", False):
                        slide_index = result.get("slide_index")
                        presentation = result.get("presentation", presentation)
                    else:
                        logger.warning(f"根据layout创建幻灯片失败: {result.get('message', '未知错误')}")
                
                # 使用找到的合适布局创建幻灯片
                elif slide_layout_info["method"] == "find_layout":
                    reference_index = slide_layout_info.get("reference_index")
                    logger.info(f"使用参考幻灯片 {reference_index} 的布局创建新幻灯片")
                    slide_index, presentation = await self._create_new_slide_with_same_layout(
                        presentation, reference_index, current_section
                    )
                
                # 使用默认布局创建幻灯片
                else:
                    logger.info("使用默认布局创建幻灯片")
                    # 默认使用第一张幻灯片的布局
                    default_index = 0
                    slide_index, presentation = await self._create_new_slide_with_same_layout(
                        presentation, default_index, current_section
                    )
                
                # 检查幻灯片是否创建成功
                if slide_index >= 0:
                    # 标记该幻灯片索引已使用
                    used_slide_indices.add(slide_index)
                    
                    # 添加slide_id到幻灯片备注中
                    await self._add_slide_id_to_notes(presentation, slide_index, current_section)
                    
                    # 记录幻灯片信息
                    slides_info.append({
                        "section_index": section_index,
                        "slide_index": slide_index,
                        "section_content": current_section,
                        "layout_method": layout_method
                    })
                    logger.info(f"成功创建第 {section_index + 1} 张幻灯片，索引: {slide_index}")
                else:
                    error_msg = f"创建第 {section_index + 1} 张幻灯片失败"
                    logger.error(error_msg)
                    state.record_failure(error_msg)
            
            except Exception as e:
                error_msg = f"创建第 {section_index + 1} 张幻灯片失败: {str(e)}"
                logger.error(error_msg)
                logger.exception(e)
                state.record_failure(error_msg)
        
        return slides_info
    
    async def _plan_slide_content_task(self, presentation: Any, slide_index: int,
                                    current_section: Dict[str, Any], section_index: int) -> Dict[str, Any]:
        """
        规划单个幻灯片的内容操作
        
        Args:
            presentation: 演示文稿对象
            slide_index: 幻灯片索引
            current_section: 当前处理的章节信息
            section_index: 章节索引
            
        Returns:
            内容规划结果
        """
        logger.info(f"规划第 {section_index + 1} 张幻灯片的内容，索引: {slide_index}")
        
        try:
            # 获取幻灯片中的元素
            slide_elements = self.ppt_manager.get_slide_json(
                presentation=presentation,
                slide_index=slide_index
            )
            
            # 规划幻灯片操作
            operations = await self._plan_slide_operations(slide_elements, current_section)
            
            return {
                "slide_index": slide_index,
                "section_index": section_index,
                "operations": operations
            }
            
        except Exception as e:
            logger.error(f"规划第 {section_index + 1} 张幻灯片内容时出错: {str(e)}")
            return {
                "slide_index": slide_index,
                "section_index": section_index,
                "operations": [],
                "error": str(e)
            }
    
    async def _execute_all_slides_operations(self, state: AgentState, presentation: Any, 
                                          slides_info: List[Dict[str, Any]]) -> None:
        """
        串行执行所有幻灯片的操作
        
        Args:
            state: 工作流状态
            presentation: 演示文稿对象
            slides_info: 幻灯片信息列表
        """
        logger.info(f"开始串行执行 {len(slides_info)} 张幻灯片的操作")
        
        for slide_info in slides_info:
            section_index = slide_info["section_index"]
            slide_index = slide_info["slide_index"]
            current_section = slide_info["section_content"]
            operations = slide_info.get("operations", [])
            
            try:
                # 执行操作
                if operations:
                    logger.info(f"执行第 {section_index + 1} 张幻灯片的 {len(operations)} 个操作，索引: {slide_index}")
                    success = await self._execute_operations(presentation, slide_index, operations)
                    if not success:
                        logger.warning(f"执行第 {section_index + 1} 张幻灯片操作时出现问题")
                else:
                    logger.warning(f"第 {section_index + 1} 张幻灯片没有需要执行的操作")
                
                # 记录生成的幻灯片信息
                self._record_generated_slide(state, section_index, slide_index, current_section, operations)
                
            except Exception as e:
                error_msg = f"执行第 {section_index + 1} 张幻灯片操作时出错: {str(e)}"
                logger.error(error_msg)
                logger.exception(e)
                state.record_failure(error_msg)
    