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
from config.prompts.slide_generator_prompts import LLM_PPT_ELEMENT_MATCHING_PROMPT

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
            # 尝试导入PPTManager
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
            # 检查PPTManager是否已初始化
            if not hasattr(self, 'ppt_manager') or self.ppt_manager is None:
                raise ValueError("PPTManager未初始化")
            
            # 检查内容规划是否存在
            if not state.content_plan:
                raise ValueError("缺少内容规划，无法生成幻灯片")
            
            # 统一模板路径参数，优先使用template_path，兼容ppt_template_path
            template_path = state.template_path if hasattr(state, 'template_path') and state.template_path else state.ppt_template_path if hasattr(state, 'ppt_template_path') else None
            if not template_path or not os.path.exists(template_path):
                raise ValueError(f"无效的PPT模板路径: {template_path}")
            
            # 获取当前章节索引
            current_index = state.current_section_index
            if current_index is None:
                raise ValueError("当前章节索引未定义")
                
            # 检查索引是否在有效范围内
            if current_index < 0 or current_index >= len(state.content_plan):
                raise ValueError(f"无效的章节索引: {current_index}，内容规划共有{len(state.content_plan)}个章节")
            
            # 获取当前要处理的章节
            current_section = state.content_plan[current_index]
            logger.info(f"处理章节 {current_index + 1}/{len(state.content_plan)}: {current_section.get('slide_type', '未知类型')}")
            
            # 加载PPT模板
            presentation = self.ppt_manager.load_presentation(template_path)
            logger.info(f"已加载PPT模板: {template_path}")
            
            # 获取PPT的JSON结构，用于获取模板幻灯片ID
            ppt_json = self.ppt_manager.get_presentation_json(presentation, include_details=False)
            logger.info(f"已获取PPT JSON结构，包含 {len(ppt_json.get('slides', []))} 张幻灯片")
            
            # 获取模板幻灯片ID
            template_info = current_section.get("template", {})
            slide_id = self._get_template_slide_id(template_info, ppt_json)
            logger.info(f"已选择模板幻灯片ID: {slide_id}")
            
            # 复制模板幻灯片
            duplicate_result = self.ppt_manager.duplicate_slide_by_id(
                presentation=presentation,
                slide_id=slide_id
            )
            
            if not duplicate_result["success"]:
                raise ValueError(f"复制模板幻灯片失败: {duplicate_result.get('message', '未知错误')}")
                
            new_slide_id = duplicate_result["slide_id"]
            # 更新presentation对象，确保包含新创建的幻灯片
            presentation = duplicate_result["presentation"]
            
            logger.info(f"已复制模板幻灯片, 新幻灯片ID: {new_slide_id}")
            
            # 直接获取新幻灯片的详细信息
            slide_result = self.ppt_manager.get_slide_json_by_id(
                presentation=presentation,
                slide_id=new_slide_id            
            )
                    
            # 使用LLM进行内容-元素智能匹配
            logger.info("调用LLM进行内容-元素智能匹配")
            llm_matches = await self._llm_match_content_to_elements(
                slide_type=current_section.get("slide_type", "content"),
                slide_elements=slide_result,
                current_section=current_section
            )
            
            if not llm_matches:
                raise ValueError("LLM未能正确匹配内容和元素")
            
            # 应用LLM匹配结果到幻灯片
            logger.info(f"开始应用LLM匹配结果，共 {len(llm_matches)} 项")
            success = await self._apply_llm_matches(presentation, new_slide_id, llm_matches)
            
            if not success:
                raise ValueError("应用LLM匹配结果失败")
            
            # # 生成幻灯片预览
            # preview_dir = os.path.join(state.output_dir, "previews")
            # os.makedirs(preview_dir, exist_ok=True)
            # preview_path = os.path.join(preview_dir, f"slide_{current_index}.png")
            
            # slide_index = self._get_slide_index_by_id(presentation, new_slide_id)
            # render_result = self.ppt_manager.render_presentation(
            #     presentation=presentation,
            #     output_dir=preview_dir,
            #     slide_index=slide_index,
            #     format="png"
            # )
            
            # if render_result and len(render_result) > 0:
            #     preview_path = render_result[0]
            #     logger.info(f"已生成幻灯片预览: {preview_path}")
            # else:
            #     logger.warning("生成幻灯片预览失败")
            
            # # 保存修改后的演示文稿
            # output_path = os.path.join(state.output_dir, f"generated_slide_{current_index}.pptx")
            # self.ppt_manager.save_presentation(presentation, output_path)
            # logger.info(f"已保存修改后的演示文稿: {output_path}")
            
            # 更新状态
            if not hasattr(state, 'generated_slides') or state.generated_slides is None:
                state.generated_slides = []
            
            # 添加已生成的幻灯片信息
            slide_info = {
                "section_index": current_index,
                "slide_id": new_slide_id,
                # "preview_path": preview_path,
                # "pptx_path": output_path
            }
            state.generated_slides.append(slide_info)
            logger.info(f"已更新状态，添加生成的幻灯片信息")
            
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
    
    def _get_slide_index_by_id(self, presentation: Any, slide_id: str) -> Optional[int]:
        """
        根据幻灯片ID获取索引
        
        Args:
            presentation: PPT演示文稿对象
            slide_id: 幻灯片ID
            
        Returns:
            幻灯片索引，未找到时返回None
        """
        # 获取所有幻灯片
        result = self.ppt_manager.get_slides(presentation)
        if not result["success"]:
            logger.error("获取幻灯片列表失败")
            return None
        
        # 遍历查找匹配ID的幻灯片
        slides = result["slides"]
        for i, slide in enumerate(slides):
            if slide.get("id") == slide_id:
                return i
        
        logger.warning(f"未找到ID为 {slide_id} 的幻灯片")
        return None
    
    async def _llm_match_content_to_elements(self, slide_type: str, slide_elements: List[Dict[str, Any]], current_section: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        使用LLM将章节内容与幻灯片元素进行智能匹配
        
        Args:
            slide_type: 幻灯片类型（opening, content, closing）
            slide_elements: 幻灯片元素列表
            current_section: 当前处理的章节信息
            
        Returns:
            匹配结果列表
        """
        try:
            # 将slide_type转换为中文描述，更适合中文大模型理解
            slide_type_map = {
                "opening": "开篇页",
                "content": "内容页",
                "closing": "结束页"
            }
            slide_type_zh = slide_type_map.get(slide_type, slide_type)
            
            # 构建提示词上下文
            context = {
                "slide_elements_json": json.dumps(slide_elements, ensure_ascii=False, indent=2, cls=EnumEncoder),
                "content_json": json.dumps(current_section, ensure_ascii=False, indent=2, cls=EnumEncoder), 
                "slide_type": slide_type_zh
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
            matches = self._parse_llm_matching_response(response)
            
            if matches:
                logger.info(f"LLM成功返回 {len(matches)} 个内容-元素匹配")
                return matches
            else:
                logger.warning("无法从LLM响应中解析出有效的匹配结果")
                return []
                
        except Exception as e:
            logger.exception(f"LLM内容-元素匹配过程出错: {str(e)}")
            return []
    
    def _parse_llm_matching_response(self, response: str) -> List[Dict[str, Any]]:
        """
        解析LLM返回的匹配响应
        
        Args:
            response: LLM响应文本
            
        Returns:
            解析后的匹配结果列表
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
            
            # 提取匹配列表
            if isinstance(result, dict) and "matches" in result:
                matches = result["matches"]
                if isinstance(matches, list):
                    return matches
            
            # 如果直接是列表，尝试直接使用
            if isinstance(result, list):
                return result
                
            logger.warning(f"LLM响应格式不符合预期: {json_text[:100]}...")
            return []
            
        except Exception as e:
            logger.exception(f"解析LLM匹配响应时出错: {str(e)}")
            return []
    
    async def _apply_llm_matches(self, presentation: Any, slide_id: str, matches: List[Dict[str, Any]]) -> bool:
        """
        应用LLM推荐的内容-元素匹配
        
        Args:
            presentation: PPT演示文稿对象
            slide_id: 幻灯片ID
            matches: LLM推荐的匹配列表
            
        Returns:
            是否成功应用所有匹配
        """
        if not matches:
            return False
        
        success_count = 0
        total_count = len(matches)
        
        for match in matches:
            element_id = match.get("element_id")
            content = match.get("content")
            
            if not element_id or content is None:
                logger.warning(f"跳过无效匹配: {match}")
                continue
            
            try:
                # 针对不同类型的内容进行处理
                if isinstance(content, list):
                    # 列表内容（如项目符号）
                    formatted_content = ""
                    for item in content:
                        if item and item.strip():
                            formatted_content += f"• {item.strip()}\n"
                    
                    if formatted_content:
                        result = self.ppt_manager.edit_text_element_by_id(
                            presentation=presentation,
                            slide_id=slide_id,
                            element_id=element_id,
                            new_text=formatted_content.strip()
                        )
                        
                        if result.get("success"):
                            success_count += 1
                            logger.info(f"成功应用列表内容到元素 {element_id}")
                else:
                    # 字符串内容
                    result = self.ppt_manager.edit_text_element_by_id(
                        presentation=presentation,
                        slide_id=slide_id,
                        element_id=element_id,
                        new_text=str(content).strip()
                    )
                    
                    if result.get("success"):
                        success_count += 1
                        logger.info(f"成功应用文本内容到元素 {element_id}")
            
            except Exception as e:
                logger.warning(f"应用匹配 {element_id} 时出错: {str(e)}")
        
        # 计算成功率
        success_rate = success_count / total_count if total_count > 0 else 0
        logger.info(f"应用LLM匹配完成，成功率: {success_rate:.2%} ({success_count}/{total_count})")
        
        # 如果有任何匹配成功应用，就认为整体成功
        return success_count > 0 