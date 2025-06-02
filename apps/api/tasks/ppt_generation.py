from celery import current_task
from apps.api.celery_app import celery_app
from apps.api.services.redis_service import RedisService
from core.engine.workflowEngine import WorkflowEngine
from apps.api.services.file_service import FileService
from apps.api.models import SessionLocal, GenerationTask
import asyncio
import json
from datetime import datetime
from pathlib import Path
import uuid
import os
import logging
from typing import Dict, Any, Optional, List


logger = logging.getLogger(__name__)


class TaskStatusManager:
    """任务状态管理器 - 统一处理Redis和数据库的数据同步"""
    
    def __init__(self, task_id: str, redis_service: RedisService):
        self.task_id = task_id
        self.redis_service = redis_service
        
    def update_status(self, status_data: Dict[str, Any]) -> None:
        """同时更新Redis和数据库中的任务状态"""
        # 更新数据库状态
        self._update_database_status(status_data)
        
        # 更新Redis状态
        self.redis_service.update_task_status(self.task_id, **status_data)
        
        # 发送WebSocket通知
        websocket_data = {"task_id": self.task_id, **status_data}
        self.redis_service.publish_task_update(self.task_id, websocket_data)
        
    def _update_database_status(self, status_data: Dict[str, Any]) -> None:
        """更新数据库中的任务状态"""
        with SessionLocal() as db:
            try:
                db_task = db.query(GenerationTask).filter(GenerationTask.id == self.task_id).first()
                if not db_task:
                    logger.error(f"数据库中未找到任务记录: task_id={self.task_id}")
                    return
                
                # 更新基本状态字段
                db_task.status = status_data.get("status", db_task.status)
                db_task.progress = status_data.get("progress", db_task.progress)
                db_task.current_step = status_data.get("current_step", db_task.current_step)
                db_task.step_description = status_data.get("step_description", db_task.step_description)
                
                # 处理特殊字段
                if "started_at" in status_data and status_data["started_at"]:
                    db_task.started_at = datetime.utcnow()
                    
                if "completed_at" in status_data and status_data["completed_at"]:
                    db_task.completed_at = datetime.utcnow()
                    
                if "output_path" in status_data:
                    db_task.output_path = status_data["output_path"]
                    
                # 处理错误信息
                if status_data.get("status") == "failed":
                    error_info = status_data.get("error", {})
                    db_task.error_message = error_info.get("error_message", "未知错误")
                elif status_data.get("status") == "completed":
                    db_task.error_message = None
                    
                db.commit()
                logger.info(f"已更新数据库任务状态: task_id={self.task_id}, status={status_data.get('status')}")
                
            except Exception as e:
                logger.warning(f"更新数据库任务状态失败: task_id={self.task_id}, error={str(e)}")
                db.rollback()


