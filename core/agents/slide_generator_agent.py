#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
幻灯片生成Agent模块

负责根据内容规划生成具体的幻灯片内容，包括标题、文本、图片等元素。
使用PPTManager在已有PPTX模板上进行操作，不直接生成幻灯片内容。
"""

import logging
import json
import os
import re
from typing import Dict, Any, List, Optional
import enum

from core.agents.base_agent import BaseAgent
from core.engine.state import AgentState
from core.llm.model_manager import ModelManager
from config.prompts.slide_generator_prompts import LLM_PPT_ELEMENT_MATCHING_PROMPT, SLIDE_FIX_OPERATIONS_PROMPT

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
    """幻灯片生成Agent，负责基于PPT模板生成具体的幻灯片内容"""
    
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
        self.temperature = model_config.get("temperature", 0.7)
        self.max_tokens = model_config.get("max_tokens", 4000)
        
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
        执行幻灯片生成逻辑

        Args:
            state: 工作流引擎状态

        Returns:
            更新后的工作流引擎状态
        """
        logger.info("开始生成幻灯片")
        
        try:
            # 获取PPT模板路径和内容计划
            template_path = getattr(state, 'template_path', None) or getattr(state, 'ppt_template_path', None)
            
            # 获取或加载presentation
            presentation = getattr(state, 'presentation', None)
            if not presentation:
                logger.info(f"加载PPT模板: {template_path}")
                presentation = self.ppt_manager.load_presentation(template_path)
            
            # 处理验证失败的情况，尝试修复上一张幻灯片
            validation_result = getattr(state, 'validation_result', True)
            validation_issues = getattr(state, 'validation_issues', [])
            if not validation_result and hasattr(state, 'current_slide') and validation_issues and len(validation_issues) > 0:
                logger.info(f"发现验证问题，准备修复当前幻灯片: {validation_issues}")
                await self._fix_validation_issues(state, presentation)
                return state
            
            # 获取当前章节内容
            current_index = state.current_section_index
            current_section = state.content_plan[current_index]
            logger.info(f"处理章节 {current_index + 1}/{len(state.content_plan)}: {current_section.get('slide_type', '未知类型')}")
            
            # 获取PPT的JSON结构并找到模板幻灯片ID
            ppt_json = self.ppt_manager.get_presentation_json(presentation, include_details=False)
            template_info = current_section.get("template", {})
            slide_id = self._get_template_slide_id(template_info, ppt_json)
            
            # 复制模板幻灯片
            logger.info(f"复制模板幻灯片ID: {slide_id}")
            duplicate_result = self.ppt_manager.duplicate_slide_by_id(
                presentation=presentation,
                slide_id=slide_id
            )
            
            # 获取新幻灯片信息并更新presentation
            new_slide_id = duplicate_result["slide_id"]
            presentation = duplicate_result["presentation"]
            
            # 获取新幻灯片的详细信息
            slide_result = self.ppt_manager.get_slide_json_by_id(
                presentation=presentation,
                slide_id=new_slide_id            
            )
            
            # 使用LLM匹配内容到幻灯片元素
            logger.info("调用LLM进行内容-元素智能匹配及操作规划")
            operations = await self._plan_slide_operations(
                slide_elements=slide_result,
                current_section=current_section
            )
            
            # 执行LLM规划的操作
            logger.info(f"执行幻灯片操作，共 {len(operations)} 项")
            await self._execute_operations(presentation, new_slide_id, operations)
            
            # 更新状态
            state.presentation = presentation
            
            # 初始化generated_slides如果不存在
            if not hasattr(state, 'generated_slides') or state.generated_slides is None:
                state.generated_slides = []
            
            # 更新当前幻灯片信息，供验证使用
            slide_info = {
                "section_index": current_index,
                "slide_id": new_slide_id,
                "operations": operations
            }
            
            # 设置当前幻灯片信息
            state.current_slide = slide_info
            
            # 重置验证状态
            state.validation_result = None
            if hasattr(state, 'validation_issues'):
                delattr(state, 'validation_issues')
            if hasattr(state, 'validation_suggestions'):
                delattr(state, 'validation_suggestions')
            
            return state
            
        except Exception as e:
            error_msg = f"幻灯片生成失败: {str(e)}"
            logger.error(error_msg)
            logger.exception(e)
            raise RuntimeError(error_msg)
    
    def _get_template_slide_id(self, template_info: Dict[str, Any], ppt_json: Dict[str, Any]) -> str:
        """
        从模板信息中获取幻灯片ID
        
        Args:
            template_info: 模板信息
            ppt_json: PPT的JSON结构
            
        Returns:
            幻灯片ID
        """
        if "slideIndex" in template_info:
            slide_index = template_info["slideIndex"]
            slides = ppt_json.get("slides", [])
            
            # 根据slideIndex(实际是real_index)查找对应的slide_id
            for slide in slides:
                # 检查slide是否包含real_index信息
                if "real_index" in slide and slide["real_index"] == slide_index:
                    return slide.get("slide_id")
            
            # 如果找不到匹配的real_index或index，直接抛出异常
            raise ValueError(f"无法找到real_index或index为{slide_index}的幻灯片，请检查模板配置")
        
        # 如果template_info中没有slide_id和slideIndex，直接抛出异常
        raise ValueError("template_info中缺少slide_id或slideIndex，无法确定要使用的模板幻灯片")
    
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
            # 构建提示词上下文，直接提供幻灯片元素和章节内容
            context = {
                "slide_elements_json": json.dumps(slide_elements, ensure_ascii=False, indent=2, cls=EnumEncoder),
                "content_json": json.dumps(current_section, ensure_ascii=False, indent=2, cls=EnumEncoder)
            }
            
            # 渲染提示词
            prompt = self.model_manager.render_template(LLM_PPT_ELEMENT_MATCHING_PROMPT, context)
            
            # 调用LLM获取匹配结果
            response = await self.model_manager.generate_text(
                model=self.llm_model,
                prompt=prompt,
                temperature=0.2,  # 使用较低的温度以获得更确定的结果
                max_tokens=self.max_tokens
            )
            
            # 解析LLM响应
            operations = self._parse_llm_response(response)
            
            if operations:
                logger.info(f"LLM成功返回 {len(operations)} 个操作指令")
                return operations
            else:
                logger.warning("无法从LLM响应中解析出有效的操作指令，将使用默认匹配")
                # 当无法获取有效操作时返回基本文本替换操作
                return self._generate_default_operations(slide_elements, current_section)
                
        except Exception as e:
            logger.exception(f"规划幻灯片操作时出错: {str(e)}")
            # 返回基本文本替换操作作为备选
            return self._generate_default_operations(slide_elements, current_section)
    
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
    
    def _generate_default_operations(self, slide_elements: List[Dict[str, Any]], current_section: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        生成默认的操作指令，用于LLM响应解析失败时
        
        Args:
            slide_elements: 幻灯片元素列表
            current_section: 当前处理的章节信息
            
        Returns:
            默认操作指令列表
        """
        operations = []
        
        # 尝试找到标题元素和内容元素
        title_element = None
        content_elements = []
        
        for element in slide_elements:
            element_name = element.get("metadata", {}).get("shape_name", "").lower()
            element_type = element.get("element_type", "").lower()
            
            # 查找标题元素
            if element_type == "title" or "title" in element_name:
                title_element = element
            # 查找内容元素
            elif element_type == "content" or "content" in element_name or "text" in element_type:
                content_elements.append(element)
        
        # 添加标题替换操作
        if title_element and "title" in current_section:
            operations.append({
                "element_id": title_element.get("element_id"),
                "operation": "replace_text",
                "content": current_section.get("title", "未命名幻灯片")
            })
        
        # 添加内容替换操作
        if content_elements and "content" in current_section:
            # 获取内容文本
            content_text = current_section.get("content", "")
            if isinstance(content_text, list):
                # 如果是列表，转换为项目符号
                formatted_content = ""
                for item in content_text:
                    formatted_content += f"• {item}\n"
                content_text = formatted_content.strip()
            
            # 添加内容替换操作
            operations.append({
                "element_id": content_elements[0].get("element_id"),
                "operation": "replace_text",
                "content": content_text
            })
        
        return operations
    
    async def _execute_operations(self, presentation: Any, slide_id: str, operations: List[Dict[str, Any]]) -> bool:
        """
        执行幻灯片操作指令
        
        Args:
            presentation: PPT演示文稿对象
            slide_id: 幻灯片ID
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
            element_id = operation.get("element_id")
            operation_type = operation.get("operation", "replace_text")
            content = operation.get("content")
            
            if not element_id:
                logger.warning(f"跳过缺少element_id的操作: {operation}")
                continue
            
            try:
                # 根据操作类型执行不同的操作
                if operation_type == "replace_text":
                    # 文本替换操作
                    result = await self._replace_text(presentation, slide_id, element_id, content)
                elif operation_type == "adjust_font_size":
                    # 调整字体大小
                    result = self.ppt_manager.adjust_text_font_size(
                        presentation=presentation,
                        slide_id=slide_id,
                        element_id=element_id,
                        font_size=int(content)
                    )
                elif operation_type == "replace_image":
                    # 替换图片
                    result = self.ppt_manager.replace_image_by_element_id(
                        presentation=presentation,
                        slide_id=slide_id,
                        element_id=element_id,
                        image_path=content
                    )
                elif operation_type == "add_image_caption":
                    # 添加图片说明
                    result = self.ppt_manager.add_image_caption(
                        presentation=presentation,
                        slide_id=slide_id,
                        element_id=element_id,
                        caption=content
                    )
                else:
                    logger.warning(f"未知的操作类型: {operation_type}")
                    continue
                
                if result.get("success"):
                    success_count += 1
                    logger.info(f"成功执行操作 {operation_type} 于元素 {element_id}")
                else:
                    logger.warning(f"执行操作 {operation_type} 失败: {result.get('message')}")
            
            except Exception as e:
                logger.warning(f"执行操作时出错: {str(e)}")
        
        # 计算成功率
        success_rate = success_count / total_count if total_count > 0 else 0
        logger.info(f"操作执行完成，成功率: {success_rate:.2%} ({success_count}/{total_count})")
        
        # 如果有任何操作成功应用，就认为整体成功
        return success_count > 0
    
    async def _replace_text(self, presentation: Any, slide_id: str, element_id: str, content: Any) -> Dict[str, Any]:
        """
        替换文本内容
        
        Args:
            presentation: PPT演示文稿对象
            slide_id: 幻灯片ID
            element_id: 元素ID
            content: 文本内容，可以是字符串或列表
            
        Returns:
            操作结果
        """
        # 处理不同类型的内容
        if isinstance(content, list):
            # 列表内容（如项目符号）
            formatted_content = ""
            for item in content:
                if item and item.strip():
                    formatted_content += f"• {item.strip()}\n"
            
            if formatted_content:
                return self.ppt_manager.edit_text_element_by_id(
                    presentation=presentation,
                    slide_id=slide_id,
                    element_id=element_id,
                    new_text=formatted_content.strip()
                )
        else:
            # 字符串内容
            return self.ppt_manager.edit_text_element_by_id(
                presentation=presentation,
                slide_id=slide_id,
                element_id=element_id,
                new_text=str(content).strip()
            )
        
        return {"success": False, "message": "无有效内容可替换"}
    
    async def _fix_validation_issues(self, state: AgentState, presentation: Any) -> None:
        """
        修复验证问题
        
        Args:
            state: 当前状态
            presentation: 演示文稿对象
        """
        if not hasattr(state, 'validation_issues') or not state.validation_issues or len(state.validation_issues) == 0:
            logger.warning("没有验证问题需要修复")
            return
        
        # 获取当前幻灯片信息
        current_slide = state.current_slide
        slide_id = current_slide.get("slide_id")
        operations = current_slide.get("operations", [])
        
        # 获取验证问题和建议
        issues = state.validation_issues
        suggestions = getattr(state, 'validation_suggestions', [])
        
        # 记录修复信息
        logger.info(f"开始修复验证问题: {issues}")
        logger.info(f"修复建议: {suggestions}")
        
        # 根据问题类型进行修复
        new_operations = await self._generate_fix_operations(
            presentation=presentation,
            slide_id=slide_id,
            original_operations=operations,
            issues=issues,
            suggestions=suggestions
        )
        
        # 执行修复操作
        if new_operations:
            logger.info(f"执行修复操作，共 {len(new_operations)} 项")
            success = await self._execute_operations(presentation, slide_id, new_operations)
            
            if success:
                # 更新当前幻灯片的操作记录
                state.current_slide["operations"] = state.current_slide.get("operations", []) + new_operations
                
                # 不再进行图像渲染，由验证Agent负责
        else:
            logger.warning("未能生成修复操作")
        
        # 无论修复是否成功，都清除验证问题，避免循环修复
        if hasattr(state, 'validation_issues'):
            delattr(state, 'validation_issues')
        if hasattr(state, 'validation_suggestions'):
            delattr(state, 'validation_suggestions')
        
        # 设置验证结果为通过，避免重复修复
        state.validation_result = True
        logger.info("验证问题修复完成，清除验证状态")
    
    async def _generate_fix_operations(self, presentation: Any, slide_id: str, 
                                      original_operations: List[Dict[str, Any]], 
                                      issues: List[str], suggestions: List[str]) -> List[Dict[str, Any]]:
        """
        根据验证问题生成修复操作
        
        Args:
            presentation: 演示文稿对象
            slide_id: 幻灯片ID
            original_operations: 原操作列表
            issues: 验证问题列表
            suggestions: 修复建议列表
            
        Returns:
            修复操作列表
        """
        # 获取幻灯片信息
        slide_json = self.ppt_manager.get_slide_json_by_id(presentation, slide_id)
        
        # 构建修复提示词
        context = {
            "slide_json": json.dumps(slide_json, ensure_ascii=False, indent=2, cls=EnumEncoder),
            "original_operations": json.dumps(original_operations, ensure_ascii=False, indent=2),
            "issues": json.dumps(issues, ensure_ascii=False, indent=2),
            "suggestions": json.dumps(suggestions, ensure_ascii=False, indent=2)
        }
        
        # 渲染提示词
        prompt = self.model_manager.render_template(SLIDE_FIX_OPERATIONS_PROMPT, context)
        
        # 调用LLM获取修复操作
        response = await self.model_manager.generate_text(
            model=self.llm_model,
            prompt=prompt,
            temperature=0.3,
            max_tokens=self.max_tokens
        )
        
        # 解析LLM响应
        return self._parse_llm_response(response)
    
    def _get_slide_index_by_id(self, presentation: Any, slide_id: str) -> Optional[int]:
        """
        根据幻灯片ID获取索引
        
        Args:
            presentation: PPT演示文稿对象
            slide_id: 幻灯片ID
            
        Returns:
            幻灯片索引，未找到时返回None
        """
        try:
            # 获取所有幻灯片
            ppt_json = self.ppt_manager.get_presentation_json(presentation, include_details=False)
            slides = ppt_json.get("slides", [])
            
            # 遍历查找匹配ID的幻灯片
            for i, slide in enumerate(slides):
                if slide.get("slide_id") == slide_id:
                    return i
            
            logger.warning(f"未找到ID为 {slide_id} 的幻灯片")
            return None
            
        except Exception as e:
            logger.warning(f"获取幻灯片索引时出错: {str(e)}")
            return None 