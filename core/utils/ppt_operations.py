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
        
        logger.info(f"开始执行幻灯片 {slide_index} 的 {len(operations)} 个操作")
        success_count = 0
        failed_operations = []
        
        for i, operation in enumerate(operations):
            op_type = operation.get("type", "unknown")
            op_target = operation.get("target", "unknown")
            
            try:
                # 根据操作类型执行不同的操作
                if op_type == "update_text":
                    result = self._execute_update_text(presentation, slide_index, operation)
                elif op_type == "add_text":
                    result = self._execute_add_text(presentation, slide_index, operation)
                elif op_type == "delete_element":
                    result = self._execute_delete_element(presentation, slide_index, operation)
                elif op_type == "resize_element":
                    result = self._execute_resize_element(presentation, slide_index, operation)
                elif op_type == "move_element":
                    result = self._execute_move_element(presentation, slide_index, operation)
                elif op_type == "update_style":
                    result = self._execute_update_style(presentation, slide_index, operation)
                elif op_type == "update_chart":
                    result = self._execute_update_chart(presentation, slide_index, operation)
                elif op_type == "update_image":
                    result = self._execute_update_image(presentation, slide_index, operation)
                else:
                    logger.warning(f"不支持的操作类型: {op_type}")
                    result = {"success": False, "message": f"不支持的操作类型: {op_type}"}
                
                # 记录操作结果
                if result.get("success"):
                    success_count += 1
                    logger.info(f"成功执行操作 {i+1}/{len(operations)}: {op_type} -> {op_target}")
                else:
                    failed_operations.append({
                        "index": i,
                        "type": op_type,
                        "target": op_target,
                        "message": result.get("message", "未知错误")
                    })
                    logger.warning(f"操作失败 {i+1}/{len(operations)}: {op_type} -> {op_target}, 错误: {result.get('message')}")
                    
            except Exception as e:
                failed_operations.append({
                    "index": i,
                    "type": op_type,
                    "target": op_target,
                    "message": str(e)
                })
                logger.error(f"执行操作时出错 {i+1}/{len(operations)}: {op_type} -> {op_target}, 错误: {str(e)}")
        
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
        position = operation.get("position")
        text = operation.get("text")
        
        if not text:
            return {"success": False, "message": "缺少text参数"}
        
        # 根据element_id或position更新文本
        if element_id:
            result = self.ppt_manager.update_text_by_id(
                presentation, slide_index, element_id, text
            )
        elif position is not None:
            result = self.ppt_manager.update_text_by_position(
                presentation, slide_index, position, text
            )
        else:
            return {"success": False, "message": "缺少element_id或position参数"}
        
        return result
    
    def _execute_add_text(self, presentation: Any, slide_index: int, operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行添加文本操作
        
        Args:
            presentation: 演示文稿对象
            slide_index: 幻灯片索引
            operation: 操作参数
            
        Returns:
            操作结果
        """
        text = operation.get("text")
        left = operation.get("left", 0)
        top = operation.get("top", 0)
        width = operation.get("width", 300)
        height = operation.get("height", 100)
        
        if not text:
            return {"success": False, "message": "缺少text参数"}
        
        result = self.ppt_manager.add_text(
            presentation, slide_index, text, left, top, width, height
        )
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
        position = operation.get("position")
        
        # 根据element_id或position删除元素
        if element_id:
            result = self.ppt_manager.delete_element_by_id(
                presentation, slide_index, element_id
            )
        elif position is not None:
            result = self.ppt_manager.delete_element_by_position(
                presentation, slide_index, position
            )
        else:
            return {"success": False, "message": "缺少element_id或position参数"}
        
        return result
    
    def _execute_resize_element(self, presentation: Any, slide_index: int, operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行调整元素大小操作
        
        Args:
            presentation: 演示文稿对象
            slide_index: 幻灯片索引
            operation: 操作参数
            
        Returns:
            操作结果
        """
        element_id = operation.get("element_id")
        position = operation.get("position")
        width = operation.get("width")
        height = operation.get("height")
        
        if width is None and height is None:
            return {"success": False, "message": "缺少width或height参数"}
        
        # 根据element_id或position调整元素大小
        if element_id:
            result = self.ppt_manager.resize_element_by_id(
                presentation, slide_index, element_id, width, height
            )
        elif position is not None:
            result = self.ppt_manager.resize_element_by_position(
                presentation, slide_index, position, width, height
            )
        else:
            return {"success": False, "message": "缺少element_id或position参数"}
        
        return result
    
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
        position = operation.get("position")
        left = operation.get("left")
        top = operation.get("top")
        
        if left is None and top is None:
            return {"success": False, "message": "缺少left或top参数"}
        
        # 根据element_id或position移动元素
        if element_id:
            result = self.ppt_manager.move_element_by_id(
                presentation, slide_index, element_id, left, top
            )
        elif position is not None:
            result = self.ppt_manager.move_element_by_position(
                presentation, slide_index, position, left, top
            )
        else:
            return {"success": False, "message": "缺少element_id或position参数"}
        
        return result
    
    def _execute_update_style(self, presentation: Any, slide_index: int, operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行更新样式操作
        
        Args:
            presentation: 演示文稿对象
            slide_index: 幻灯片索引
            operation: 操作参数
            
        Returns:
            操作结果
        """
        element_id = operation.get("element_id")
        position = operation.get("position")
        style_props = operation.get("style", {})
        
        if not style_props:
            return {"success": False, "message": "缺少style参数"}
        
        # 根据element_id或position更新样式
        if element_id:
            result = self.ppt_manager.update_element_style_by_id(
                presentation, slide_index, element_id, style_props
            )
        elif position is not None:
            result = self.ppt_manager.update_element_style_by_position(
                presentation, slide_index, position, style_props
            )
        else:
            return {"success": False, "message": "缺少element_id或position参数"}
        
        return result
    
    def _execute_update_chart(self, presentation: Any, slide_index: int, operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行更新图表操作
        
        Args:
            presentation: 演示文稿对象
            slide_index: 幻灯片索引
            operation: 操作参数
            
        Returns:
            操作结果
        """
        element_id = operation.get("element_id")
        position = operation.get("position")
        chart_data = operation.get("chart_data")
        
        if not chart_data:
            return {"success": False, "message": "缺少chart_data参数"}
        
        # 根据element_id或position更新图表数据
        if element_id:
            result = self.ppt_manager.update_chart_by_id(
                presentation, slide_index, element_id, chart_data
            )
        elif position is not None:
            result = self.ppt_manager.update_chart_by_position(
                presentation, slide_index, position, chart_data
            )
        else:
            return {"success": False, "message": "缺少element_id或position参数"}
        
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
        position = operation.get("position")
        image_path = operation.get("image_path")
        
        if not image_path:
            return {"success": False, "message": "缺少image_path参数"}
        
        # 根据element_id或position更新图片
        if element_id:
            result = self.ppt_manager.update_image_by_id(
                presentation, slide_index, element_id, image_path
            )
        elif position is not None:
            result = self.ppt_manager.update_image_by_position(
                presentation, slide_index, position, image_path
            )
        else:
            return {"success": False, "message": "缺少element_id或position参数"}
        
        return result


class PPTOperationHelper:
    """PPT操作辅助工具类，提供静态方法"""
    
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