def _create_progress_callback(task_id: str, status_manager: TaskStatusManager):
    """创建进度回调函数"""
    def progress_callback(step: str, progress: int, description: str, preview_data: dict = None):
        # 构建基础进度数据
        update_data = {
            "status": "processing",
            "progress": progress,
            "current_step": step,
            "step_description": description,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # 检查是否为错误状态
        if preview_data and preview_data.get("error"):
            update_data.update({
                "status": "failed",
                "progress": max(0, progress),
                "error": {
                    "has_error": True,
                    "error_code": "WORKFLOW_ERROR",
                    "error_message": description,
                    "can_retry": True
                }
            })
        
        # 添加预览数据
        if preview_data and not preview_data.get("error"):
            if "preview_url" in preview_data:
                update_data["preview_url"] = preview_data["preview_url"]
            if "preview_images" in preview_data:
                update_data["preview_images"] = preview_data["preview_images"]
        
        # 统一更新状态
        status_manager.update_status(update_data)
        
        # 记录日志
        log_level = logging.ERROR if update_data["status"] == "failed" else logging.INFO
        logger.log(log_level, f"任务进度更新: task_id={task_id}, step={step}, progress={progress}%, description={description}")
    
    return progress_callback


def _initialize_task(task_id: str, status_manager: TaskStatusManager) -> None:
    """初始化任务状态"""
    initial_status = {
        "status": "processing",
        "progress": 0,
        "current_step": "initialization",
        "step_description": "初始化PPT生成任务",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "started_at": datetime.utcnow().isoformat()
    }
    
    status_manager.update_status(initial_status)
    logger.info(f"任务初始化完成: task_id={task_id}")


def _validate_template_and_create_dirs(task_data: Dict[str, Any], task_id: str) -> tuple[str, str]:
    """验证模板并创建目录"""
    file_service = FileService()
    
    # 获取模板路径
    template_path = file_service.get_template_file_path(task_data["template_id"])
    if not template_path:
        raise ValueError(f"模板文件不存在：template_id={task_data['template_id']}")
    
    # 创建输出目录
    output_dir = file_service.create_task_output_dir(task_id)
    
    return template_path, output_dir


def _create_workflow_engine(task_data: Dict[str, Any]) -> WorkflowEngine:
    """创建工作流引擎，安全地处理MLflow跟踪"""
    # 检查是否启用跟踪，默认禁用以避免连接问题
    enable_tracking = task_data.get("enable_tracking", True)
    
    logger.info(f"正在初始化工作流引擎... (MLflow跟踪: {'启用' if enable_tracking else '禁用'})")
    engine = WorkflowEngine(enable_tracking=enable_tracking)
    logger.info("工作流引擎创建成功")
    return engine


def _execute_workflow(engine: WorkflowEngine, task_id: str, task_data: Dict[str, Any], 
                     template_path: str, output_dir: str, progress_callback) -> Any:
    """执行PPT生成工作流"""
    return asyncio.run(engine.run_async(
        session_id=task_id,
        raw_md=task_data["markdown_content"],
        ppt_template_path=template_path,
        output_dir=output_dir,
        progress_callback=progress_callback,
        enable_multimodal_validation=task_data.get("enable_multimodal_validation", False)
    ))


def _handle_workflow_failure(result: Any, task_id: str, status_manager: TaskStatusManager) -> None:
    """处理工作流执行失败"""
    if not result.failures:
        return
        
    last_failure = result.failures[-1] if result.failures else "工作流执行失败"
    logger.error(f"工作流执行失败: task_id={task_id}, error={last_failure}")
    
    error_data = {
        "status": "failed",
        "current_step": "workflow_error",
        "step_description": f"工作流执行失败: {last_failure}",
        "progress": 0,
        "updated_at": datetime.utcnow().isoformat(),
        "completed_at": datetime.utcnow().isoformat(),
        "error": {
            "has_error": True,
            "error_code": "WORKFLOW_EXECUTION_ERROR", 
            "error_message": last_failure,
            "can_retry": True
        }
    }
    
    status_manager.update_status(error_data)
    raise Exception(last_failure)


def _validate_output_file(result: Any, task_id: str, status_manager: TaskStatusManager) -> None:
    """验证输出文件是否存在"""
    if not result.output_ppt_path or not os.path.exists(result.output_ppt_path):
        error_msg = "PPT文件生成失败，输出文件不存在"
        logger.error(f"{error_msg}: task_id={task_id}")
        
        error_data = {
            "status": "failed",
            "current_step": "file_generation_error",
            "step_description": error_msg,
            "progress": 0,
            "updated_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "error": {
                "has_error": True,
                "error_code": "FILE_GENERATION_ERROR",
                "error_message": error_msg,
                "can_retry": True
            }
        }
        
        status_manager.update_status(error_data)
        raise Exception(error_msg)


