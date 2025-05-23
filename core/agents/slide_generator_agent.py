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
import os
import re
from typing import Dict, Any, List, Optional
import enum
from pathlib import Path
import uuid
import tempfile
import datetime
from config.settings import settings

from core.agents.base_agent import BaseAgent
from core.engine.state import AgentState
from core.llm.model_manager import ModelManager
from config.prompts.slide_generator_prompts import (
    LLM_PPT_ELEMENT_MATCHING_PROMPT, 
    SLIDE_SELF_VALIDATION_PROMPT
)

# 导入PPT管理器
try:
    from interfaces.ppt_api import PPTManager
except ImportError:
    logger = logging.getLogger(__name__)
    logger.error("无法导入PPTManager，请确保ppt_manager库已正确安装")
    PPTManager = None

logger = logging.getLogger(__name__)

class EnumEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, enum.Enum):
            return obj.value if hasattr(obj, 'value') else str(obj)
        return super().default(obj)

class SlideGeneratorAgent(BaseAgent):
    """幻灯片生成Agent，负责基于PPT模板生成具体的幻灯片内容，并进行自验证"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化幻灯片生成Agent
        
        Args:
            config: Agent配置
        """
        super().__init__(config)
        # 初始化模型管理器
        self.model_manager = ModelManager()
        
        # 从配置获取模型类型和名称
        self.model_type = config.get("model_type", "text")
        
        # 初始化模型属性
        model_config = self.model_manager.get_model_config(self.model_type)
        self.llm_model = model_config.get("model")
        self.temperature = model_config.get("temperature")
        self.max_tokens = model_config.get("max_tokens")
        
        # 初始化PPTManager
        try:
            from interfaces.ppt_api import PPTManager
            self.ppt_manager = PPTManager()
            logger.info("成功初始化PPT管理器")
        except ImportError as e:
            logger.error(f"无法导入PPTManager: {str(e)}")
            self.ppt_manager = None
        
        logger.info(f"初始化SlideGeneratorAgent，使用模型: {self.llm_model}")
    
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
            
            # 检查状态中是否有内容计划
            if not hasattr(state, 'content_plan') or not state.content_plan:
                error_msg = "无法生成幻灯片：找不到内容计划"
                logger.error(error_msg)
                state.record_failure(error_msg)
                return state
                
            # 初始化存储生成幻灯片的列表
            state.generated_slides = []
            
            # 循环处理所有章节内容
            total_sections = len(state.content_plan)
            logger.info(f"开始生成 {total_sections} 张幻灯片")
            
            for section_index, current_section in enumerate(state.content_plan):
                logger.info(f"生成第 {section_index + 1}/{total_sections} 张幻灯片: {current_section.get('slide_type', '未知类型')}")
                
                try:
                    # 更新当前章节索引
                    state.current_section_index = section_index
                    
                    # 生成幻灯片
                    slide_index, presentation = await self._find_template_slide(state, presentation, current_section)
                    
                    # 执行幻灯片内容填充操作
                    operations = await self._plan_and_execute_content_operations(
                        presentation, slide_index, current_section
                    )
                    
                    # 记录生成的幻灯片信息
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
                    
                except Exception as e:
                    error_msg = f"生成第 {section_index + 1} 张幻灯片失败: {str(e)}"
                    logger.error(error_msg)
                    logger.exception(e)
                    state.record_failure(error_msg)
                    # 继续生成其他幻灯片，不中断整个过程
            
            # 更新状态
            state.presentation = presentation
            state.has_more_content = False  # 标记所有内容已处理完毕
            
            # 记录完成信息
            logger.info(f"已完成所有 {len(state.generated_slides)}/{total_sections} 张幻灯片的生成")
            
            return state
            
        except Exception as e:
            error_msg = f"幻灯片生成流程失败: {str(e)}"
            logger.error(error_msg)
            logger.exception(e)
            state.record_failure(error_msg)
            raise RuntimeError(error_msg)
    
    def _ensure_default_fields(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        确保结果字典包含所需的默认字段
        
        Args:
            result: 结果字典
            
        Returns:
            包含默认字段的结果字典
        """
        result.setdefault("has_issues", False)
        result.setdefault("issues", [])
        result.setdefault("suggestions", [])
        return result
    
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

    # def _get_template_slide_id(self, template_info: Dict[str, Any], ppt_json: Dict[str, Any]) -> str:
    #     """
    #     从模板信息中获取幻灯片ID
        
    #     Args:
    #         template_info: 模板信息
    #         ppt_json: PPT的JSON结构
            
    #     Returns:
    #         幻灯片ID
    #     """
    #     if "slideIndex" in template_info:
    #         slide_index = template_info["slideIndex"]
    #         slides = ppt_json.get("slides", [])
            
    #         # 根据slideIndex(实际是real_index)查找对应的slide_id
    #         for slide in slides:
    #             # 检查slide是否包含real_index信息
    #             if "real_index" in slide and slide["real_index"] == slide_index:
    #                 return slide.get("real_index")
            
    #         # 如果找不到匹配的real_index或index，直接抛出异常
    #         raise ValueError(f"无法找到real_index或index为{slide_index}的幻灯片，请检查模板配置")
        
    #     # 如果template_info中没有slide_id和slideIndex，直接抛出异常
    #     raise ValueError("template_info中缺少slide_id或slideIndex，无法确定要使用的模板幻灯片")
    
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
        
        # 调用LLM获取匹配结果
        response = await self.model_manager.generate_text(
            model=self.llm_model,
            prompt=prompt,
            temperature=self.temperature,  # 使用较低的温度以获得更确定的结果
            max_tokens=self.max_tokens
        )
        
        # 解析LLM响应
        return self._parse_llm_response(response)

    def _validate_operation(self, operation: Dict[str, Any]) -> bool:
        """
        验证操作有效性
        
        Args:
            operation: 操作指令
            
        Returns:
            操作是否有效
        """
        element_id = operation.get("element_id")
        if not element_id:
            logger.warning(f"跳过缺少element_id的操作: {operation}")
            return False
        return True

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
    
    def _parse_llm_response(self, response: str) -> List[Dict[str, Any]]:
        """
        解析LLM返回的响应
        
        Args:
            response: LLM响应文本
            
        Returns:
            解析后的操作指令列表
        """
        try:
            # 提取JSON部分
            json_text = response
            if "```json" in response:
                # 提取JSON代码块
                pattern = r"```(?:json)?\s*([\s\S]*?)```"
                matches = re.findall(pattern, response)
                if matches:
                    json_text = matches[0]
            
            # 解析JSON
            result = json.loads(json_text)
            
            # 提取操作列表
            if isinstance(result, dict):
                # 兼容旧格式: {"matches": [...]}
                if "matches" in result:
                    return result["matches"]
                # 新格式: {"operations": [...]}
                if "operations" in result:
                    return result["operations"]
            
            # 如果直接是列表，尝试直接使用
            if isinstance(result, list):
                return result
                
            logger.warning(f"LLM响应格式不符合预期: {json_text[:100]}...")
            return []
            
        except Exception as e:
            logger.exception(f"解析LLM响应时出错: {str(e)}")
            return []
    
    def _extract_json_from_response(self, response: str) -> str:
        """
        从响应中提取JSON文本
        
        Args:
            response: 响应文本
            
        Returns:
            JSON文本
        """
        # 尝试直接解析JSON响应
        json_text = response
        
        # 如果响应包含JSON代码块，提取它
        if "```json" in response:
            pattern = r"```(?:json)?\s*([\s\S]*?)```"
            matches = re.findall(pattern, response)
            if matches:
                json_text = matches[0]
                
        return json_text
    
    def _parse_vision_response(self, response: str) -> Dict[str, Any]:
        """
        解析视觉模型响应
        
        Args:
            response: 视觉模型响应文本
            
        Returns:
            解析后的结果字典
        """
        try:
            # 提取JSON部分
            json_text = self._extract_json_from_response(response)
            
            # 解析JSON
            result = json.loads(json_text)
            
            # 确保结果有必要的字段
            if not isinstance(result, dict):
                raise ValueError("响应不是有效的JSON对象")
            
            # 添加默认字段
            return self._ensure_default_fields(result)
            
        except Exception as e:
            logger.error(f"解析视觉模型响应时出错: {str(e)}")
            return {
                "has_issues": True,
                "issues": ["解析响应失败"],
                "suggestions": ["尝试重新生成"]
            }
    
    async def _generate_slide(self, state: AgentState, presentation: Any) -> None:
        """
        生成幻灯片内容
        
        Args:
            state: 当前状态
            presentation: 演示文稿对象
        """
        # 获取当前章节内容
        current_index = state.current_section_index
        current_section = state.content_plan[current_index]
        logger.info(f"处理章节 {current_index + 1}/{len(state.content_plan)}: {current_section.get('slide_type', '未知类型')}")
        
        # 第一步：找到目标幻灯片
        slide_index, presentation = await self._find_template_slide(state, presentation, current_section)
        
        # 第二步：规划并执行幻灯片内容填充操作
        operations = await self._plan_and_execute_content_operations(
            presentation, slide_index, current_section
        )
        
        # 更新状态
        state.presentation = presentation
        
        # 初始化generated_slides如果不存在
        if not hasattr(state, 'generated_slides') or state.generated_slides is None:
            state.generated_slides = []
        
        # 更新当前幻灯片信息，供验证使用
        state.current_slide = {
            "section_index": current_index,
            "slide_index": slide_index,
            "slide_type": current_section.get("slide_type", ""),
            "template_info": current_section.get("template", {}),
            "section_content": current_section,
            "operations": operations,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # 记录详细日志
        logger.info(f"已生成幻灯片，索引: {slide_index}, 类型: {current_section.get('slide_type', '未知类型')}")
    
    async def _add_slide_id_to_notes(self, presentation: Any, slide_index: int, current_section: Dict[str, Any]) -> None:
        """
        将content_planning中备注的slide_id信息写入到对应slide的备注信息中
        
        Args:
            presentation: 演示文稿对象
            slide_index: 幻灯片索引
            current_section: 当前章节内容
        """
        try:
            # 从当前章节获取slide_id
            slide_id = current_section.get("slide_id")
            
            if not slide_id:
                logger.warning(f"幻灯片索引 {slide_index} 没有关联的slide_id")
                return
            
            logger.info(f"将slide_id: {slide_id} 添加到幻灯片 {slide_index} 的备注中")
            
            # 获取现有备注
            notes_result = self.ppt_manager.get_slide_notes(
                presentation=presentation,
                slide_index=slide_index
            )
            
            existing_notes = notes_result.get("notes", "")
            
            # 构建新备注内容
            new_notes = f"slide_id: {slide_id}"
            if existing_notes:
                new_notes = f"{existing_notes}\n{new_notes}"
            
            # 更新备注
            self.ppt_manager.update_slide_notes(
                presentation=presentation,
                slide_index=slide_index,
                notes=new_notes
            )
            
            logger.info(f"成功将slide_id添加到幻灯片 {slide_index} 的备注中")
            
        except Exception as e:
            logger.error(f"添加slide_id到备注时出错: {str(e)}")
            # 记录错误但不中断主要流程

    async def _plan_and_execute_content_operations(
        self, presentation: Any, slide_index: int, current_section: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        规划并执行幻灯片内容填充操作
        
        Args:
            presentation: 演示文稿对象
            slide_id: 幻灯片ID
            current_section: 当前章节内容
            
        Returns:
            执行的操作列表
        """
        # 获取新幻灯片的详细信息
        slide_result = self.ppt_manager.get_slide_json(
            presentation=presentation,
            slide_index=slide_index            
        )
        
        # 使用LLM匹配内容到幻灯片元素
        logger.info("调用LLM进行内容-元素智能匹配及操作规划")
        operations = await self._plan_slide_operations(
            slide_elements=slide_result,
            current_section=current_section
        )
        
        # 执行LLM规划的操作
        logger.info(f"执行幻灯片操作，共 {len(operations)} 项")
        await self._execute_operations(presentation, slide_index, operations)
        
        # 将slide_id写入幻灯片备注
        await self._add_slide_id_to_notes(presentation, slide_index, current_section)
        
        return operations
    
    async def _plan_slide_operations(self, slide_elements: List[Dict[str, Any]], current_section: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        使用LLM规划幻灯片操作，包括内容匹配和特殊操作
        
        Args:
            slide_elements: 幻灯片元素列表
            current_section: 当前处理的章节信息
            
        Returns:
            操作指令列表
        """
        try:
            # 构建提示词上下文
            context = self._build_operation_context(slide_elements, current_section)
            
            # 获取LLM响应
            operations = await self._get_operations_from_llm(context)
            
            if operations:
                logger.info(f"LLM成功返回 {len(operations)} 个操作指令")
                return operations
            else:
                logger.warning("无法从LLM响应中解析出有效的操作指令，将使用默认匹配")
                
        except Exception as e:
            logger.exception(f"规划幻灯片操作时出错: {str(e)}")
    
    async def _execute_operations(self, presentation: Any, slide_index: int, operations: List[Dict[str, Any]]) -> bool:
        """
        执行幻灯片操作指令
        
        Args:
            presentation: PPT演示文稿对象
            slide_index: 幻灯片索引
            operations: 操作指令列表
            
        Returns:
            是否成功执行所有操作
        """
        if not operations:
            logger.warning("没有操作指令可执行")
            return False
        
        success_count = 0
        total_count = len(operations)
        
        for operation in operations:
            if not self._validate_operation(operation):
                continue
                
            try:
                # 执行操作
                result = await self._execute_single_operation(presentation, slide_index, operation)
                
                if result.get("success"):
                    success_count += 1
                    logger.info(f"成功执行操作 {operation.get('operation')} 于元素 {operation.get('element_id')}")
                else:
                    logger.warning(f"执行操作 {operation.get('operation')} 失败: {result.get('message')}")
            
            except Exception as e:
                logger.warning(f"执行操作时出错: {str(e)}")
        
        # 计算成功率
        success_rate = success_count / total_count if total_count > 0 else 0
        logger.info(f"操作执行完成，成功率: {success_rate:.2%} ({success_count}/{total_count})")
        
        # 如果有任何操作成功应用，就认为整体成功
        return success_count > 0
    
    async def _execute_single_operation(self, presentation: Any, slide_index: int, operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行单个操作
        
        Args:
            presentation: PPT演示文稿对象
            slide_index: 幻灯片索引
            operation: 操作指令
            
        Returns:
            操作结果
        """
        element_id = operation.get("element_id")
        operation_type = operation.get("operation", "update_element_content")
        content = operation.get("content")
        
        # 根据操作类型执行不同的操作
        if operation_type == "update_element_content":
            # 文本替换操作
            return self.ppt_manager.update_element_content(
                presentation=presentation,
                slide_index=slide_index,
                element_id=element_id,
                new_content=str(content).strip()
            )
        elif operation_type == "adjust_text_font_size":
            # 调整字体大小
            return self.ppt_manager.adjust_text_font_size(
                presentation=presentation,
                slide_index=slide_index,
                element_id=element_id,
                font_size=int(content)
            )
        elif operation_type == "replace_image":
            # 替换图片
            return self.ppt_manager.replace_image(
                presentation=presentation,
                slide_index=slide_index,
                element_id=element_id,
                image_path=content
            )
        elif operation_type == "adjust_element_position":
            # 调整元素位置
            return self.ppt_manager.adjust_element_position(
                presentation=presentation,
                slide_index=slide_index,
                element_id=element_id,
                left=content.get("left"),
                top=content.get("top"),
                width=content.get("width"),
                height=content.get("height")
            )
        elif operation_type == "delete_element":
            # 删除元素
            return self.ppt_manager.delete_element(
                presentation=presentation,
                slide_index=slide_index,
                element_id=element_id
            )
        else:
            logger.warning(f"未知的操作类型: {operation_type}")
            return {"success": False, "message": f"未知的操作类型: {operation_type}"}
        
    async def _render_slide_to_image(self, state: AgentState, presentation: Any, slide_index: int) -> Optional[str]:
        """
        渲染幻灯片为图片
        
        Args:
            state: 当前状态
            presentation: 演示文稿对象
            slide_index: 幻灯片索引
            
        Returns:
            图片路径，失败返回None
        """
        # 创建临时目录用于存储渲染的幻灯片图像和临时PPTX文件
        session_dir = Path(f"workspace/sessions/{state.session_id}/slide_images")
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建唯一的临时文件名
        temp_pptx_filename = f"temp_{uuid.uuid4().hex}.pptx"
        temp_pptx_path = session_dir / temp_pptx_filename
        
        try:
            # 临时保存修改后的presentation对象为PPTX文件
            logger.info(f"临时保存修改后的演示文稿到: {temp_pptx_path}")
            self.ppt_manager.save_presentation(presentation, str(temp_pptx_path))
            
            # 使用临时保存的PPTX文件进行渲染
            logger.info(f"使用临时PPTX文件渲染幻灯片，索引: {slide_index}")
            image_paths = self.ppt_manager.render_pptx_file(
                pptx_path=str(temp_pptx_path),
                output_dir=str(session_dir),
                slide_index=slide_index
            )
            
            logger.info(f"渲染结果: {image_paths}")
            
            if not image_paths or len(image_paths) == 0:
                logger.error("渲染幻灯片图像失败")
                return None
                
            return image_paths[0]
            
        finally:
            # 无论渲染成功与否，都删除临时PPTX文件
            if temp_pptx_path.exists():
                logger.info(f"删除临时PPTX文件: {temp_pptx_path}")
                temp_pptx_path.unlink()
    
    async def _create_new_slide_with_same_layout(self, presentation: Any, slide_index: int, current_section: Optional[Dict[str, Any]] = None) -> tuple:
        """
        根据指定幻灯片的布局创建一个新的幻灯片
        
        Args:
            presentation: 演示文稿对象
            slide_index: 参考幻灯片索引
            current_section: 当前章节内容，用于提取slide_id
            
        Returns:
            tuple: (新幻灯片ID, 更新后的演示文稿对象)
        """
        # 获取当前幻灯片的布局信息
        layout_json = self.ppt_manager.get_slide_layout_json(
            presentation=presentation,
            slide_index=slide_index
        )
        
        # 从layout_json中获取layout_name
        layout_name = layout_json.get("layout_name", "Title and Content")
        logger.info(f"获取到幻灯片 {slide_index} 的布局名称: {layout_name}")
        
        # 创建新幻灯片
        result = self.ppt_manager.create_slide_with_layout(
            presentation=presentation,
            layout_name=layout_name
        )
        
        if result.get("success", False):
            # 获取新创建的幻灯片ID
            new_slide_index = result.get("slide_index")
            logger.info(f"成功创建新幻灯片，ID: {new_slide_index}")
            # 返回可能更新的presentation对象
            presentation = result.get("presentation", presentation)
            
            # 如果提供了current_section，则将slide_id写入新幻灯片的备注
            if current_section and "slide_id" in current_section:
                await self._add_slide_id_to_notes(presentation, new_slide_index, current_section)
            
            return new_slide_index, presentation
        else:
            # 创建失败，仍使用原幻灯片
            logger.warning(f"创建新幻灯片失败: {result.get('message')}，使用原幻灯片")
            return slide_index, presentation

    async def _find_template_slide(self, state: AgentState, presentation: Any, current_section: Dict[str, Any]) -> tuple:
        """
        找到模板幻灯片
        
        Args:
            state: 当前状态
            presentation: 演示文稿对象
            current_section: 当前章节内容
            
        Returns:
            tuple: (幻灯片ID, 更新后的演示文稿对象)
        """
        # 获取PPT的JSON结构并找到模板幻灯片ID
        ppt_json = self.ppt_manager.get_presentation_json(presentation, include_details=False)
        template_info = current_section.get("template", {})
        slide_index = template_info.get("slide_index")
        
        # 从state获取已编辑幻灯片ID记录
        if not hasattr(state, "edited_slides") or state.edited_slides is None:
            state.edited_slides = set()
        
        # 判断幻灯片是否已编辑过
        if slide_index in state.edited_slides:
            logger.info(f"幻灯片 {slide_index} 已被编辑过，创建新幻灯片")
            return await self._create_new_slide_with_same_layout(presentation, slide_index, current_section)
        else:
            # 将当前幻灯片ID添加到已编辑列表
            state.edited_slides.add(slide_index)
            logger.info(f"使用现有幻灯片，ID: {slide_index}")
            
            return slide_index, presentation
    