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
    """PPT操作执行器，提供统一的PPT操作接口"""
    
    def __init__(self, ppt_manager, agent_name: str = "PPTOperationExecutor"):
        """
        初始化PPT操作执行器
        
        Args:
            ppt_manager: PPT管理器实例
            agent_name: 调用该执行器的代理名称，用于日志记录
        """
        self.ppt_manager = ppt_manager
        self.agent_name = agent_name
        self.logger = logging.getLogger(f"{__name__}.{agent_name}")
    
    async def execute_single_operation(self, presentation: Any, slide_index: int, 
                                     operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行单个PPT操作
        
        Args:
            presentation: PPT演示文稿对象
            slide_index: 幻灯片索引
            operation: 操作指令，包含以下字段：
                - element_id: 元素ID
                - operation: 操作类型
                - content: 操作内容
                
        Returns:
            操作结果字典，包含success标志和message信息
        """
        element_id = operation.get("element_id")
        operation_type = operation.get("operation", "update_element_content")
        content = operation.get("content")
        
        if not element_id:
            return {"success": False, "message": "缺少element_id参数"}
        
        try:
            # 根据操作类型分发到具体的操作方法
            if operation_type == "update_element_content":
                return await self._execute_update_content(presentation, slide_index, element_id, content)
            elif operation_type == "adjust_text_font_size":
                return await self._execute_adjust_font_size(presentation, slide_index, element_id, content)
            elif operation_type == "replace_image":
                return await self._execute_replace_image(presentation, slide_index, element_id, content)
            elif operation_type == "adjust_element_position":
                return await self._execute_adjust_position(presentation, slide_index, element_id, content)
            elif operation_type == "delete_element":
                return await self._execute_delete_element(presentation, slide_index, element_id)
            else:
                error_msg = f"不支持的操作类型: {operation_type}"
                self.logger.warning(error_msg)
                return {"success": False, "message": error_msg}
                
        except Exception as e:
            error_msg = f"执行操作 {operation_type} 时出错: {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "message": error_msg}
    
    async def execute_batch_operations(self, presentation: Any, slide_index: int, 
                                     operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量执行PPT操作
        
        Args:
            presentation: PPT演示文稿对象
            slide_index: 幻灯片索引
            operations: 操作指令列表
            
        Returns:
            批量操作结果，包含成功率、详细结果等信息
        """
        if not operations:
            self.logger.warning("没有操作指令可执行")
            return {
                "success": False,
                "message": "没有操作指令可执行",
                "total_count": 0,
                "success_count": 0,
                "success_rate": 0.0,
                "results": []
            }
        
        success_count = 0
        total_count = len(operations)
        operation_results = []
        
        for i, operation in enumerate(operations):
            # 验证操作有效性
            if not self._validate_operation(operation):
                operation_results.append({
                    "index": i,
                    "operation": operation,
                    "success": False,
                    "message": "操作验证失败"
                })
                continue
                
            try:
                # 执行单个操作
                result = await self.execute_single_operation(presentation, slide_index, operation)
                operation_results.append({
                    "index": i,
                    "operation": operation,
                    "success": result.get("success", False),
                    "message": result.get("message", "")
                })
                
                if result.get("success"):
                    success_count += 1
                    self.logger.info(f"成功执行操作 {operation.get('operation')} 于元素 {operation.get('element_id')}")
                else:
                    self.logger.warning(f"执行操作 {operation.get('operation')} 失败: {result.get('message')}")
            
            except Exception as e:
                error_msg = f"执行操作时出错: {str(e)}"
                self.logger.warning(error_msg)
                operation_results.append({
                    "index": i,
                    "operation": operation,
                    "success": False,
                    "message": error_msg
                })
        
        # 计算成功率
        success_rate = success_count / total_count if total_count > 0 else 0
        self.logger.info(f"[{self.agent_name}] 操作执行完成，成功率: {success_rate:.2%} ({success_count}/{total_count})")
        
        return {
            "success": success_count > 0,
            "message": f"成功执行 {success_count}/{total_count} 个操作",
            "total_count": total_count,
            "success_count": success_count,
            "success_rate": success_rate,
            "results": operation_results
        }
    
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
            self.logger.warning(f"跳过缺少element_id的操作: {operation}")
            return False
        return True
    
    async def _execute_update_content(self, presentation: Any, slide_index: int, 
                                    element_id: str, content: Any) -> Dict[str, Any]:
        """执行文本内容更新操作"""
        return self.ppt_manager.update_element_content(
            presentation=presentation,
            slide_index=slide_index,
            element_id=element_id,
            new_content=str(content).strip()
        )
    
    async def _execute_adjust_font_size(self, presentation: Any, slide_index: int,
                                      element_id: str, content: Any) -> Dict[str, Any]:
        """执行字体大小调整操作"""
        try:
            font_size = int(content)
            return self.ppt_manager.adjust_text_font_size(
                presentation=presentation,
                slide_index=slide_index,
                element_id=element_id,
                font_size=font_size
            )
        except (ValueError, TypeError) as e:
            return {"success": False, "message": f"无效的字体大小值: {content}"}
    
    async def _execute_replace_image(self, presentation: Any, slide_index: int,
                                   element_id: str, content: Any) -> Dict[str, Any]:
        """执行图片替换操作"""
        return self.ppt_manager.replace_image(
            presentation=presentation,
            slide_index=slide_index,
            element_id=element_id,
            image_path=content
        )
    
    async def _execute_adjust_position(self, presentation: Any, slide_index: int,
                                     element_id: str, content: Any) -> Dict[str, Any]:
        """执行元素位置调整操作"""
        if not isinstance(content, dict):
            return {"success": False, "message": "位置调整参数必须是字典格式"}
        
        return self.ppt_manager.adjust_element_position(
            presentation=presentation,
            slide_index=slide_index,
            element_id=element_id,
            left=content.get("left"),
            top=content.get("top"),
            width=content.get("width"),
            height=content.get("height")
        )
    
    async def _execute_delete_element(self, presentation: Any, slide_index: int,
                                    element_id: str) -> Dict[str, Any]:
        """执行元素删除操作"""
        return self.ppt_manager.delete_element(
            presentation=presentation,
            slide_index=slide_index,
            element_id=element_id
        )


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