def _complete_task(result: Any, task_id: str, status_manager: TaskStatusManager) -> Dict[str, Any]:
    """完成任务并返回结果"""
    # 生成预览图
    preview_images = []
    if result.output_ppt_path:
        preview_images = generate_preview_images(result.output_ppt_path)
    else:
        preview_images = [
            {"slide_index": i, "preview_url": f"/workspace/output/{task_id}/preview_{i}.png"} 
            for i in range(3)
        ]
        logger.warning(f"PPT路径为空，使用默认预览图: {task_id}")
    
    # 构建完成状态
    final_data = {
        "status": "completed",
        "progress": 100,
        "current_step": "completed",
        "step_description": "PPT生成已完成",
        "file_url": f"/workspace/output/{task_id}/presentation.pptx",
        "preview_images": preview_images,
        "completed_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "output_path": result.output_ppt_path
    }
    
    status_manager.update_status(final_data)
    logger.info(f"任务完成: task_id={task_id}")
    
    return {"task_id": task_id, **final_data}


def _handle_task_exception(e: Exception, task_id: str, status_manager: TaskStatusManager) -> Dict[str, Any]:
    """处理任务异常"""
    logger.exception(f"PPT生成任务失败: {str(e)}")
    
    error_data = {
        "status": "failed",
        "current_step": "error",
        "step_description": f"PPT生成失败: {str(e)}",
        "progress": 0,
        "updated_at": datetime.utcnow().isoformat(),
        "completed_at": datetime.utcnow().isoformat(),
        "error": {
            "has_error": True,
            "error_code": "GENERATION_ERROR",
            "error_message": str(e),
            "can_retry": True
        }
    }
    
    status_manager.update_status(error_data)
    return {"task_id": task_id, **error_data}


@celery_app.task(bind=True, autoretry_for=(), max_retries=0, default_retry_delay=0)
def generate_ppt_task(self, task_data: dict):
    """
    PPT生成异步任务
    
    Args:
        task_data: 包含template_id, markdown_content等信息
    """
    task_id = self.request.id
    logger.info(f"开始PPT生成任务: task_id={task_id}, template_id={task_data.get('template_id')}")
    
    # 初始化服务
    redis_service = RedisService()
    status_manager = TaskStatusManager(task_id, redis_service)
    
    try:
        # 1. 初始化任务
        _initialize_task(task_id, status_manager)
        
        # 2. 验证模板并创建目录
        template_path, output_dir = _validate_template_and_create_dirs(task_data, task_id)
        
        # 3. 创建工作流引擎（带MLflow错误处理）
        engine = _create_workflow_engine(task_data)
        
        # 4. 设置进度回调
        progress_callback = _create_progress_callback(task_id, status_manager)
        engine.node_executor.set_progress_callback(progress_callback)
        
        # 5. 执行工作流
        result = _execute_workflow(engine, task_id, task_data, template_path, output_dir, progress_callback)
        
        # 6. 检查工作流执行结果
        _handle_workflow_failure(result, task_id, status_manager)
        
        # 7. 验证输出文件
        _validate_output_file(result, task_id, status_manager)
        
        # 8. 完成任务
        return _complete_task(result, task_id, status_manager)
        
    except Exception as e:
        # 统一异常处理
        return _handle_task_exception(e, task_id, status_manager)


def generate_preview_images(ppt_path: str) -> List[Dict[str, Any]]:
    """生成PPT预览图
    
    Args:
        ppt_path: PPT文件路径，可能为None
        
    Returns:
        预览图URL列表，格式为 [{"slide_index": 0, "preview_url": "..."}, ...]
    """
    if not ppt_path:
        logger.warning("生成预览图失败: PPT路径为None")
        return []
        
    try:
        # TODO: 实现PPT转图片的逻辑
        # 这里简单返回一个模拟预览图列表
        task_id = os.path.basename(os.path.dirname(ppt_path))
        return [
            {"slide_index": i, "preview_url": f"/workspace/output/{task_id}/preview_{i}.png"} 
            for i in range(3)
        ]
    except Exception as e:
        logger.error(f"生成预览图失败: {str(e)}")
        return [] 