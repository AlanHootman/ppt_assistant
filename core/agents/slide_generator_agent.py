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
        self.model_type = config.get("model_type", "vision")
        
        # 初始化模型属性
        model_config = self.model_manager.get_model_config(self.model_type)
        self.llm_model = model_config.get("model")
        self.vision_model = model_config.get("model")  # 为验证功能使用同一个视觉模型
        # 直接使用模型配置中的值，不再需要类型转换
        self.temperature = model_config.get("temperature")
        self.max_tokens = model_config.get("max_tokens")
        
        # 获取迭代优化相关配置
        self.max_iterations = config.get("max_iterations", settings.MAX_SLIDE_ITERATIONS)
        
        # 初始化PPTManager
        try:
            from interfaces.ppt_api import PPTManager
            self.ppt_manager = PPTManager()
            logger.info("成功初始化PPT管理器")
        except ImportError as e:
            logger.error(f"无法导入PPTManager: {str(e)}")
            self.ppt_manager = None
        
        logger.info(f"初始化SlideGeneratorAgent，使用模型: {self.llm_model}, 最大迭代次数: {self.max_iterations}")
    
    async def run(self, state: AgentState) -> AgentState:
        """
        执行幻灯片生成逻辑，包含自验证功能

        Args:
            state: 工作流引擎状态

        Returns:
            更新后的工作流引擎状态
        """
        logger.info("开始生成幻灯片")
        
        try:
            # 第一步：准备工作 - 加载和检查必要资源
            presentation = await self._prepare_presentation(state)
            
            # 第二步：生成幻灯片
            await self._generate_slide(state, presentation)
            
            # 第三步：验证幻灯片质量
            await self._validate_slide(state, presentation)
            
            return state
            
        except Exception as e:
            error_msg = f"幻灯片生成失败: {str(e)}"
            logger.error(error_msg)
            logger.exception(e)
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
    
    def _check_validation_prerequisites(self, state: AgentState) -> bool:
        """
        检查验证前置条件
        
        Args:
            state: 当前状态
            
        Returns:
            是否满足前置条件
        """
        if not hasattr(state, "current_slide") or not state.current_slide:
            logger.error("没有当前幻灯片可供验证")
            state.validation_result = False
            state.validation_issues = ["缺少幻灯片数据"]
            state.validation_suggestions = ["重新生成幻灯片"]
            return False
            
        if not hasattr(state, "content_plan") or not state.content_plan:
            logger.error("没有内容计划可供验证")
            state.validation_result = False
            state.validation_issues = ["缺少内容计划"]
            state.validation_suggestions = ["重新生成内容计划"]
            return False
            
        return True
    
    def _update_validation_result(self, state: AgentState, analysis: Dict[str, Any]) -> None:
        """
        更新验证结果
        
        Args:
            state: 当前状态
            analysis: 分析结果
        """
        # 获取分析结果
        issues = analysis.get("issues", [])
        suggestions = analysis.get("suggestions", [])
        quality_score = analysis.get("quality_score", 0)
        
        # 更新状态
        state.validation_issues = issues
        state.validation_suggestions = suggestions
        
        # 记录质量分数
        if not hasattr(state, "quality_scores"):
            state.quality_scores = []
        state.quality_scores.append(quality_score)
        
        # 记录验证信息
        if state.validation_result:
            logger.info(f"幻灯片验证通过，质量评分: {quality_score}/10")
        else:
            logger.warning(f"幻灯片验证不通过，质量评分: {quality_score}/10")
            logger.warning(f"问题: {issues}")
            logger.info(f"修复建议: {suggestions}")
            
        # 记录验证次数
        logger.info(f"总验证尝试次数: {state.validation_attempts}") 

    def _set_validation_failure(self, state: AgentState, issue: str, suggestions: List[str]) -> None:
        """
        设置验证失败状态
        
        Args:
            state: 当前状态
            issue:
            suggestions:
        """
        state.validation_result = False
        state.validation_issues = [issue]
        state.validation_suggestions = suggestions

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
            temperature=0.2,  # 使用较低的温度以获得更确定的结果
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
        slide_index, presentation = await self._find_template_slide(presentation, current_section)
        
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
            "operations": operations
        }
    
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
    
    async def _analyze_with_vision_model(self, image_path: str, slide_elements: List[Dict[str, Any]], 
                                        current_section: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用多模态视觉模型分析幻灯片图像并提供修改建议
        
        Args:
            image_path: 幻灯片图像路径
            slide_elements: 幻灯片元素详细信息
            current_section: 当前处理的章节内容
            
        Returns:
            分析结果，包含问题、建议和操作指令
        """
        # 检查图像是否存在
        if not os.path.exists(image_path):
            logger.warning(f"图像文件不存在: {image_path}")
            return {
                "has_issues": True, 
                "issues": ["图像文件不存在"], 
                "suggestions": ["重新生成幻灯片预览"]
            }
        
        try:
            # 准备并发送分析请求
            logger.info(f"使用多模态模型分析幻灯片图像: {image_path}")
            
            # 准备上下文数据
            context = {
                "section_json": json.dumps(current_section, ensure_ascii=False, indent=2, cls=EnumEncoder),
                "slide_elements_json": json.dumps(slide_elements, ensure_ascii=False, indent=2, cls=EnumEncoder)
            }
            
            # 渲染提示词
            prompt = self.model_manager.render_template(SLIDE_SELF_VALIDATION_PROMPT, context)
            
            # 调用多模态视觉模型
            response = await self.model_manager.analyze_image(
                model=self.vision_model,
                prompt=prompt,
                image_path=image_path
            )
            
            # 解析响应
            result = self._parse_vision_response(response)
            
            # 记录分析结果
            issues = result.get("issues", [])
            suggestions = result.get("suggestions", [])
            operations = result.get("operations", [])
            
            if issues:
                logger.info(f"多模态模型发现问题: {issues}")
                logger.info(f"修改建议: {suggestions}")
                logger.info(f"修改操作: {len(operations)} 项")
            else:
                logger.info("多模态模型未发现问题")
            
            return result
            
        except Exception as e:
            logger.exception(f"多模态分析过程中出错: {str(e)}")
            return {
                "has_issues": True,
                "issues": ["多模态分析过程中出错"],
                "suggestions": ["检查日志并修复错误"]
            }
    
    async def _validate_slide(self, state: AgentState, presentation: Any) -> None:
        """
        验证生成的幻灯片质量，并根据多模态模型分析结果进行迭代优化
        
        Args:
            state: 当前状态
            presentation: PPT演示文稿对象
        """
        logger.info("开始验证生成的幻灯片")
        
        # 1. 检查前置条件
        if not self._check_validation_prerequisites(state):
            return
        
        try:
            # 2. 准备验证所需参数
            current_slide = state.current_slide
            slide_index = current_slide.get("slide_index")
            operations = current_slide.get("operations", [])
            current_section = state.content_plan[state.current_section_index]
            
            # 初始化验证尝试次数
            if not hasattr(state, "validation_attempts") or state.validation_attempts is None:
                state.validation_attempts = 0
            
            has_issues = True
            iteration_count = 0
            
            # 3. 获取幻灯片详细信息，供多模态模型分析
            slide_elements = self.ppt_manager.get_slide_json(
                presentation=presentation,
                slide_index=slide_index            
            )
            
            # # 4. 验证幻灯片索引
            # real_slide_index = self._get_real_slide_index(presentation, slide_index)
            # if real_slide_index is None:
            #     self._set_validation_failure(state, f"无法找到ID为 {slide_index} 的幻灯片索引", ["检查幻灯片ID是否正确"])
            #     return
            
            # 5. 迭代优化循环
            while has_issues and iteration_count < self.max_iterations:
                iteration_count += 1
                logger.info(f"开始第 {iteration_count} 次幻灯片优化迭代")
                
                # 5.1 渲染幻灯片为图片
                image_path = await self._render_slide_to_image(state, presentation, slide_index)
                if not image_path:
                    break
                
                # 更新幻灯片图片路径
                current_slide["image_path"] = image_path
                
                # 5.2 使用多模态模型分析幻灯片
                analysis = await self._analyze_with_vision_model(
                    image_path=image_path, 
                    slide_elements=slide_elements,
                    current_section=current_section
                )
                
                # 检查是否有问题需要修复
                has_issues = analysis.get("has_issues", False)
                if not has_issues:
                    logger.info(f"第 {iteration_count} 次分析未发现问题，优化完成")
                    break
                
                # 5.3 获取修改操作列表
                fix_operations = analysis.get("operations", [])
                if not fix_operations:
                    logger.warning(f"第 {iteration_count} 次分析发现问题，但未提供修复操作")
                    break
                
                # 5.4 执行修复操作
                logger.info(f"执行第 {iteration_count} 次修复操作，共 {len(fix_operations)} 项")
                success = await self._execute_operations(presentation, slide_index, fix_operations)
                
                if success:
                    # 合并操作记录
                    current_slide["operations"] = operations + fix_operations
                    operations = current_slide["operations"]
                    logger.info(f"第 {iteration_count} 次修复操作执行成功")
                else:
                    logger.warning(f"第 {iteration_count} 次修复操作执行失败")
                    break
            
            # 6. 记录最终验证结果
            state.validation_attempts += iteration_count
            state.validation_result = not has_issues
            
            if has_issues and iteration_count >= self.max_iterations:
                logger.warning(f"已达到最大迭代次数 {self.max_iterations}，强制通过验证")
                state.validation_result = True
                analysis.setdefault("issues", []).append(f"经过 {iteration_count} 次修改尝试，仍有未解决的问题")
            
            # 7. 更新验证结果
            self._update_validation_result(state, analysis)
            
        except Exception as e:
            error_msg = f"幻灯片验证失败: {str(e)}"
            logger.error(error_msg)
            logger.exception(e)
            self._set_validation_failure(state, "验证过程出错", ["检查日志并修复错误"])
    
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
        elif operation_type == "adjust_font_size":
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
        session_dir = Path(f"workspace/sessions/{state.session_id}/validator_images")
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
                self._set_validation_failure(state, "渲染幻灯片图像失败", ["检查PPT渲染服务"])
                return None
                
            return image_paths[0]
            
        finally:
            # 无论渲染成功与否，都删除临时PPTX文件
            if temp_pptx_path.exists():
                logger.info(f"删除临时PPTX文件: {temp_pptx_path}")
                temp_pptx_path.unlink()
    
    async def _find_template_slide(self, presentation: Any, current_section: Dict[str, Any]) -> tuple:
        """
        找到模板幻灯片
        
        Args:
            presentation: 演示文稿对象
            current_section: 当前章节内容
            
        Returns:
            tuple: (幻灯片ID, 更新后的演示文稿对象)
        """
        # 获取PPT的JSON结构并找到模板幻灯片ID
        ppt_json = self.ppt_manager.get_presentation_json(presentation, include_details=False)
        template_info = current_section.get("template", {})
        slide_index = template_info.get("slide_index")
        # slide_id = self._get_template_slide_id(template_info, ppt_json)
        
        # 初始化已编辑幻灯片ID记录（如果不存在）
        if not hasattr(self, "_edited_slides"):
            self._edited_slides = set()
        
        # 判断幻灯片是否已编辑过
        if slide_index in self._edited_slides:
            logger.info(f"幻灯片 {slide_index} 已被编辑过，创建新幻灯片")
            
            # 获取模板布局信息
            layout_name = template_info.get("layout", "Title and Content")
            
            # 创建新幻灯片
            result = self.ppt_manager.create_slide_with_layout(
                presentation=presentation,
                layout_name=layout_name
            )
            
            if result.get("success", False):
                # 获取新创建的幻灯片ID
                new_slide_id = result.get("slide_id")
                logger.info(f"成功创建新幻灯片，ID: {new_slide_id}")
                # 返回可能更新的presentation对象
                presentation = result.get("presentation", presentation)
                return new_slide_id, presentation
            else:
                # 创建失败，仍使用原幻灯片
                logger.warning(f"创建新幻灯片失败: {result.get('message')}，使用原幻灯片")
                return slide_index, presentation
        else:
            # 将当前幻灯片ID添加到已编辑列表
            self._edited_slides.add(slide_index)
            logger.info(f"使用现有幻灯片，ID: {slide_index}")
            
            return slide_index, presentation
    