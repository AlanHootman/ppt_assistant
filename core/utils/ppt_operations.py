#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PPT操作工具模块

提供统一的PPT幻灯片操作功能，包括单个操作执行和批量操作执行。
供slide_generator_agent和ppt_finalizer_agent等多个模块复用。
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class PPTOperationExecutor:
    """PPT操作执行器，负责执行PPT操作"""
    
    def __init__(self, ppt_manager, agent_name="PPTOperationExecutor"):
        """
        初始化PPT操作执行器
        
        Args:
            ppt_manager: PPT管理器实例
            agent_name: 执行器所属的Agent名称
        """
        self.ppt_manager = ppt_manager
        self.agent_name = agent_name
        logger.info(f"初始化PPT操作执行器，所属Agent: {agent_name}")
    
    async def execute_batch_operations(self, presentation: Any, slide_index: int, 
                                 operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量执行幻灯片操作
        
        Args:
            presentation: 演示文稿对象
            slide_index: 幻灯片索引
            operations: 操作列表
            
        Returns:
            操作结果
        """
        if not operations:
            return {"success": True, "message": "没有需要执行的操作", "operations_count": 0}
        
        # 确保operations是列表
        if not isinstance(operations, list):
            return {"success": False, "message": f"operations不是列表类型: {type(operations)}", "operations_count": 0}
        
        logger.info(f"开始执行幻灯片 {slide_index} 的 {len(operations)} 个操作")
        success_count = 0
        failed_operations = []
        
        for i, operation in enumerate(operations):
            # 确保每个操作是字典类型
            if not isinstance(operation, dict):
                logger.warning(f"操作 {i+1} 不是字典类型: {type(operation)}, 值: {operation}")
                failed_operations.append({
                    "index": i,
                    "operation": "unknown",
                    "element_id": "unknown",
                    "message": f"操作不是字典类型: {type(operation)}"
                })
                continue
                
            op_type = operation.get("operation", "unknown")
            element_id = operation.get("element_id", "unknown")
            
            try:
                # 根据操作类型执行不同的操作
                if op_type == "update_element_content":
                    result = self._execute_update_text(presentation, slide_index, operation)
                elif op_type == "delete_element":
                    result = self._execute_delete_element(presentation, slide_index, operation)
                elif op_type == "adjust_element_position":
                    result = self._execute_resize_element(presentation, slide_index, operation)
                elif op_type == "move_element":
                    result = self._execute_move_element(presentation, slide_index, operation)
                elif op_type == "replace_image":
                    result = self._execute_update_image(presentation, slide_index, operation)
                elif op_type == "adjust_text_font_size":
                    result = self._execute_adjust_font_size(presentation, slide_index, operation)
                else:
                    logger.warning(f"不支持的操作类型: {op_type}")
                    result = {"success": False, "message": f"不支持的操作类型: {op_type}"}
                
                # 记录操作结果
                if result.get("success"):
                    success_count += 1
                    logger.info(f"成功执行操作 {i+1}/{len(operations)}: {op_type} -> {element_id}")
                else:
                    failed_operations.append({
                        "index": i,
                        "operation": op_type,
                        "element_id": element_id,
                        "message": result.get("message", "未知错误")
                    })
                    logger.warning(f"操作失败 {i+1}/{len(operations)}: {op_type} -> {element_id}, 错误: {result.get('message')}")
                    
            except Exception as e:
                failed_operations.append({
                    "index": i,
                    "operation": op_type,
                    "element_id": element_id,
                    "message": str(e)
                })
                logger.error(f"执行操作时出错 {i+1}/{len(operations)}: {op_type} -> {element_id}, 错误: {str(e)}")
        
        # 返回总体结果
        overall_success = success_count == len(operations)
        return {
            "success": overall_success,
            "message": f"执行了 {success_count}/{len(operations)} 个操作" if overall_success else f"有 {len(failed_operations)} 个操作失败",
            "operations_count": len(operations),
            "success_count": success_count,
            "failed_operations": failed_operations
        }
    
    def _execute_update_text(self, presentation: Any, slide_index: int, operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行文本更新操作
        
        Args:
            presentation: 演示文稿对象
            slide_index: 幻灯片索引
            operation: 操作参数
            
        Returns:
            操作结果
        """
        element_id = operation.get("element_id")
        content = operation.get("content")
        
        if not content:
            return {"success": False, "message": "缺少content参数"}
        
        # 使用update_element_content更新文本
        if element_id:
            result = self.ppt_manager.update_element_content(
                presentation=presentation,
                slide_index=slide_index,
                element_id=element_id,
                new_content=content
            )
        else:
            return {"success": False, "message": "缺少element_id参数"}
        
        return result
    
    def _execute_delete_element(self, presentation: Any, slide_index: int, operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行删除元素操作
        
        Args:
            presentation: 演示文稿对象
            slide_index: 幻灯片索引
            operation: 操作参数
            
        Returns:
            操作结果
        """
        element_id = operation.get("element_id")
        
        # 删除元素
        if element_id:
            result = self.ppt_manager.delete_element(
                presentation=presentation,
                slide_index=slide_index,
                element_id=element_id
            )
        else:
            return {"success": False, "message": "缺少element_id参数"}
        
        return result
    
    def _execute_resize_element(self, presentation: Any, slide_index: int, operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行调整元素位置和大小操作
        
        Args:
            presentation: 演示文稿对象
            slide_index: 幻灯片索引
            operation: 操作参数
            
        Returns:
            操作结果
        """
        element_id = operation.get("element_id")
        content = operation.get("content", {})
        
        if not isinstance(content, dict):
            return {"success": False, "message": "content参数必须是字典类型"}
        
        left = content.get("left")
        top = content.get("top")
        width = content.get("width")
        height = content.get("height")
        
        if left is None and top is None and width is None and height is None:
            return {"success": False, "message": "缺少位置或大小参数"}
        
        # 调整元素位置和大小
        if element_id:
            result = self.ppt_manager.adjust_element_position(
                presentation=presentation,
                slide_index=slide_index,
                element_id=element_id,
                left=left,
                top=top,
                width=width,
                height=height
            )
            return result
        else:
            return {"success": False, "message": "缺少element_id参数"}
    
    def _execute_move_element(self, presentation: Any, slide_index: int, operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行移动元素操作
        
        Args:
            presentation: 演示文稿对象
            slide_index: 幻灯片索引
            operation: 操作参数
            
        Returns:
            操作结果
        """
        element_id = operation.get("element_id")
        content = operation.get("content", {})
        
        if not isinstance(content, dict):
            return {"success": False, "message": "content参数必须是字典类型"}
        
        left = content.get("left")
        top = content.get("top")
        
        if left is None and top is None:
            return {"success": False, "message": "缺少left或top参数"}
        
        # 移动元素
        if element_id:
            result = self.ppt_manager.adjust_element_position(
                presentation=presentation,
                slide_index=slide_index,
                element_id=element_id,
                left=left,
                top=top,
                width=None,
                height=None
            )
        else:
            return {"success": False, "message": "缺少element_id参数"}
        
        return result
    
    def _execute_update_image(self, presentation: Any, slide_index: int, operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行更新图片操作
        
        Args:
            presentation: 演示文稿对象
            slide_index: 幻灯片索引
            operation: 操作参数
            
        Returns:
            操作结果
        """
        element_id = operation.get("element_id")
        content = operation.get("content")  # 图片路径
        
        if not content:
            return {"success": False, "message": "缺少content参数（图片路径）"}
        
        # 更新图片
        if element_id:
            result = self.ppt_manager.replace_image(
                presentation=presentation,
                slide_index=slide_index,
                element_id=element_id,
                image_path=content
            )
        else:
            return {"success": False, "message": "缺少element_id参数"}
        
        return result

    def _execute_adjust_font_size(self, presentation: Any, slide_index: int, operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行字体大小调整操作
        
        Args:
            presentation: 演示文稿对象
            slide_index: 幻灯片索引
            operation: 操作参数
            
        Returns:
            操作结果
        """
        element_id = operation.get("element_id")
        content = operation.get("content")  # 字体大小值
        
        if content is None:
            return {"success": False, "message": "缺少content参数（字体大小）"}
        
        try:
            # 将字体大小转换为整数
            font_size = int(content)
            
            # 更新字体大小
            if element_id:
                result = self.ppt_manager.adjust_text_font_size(
                    presentation=presentation,
                    slide_index=slide_index,
                    element_id=element_id,
                    font_size=font_size
                )
            else:
                return {"success": False, "message": "缺少element_id参数"}
            
            return result
        except ValueError:
            return {"success": False, "message": f"无效的字体大小值: {content}"}
        except Exception as e:
            return {"success": False, "message": f"调整字体大小时出错: {str(e)}"}


class PPTOperationHelper:
    """PPT操作辅助工具类，提供创建标准操作指令的静态方法"""
    
    @staticmethod
    def create_operation(operation_type: str, element_id: str, content: Any = None) -> Dict[str, Any]:
        """
        创建标准的操作指令
        
        Args:
            operation_type: 操作类型
            element_id: 元素ID
            content: 操作内容（可选）
            
        Returns:
            标准格式的操作指令
        """
        operation = {
            "operation": operation_type,
            "element_id": element_id
        }
        
        if content is not None:
            operation["content"] = content
            
        return operation
    
    @staticmethod
    def create_update_content_operation(element_id: str, new_content: str) -> Dict[str, Any]:
        """创建文本内容更新操作"""
        return PPTOperationHelper.create_operation("update_element_content", element_id, new_content)
    
    @staticmethod
    def create_adjust_font_size_operation(element_id: str, font_size: int) -> Dict[str, Any]:
        """创建字体大小调整操作"""
        return PPTOperationHelper.create_operation("adjust_text_font_size", element_id, font_size)
    
    @staticmethod
    def create_replace_image_operation(element_id: str, image_path: str) -> Dict[str, Any]:
        """创建图片替换操作"""
        return PPTOperationHelper.create_operation("replace_image", element_id, image_path)
    
    @staticmethod
    def create_adjust_position_operation(element_id: str, left: Optional[float] = None,
                                       top: Optional[float] = None, width: Optional[float] = None,
                                       height: Optional[float] = None) -> Dict[str, Any]:
        """创建元素位置调整操作"""
        position_params = {}
        if left is not None:
            position_params["left"] = left
        if top is not None:
            position_params["top"] = top
        if width is not None:
            position_params["width"] = width
        if height is not None:
            position_params["height"] = height
            
        return PPTOperationHelper.create_operation("adjust_element_position", element_id, position_params)
    
    @staticmethod
    def create_delete_element_operation(element_id: str) -> Dict[str, Any]:
        """创建元素删除操作"""
        return PPTOperationHelper.create_operation("delete_element", element_id) 