#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
幻灯片验证Agent模块

负责验证生成的幻灯片是否符合质量要求，检测布局问题、内容溢出等。
"""

import logging
import os
import json
from typing import Dict, Any, List, Optional, Tuple
import re
from jinja2 import Template

from core.agents.base_agent import BaseAgent
from core.engine.state import AgentState
from core.llm.model_manager import ModelManager
from config.prompts.slide_validator_prompts import SLIDE_VALIDATION_PROMPT, CONTENT_VALIDATION_PROMPT

logger = logging.getLogger(__name__)

# 导入PPT管理器
try:
    from interfaces.ppt_api import PPTManager
except ImportError:
    logger = logging.getLogger(__name__)
    logger.error("无法导入PPTManager，请确保ppt_manager库已正确安装")
    PPTManager = None

class SlideValidatorAgent(BaseAgent):
    """幻灯片验证Agent，负责验证生成的幻灯片质量"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化幻灯片验证Agent
        
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
        self.vision_model = model_config.get("model")
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
        
        logger.info(f"初始化SlideValidatorAgent，使用模型: {self.vision_model}")
    
    async def run(self, state: AgentState) -> AgentState:
        """
        执行幻灯片验证
        
        Args:
            state: 当前工作流状态
            
        Returns:
            更新后的状态
        """
        logger.info("开始验证幻灯片")
        
        # 检查是否有当前幻灯片
        if not hasattr(state, "current_slide") or not state.current_slide:
            logger.error("没有当前幻灯片可供验证")
            state.validation_result = False
            state.validation_issues = ["缺少幻灯片数据"]
            state.validation_suggestions = ["重新生成幻灯片"]
            return state
        
        try:
            # 获取当前幻灯片信息
            current_slide = state.current_slide
            slide_id = current_slide.get("slide_id")
            operations = current_slide.get("operations", [])
            
            # 获取幻灯片数据
            presentation = getattr(state, "presentation", None)
            if not presentation:
                logger.error("没有找到演示文稿对象")
                state.validation_result = False
                state.validation_issues = ["缺少演示文稿对象"]
                state.validation_suggestions = ["检查工作流状态"]
                return state
            
            # 获取幻灯片索引
            slide_index = self._get_slide_index_by_id(presentation, slide_id)
            if slide_index is None:
                logger.error(f"无法找到ID为 {slide_id} 的幻灯片")
                state.validation_result = False
                state.validation_issues = [f"无法找到ID为 {slide_id} 的幻灯片"]
                state.validation_suggestions = ["检查幻灯片ID是否正确"]
                return state
                
            # 渲染幻灯片为图片
            logger.info(f"渲染幻灯片 {slide_id} 为图片用于验证")
            output_dir = getattr(state, "output_dir", "workspace/output/preview")
            os.makedirs(output_dir, exist_ok=True)
            
            # 修正：使用实际索引而不是slide_index值，这是一个数字而不是slide对象
            real_slide_index = None
            for i, slide in enumerate(presentation.slides):
                if hasattr(slide, 'slide_id') and slide.slide_id == slide_id:
                    real_slide_index = i
                    break
            
            if real_slide_index is None:
                logger.error(f"无法找到ID为 {slide_id} 的幻灯片索引")
                state.validation_result = False
                state.validation_issues = [f"无法找到ID为 {slide_id} 的幻灯片索引"]
                state.validation_suggestions = ["检查幻灯片ID是否正确"]
                return state
                
            logger.info(f"找到幻灯片索引: {real_slide_index}")
            
            # 创建临时目录用于存储渲染的幻灯片图像和临时PPTX文件
            from pathlib import Path
            import uuid
            import tempfile
            
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
                logger.info(f"使用临时PPTX文件渲染幻灯片，索引: {real_slide_index}")
                image_paths = self.ppt_manager.render_pptx_file(
                    pptx_path=str(temp_pptx_path),
                    output_dir=str(session_dir),
                    slide_index=real_slide_index
                )
                
                logger.info(f"渲染结果: {image_paths}")
            finally:
                # 无论渲染成功与否，都删除临时PPTX文件
                if temp_pptx_path.exists():
                    logger.info(f"删除临时PPTX文件: {temp_pptx_path}")
                    temp_pptx_path.unlink()
            
            if not image_paths or len(image_paths) == 0:
                logger.error("渲染幻灯片图像失败")
                state.validation_result = False
                state.validation_issues = ["渲染幻灯片图像失败"]
                state.validation_suggestions = ["检查PPT渲染服务"]
                return state
                
            # 更新幻灯片图片路径
            image_path = image_paths[0]
            current_slide["image_path"] = image_path
            
            # 验证幻灯片
            validation_result = True
            issues = []
            suggestions = []
            
            # 使用多模态模型分析幻灯片图像
            logger.info(f"使用视觉模型分析幻灯片图像: {image_path}")
            analysis = await self._analyze_with_vision_model(image_path, operations)
            
            # 处理分析结果
            validation_result = not analysis.get("has_issues", False)
            issues = analysis.get("issues", [])
            suggestions = analysis.get("suggestions", [])
            
            # 增加验证次数计数
            if not hasattr(state, "validation_attempts") or state.validation_attempts is None:
                state.validation_attempts = 0
            state.validation_attempts += 1
            
            # 在多次尝试后降低验证标准
            max_attempts = 3
            if state.validation_attempts >= max_attempts and not validation_result:
                logger.warning(f"已尝试 {state.validation_attempts} 次，强制通过验证")
                validation_result = True
                issues.append(f"经过 {state.validation_attempts} 次修改尝试，仍有未解决的问题")
            
            # 更新状态
            state.validation_result = validation_result
            state.validation_issues = issues
            state.validation_suggestions = suggestions
            
            # 记录验证信息
            if validation_result:
                logger.info("幻灯片验证通过")
                # 验证通过时，将幻灯片添加到已生成列表
                if not hasattr(state, "generated_slides"):
                    state.generated_slides = []
                state.generated_slides.append(current_slide)
                # 增加索引，准备生成下一张幻灯片
                state.current_section_index += 1
                # 判断是否还有更多内容需要处理
                state.has_more_content = (state.current_section_index < len(state.content_plan))
                # 重置验证尝试次数
                state.validation_attempts = 0
            else:
                logger.warning(f"幻灯片验证不通过，问题: {issues}")
                logger.info(f"修复建议: {suggestions}")
            
            # 记录检查点
            self.add_checkpoint(state)
            
        except Exception as e:
            error_msg = f"幻灯片验证失败: {str(e)}"
            logger.error(error_msg)
            logger.exception(e)
            state.validation_result = False
            state.validation_issues = ["验证过程出错"]
            state.validation_suggestions = ["检查日志并修复错误"]
        
        return state
    
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
    
    async def _analyze_with_vision_model(self, image_path: str, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        使用视觉模型分析幻灯片图像
        
        Args:
            image_path: 幻灯片图像路径
            operations: 应用于幻灯片的操作列表
            
        Returns:
            分析结果
        """
        # 检查图像是否存在
        if not os.path.exists(image_path):
            logger.warning(f"图像文件不存在: {image_path}")
            return {"has_issues": True, "issues": ["图像文件不存在"], "suggestions": ["重新生成幻灯片预览"]}
        
        try:
            # 使用Jinja2模板渲染提示词
            operations_json = json.dumps(operations, ensure_ascii=False, indent=2)
            template = Template(SLIDE_VALIDATION_PROMPT)
            prompt = template.render(operations_json=operations_json)
            
            # 调用视觉模型分析图像
            response = await self.model_manager.analyze_image(
                model=self.vision_model,
                prompt=prompt,
                image_path=image_path
            )
            
            # 解析模型响应
            return self._parse_vision_response(response)
            
        except Exception as e:
            logger.exception(f"视觉分析过程中出错: {str(e)}")
            return {
                "has_issues": True,
                "issues": ["视觉分析过程中出错"],
                "suggestions": ["检查日志并修复错误"]
            }
    
    def _read_image(self, image_path: str) -> bytes:
        """
        读取图像文件为字节数据
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            图像字节数据
        """
        with open(image_path, "rb") as f:
            return f.read()
    
    def _parse_vision_response(self, response: str) -> Dict[str, Any]:
        """
        解析视觉模型响应
        
        Args:
            response: 视觉模型响应文本
            
        Returns:
            解析后的结果字典
        """
        try:
            # 尝试直接解析JSON响应
            json_text = response
            
            # 如果响应包含JSON代码块，提取它
            if "```json" in response:
                pattern = r"```(?:json)?\s*([\s\S]*?)```"
                matches = re.findall(pattern, response)
                if matches:
                    json_text = matches[0]
            
            # 解析JSON
            result = json.loads(json_text)
            
            # 确保结果有必要的字段
            if not isinstance(result, dict):
                raise ValueError("响应不是有效的JSON对象")
            
            # 添加默认字段
            result.setdefault("has_issues", False)
            result.setdefault("issues", [])
            result.setdefault("suggestions", [])
            
            return result
            
        except Exception as e:
            logger.exception(f"解析视觉模型响应出错: {str(e)}")
            
            # 尝试从文本中提取问题和建议
            issues = []
            suggestions = []
            
            # 简单解析文本中的问题和建议
            lines = response.split("\n")
            current_section = None
            
            for line in lines:
                line = line.strip()
                if "问题" in line or "issue" in line.lower():
                    current_section = "issues"
                elif "建议" in line or "suggestion" in line.lower():
                    current_section = "suggestions"
                elif line and current_section:
                    # 移除行首的数字、破折号等
                    cleaned_line = re.sub(r"^[\d\.\-\*]+\s*", "", line)
                    if cleaned_line:
                        if current_section == "issues":
                            issues.append(cleaned_line)
                        elif current_section == "suggestions":
                            suggestions.append(cleaned_line)
            
            # 确定是否有问题
            has_issues = len(issues) > 0
            
            return {
                "has_issues": has_issues,
                "issues": issues,
                "suggestions": suggestions
            } 