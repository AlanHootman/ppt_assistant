from celery import current_task
from apps.api.celery_app import celery_app
from apps.api.services.redis_service import RedisService
from core.engine.workflowEngine import WorkflowEngine
from apps.api.services.file_service import FileService
import asyncio
import json
from datetime import datetime
from pathlib import Path
import uuid
import os
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def generate_ppt_task(self, task_data: dict):
    """
    PPT生成异步任务
    
    Args:
        task_data: 包含template_id, markdown_content等信息
    """
    task_id = self.request.id
    logger.info(f"开始PPT生成任务: task_id={task_id}, template_id={task_data.get('template_id')}")
    
    redis_service = RedisService()
    file_service = FileService()
    
    try:
        # 准备初始状态数据
        initial_status = {
            "status": "processing",
            "progress": 0,
            "current_step": "initialization",
            "step_description": "初始化PPT生成任务",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # 更新任务状态
        redis_service.update_task_status(task_id, **initial_status)
        
        # 发送WebSocket通知（添加task_id用于WebSocket消息）
        websocket_data = {"task_id": task_id, **initial_status}
        redis_service.publish_task_update(task_id, websocket_data)
        
        # 创建工作流引擎
        engine = WorkflowEngine(enable_tracking=True)
        
        # 获取模板路径
        template_path = file_service.get_template_file_path(task_data["template_id"])
        if not template_path:
            raise ValueError(f"模板文件不存在：template_id={task_data['template_id']}")
        
        # 创建输出目录
        output_dir = file_service.create_task_output_dir(task_id)
        
        # 设置进度回调
        def progress_callback(step: str, progress: int, description: str, preview_data: dict = None):
            # 构建完整的进度数据
            update_data = {
                "status": "processing",
                "progress": progress,
                "current_step": step,
                "step_description": description,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # 检查是否为错误状态
            if preview_data and preview_data.get("error"):
                update_data["status"] = "failed"
                update_data["error"] = {
                    "has_error": True,
                    "error_code": "WORKFLOW_ERROR",
                    "error_message": description,
                    "can_retry": True
                }
                # 错误状态时，进度设为失败时的进度或0
                update_data["progress"] = max(0, progress)
            
            # 如果有其他预览数据，添加到更新数据中
            if preview_data and not preview_data.get("error"):
                if "preview_url" in preview_data:
                    update_data["preview_url"] = preview_data["preview_url"]
                if "preview_images" in preview_data:
                    update_data["preview_images"] = preview_data["preview_images"]
            
            # 更新Redis中的任务状态
            redis_service.update_task_status(task_id, **update_data)
            
            # 通过WebSocket发送更新（添加task_id用于WebSocket消息）
            websocket_data = {"task_id": task_id, **update_data}
            redis_service.publish_task_update(task_id, websocket_data)
            
            # 根据状态类型记录不同级别的日志
            if update_data["status"] == "failed":
                logger.error(f"任务错误: task_id={task_id}, step={step}, description={description}")
            else:
                logger.info(f"任务进度更新: task_id={task_id}, step={step}, progress={progress}%, description={description}")
        
        # 设置进度回调到节点执行器
        engine.node_executor.set_progress_callback(progress_callback)
        
        # 执行PPT生成工作流
        result = asyncio.run(engine.run_async(
            session_id=task_id,
            raw_md=task_data["markdown_content"],
            ppt_template_path=template_path,
            output_dir=output_dir,
            progress_callback=progress_callback
        ))
        
        # 检查工作流执行结果，如果有失败记录，不执行完成逻辑
        if result.failures:
            # 工作流执行失败，获取最后一个错误信息
            last_failure = result.failures[-1] if result.failures else "工作流执行失败"
            logger.error(f"工作流执行失败: task_id={task_id}, error={last_failure}")
            
            # 构建失败状态
            error_data = {
                "status": "failed",
                "current_step": "workflow_error",
                "step_description": f"工作流执行失败: {last_failure}",
                "progress": 0,
                "updated_at": datetime.utcnow().isoformat(),
                "error": {
                    "has_error": True,
                    "error_code": "WORKFLOW_EXECUTION_ERROR", 
                    "error_message": last_failure,
                    "can_retry": True
                }
            }
            
            # 更新Redis状态
            redis_service.update_task_status(task_id, **error_data)
            
            # 发送WebSocket通知
            websocket_data = {"task_id": task_id, **error_data}
            redis_service.publish_task_update(task_id, websocket_data)
            
            # 抛出异常以终止任务
            raise Exception(last_failure)
        
        # 检查是否有必要的输出文件
        if not result.output_ppt_path or not os.path.exists(result.output_ppt_path):
            error_msg = "PPT文件生成失败，输出文件不存在"
            logger.error(f"{error_msg}: task_id={task_id}")
            
            # 构建失败状态
            error_data = {
                "status": "failed",
                "current_step": "file_generation_error",
                "step_description": error_msg,
                "progress": 0,
                "updated_at": datetime.utcnow().isoformat(),
                "error": {
                    "has_error": True,
                    "error_code": "FILE_GENERATION_ERROR",
                    "error_message": error_msg,
                    "can_retry": True
                }
            }
            
            # 更新Redis状态
            redis_service.update_task_status(task_id, **error_data)
            
            # 发送WebSocket通知
            websocket_data = {"task_id": task_id, **error_data}
            redis_service.publish_task_update(task_id, websocket_data)
            
            # 抛出异常以终止任务
            raise Exception(error_msg)
        
        # 生成预览图
        preview_images = []
        if result.output_ppt_path:
            preview_images = generate_preview_images(result.output_ppt_path)
        else:
            # 如果PPT路径为空，使用任务ID创建默认预览图
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
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # 更新Redis状态
        redis_service.update_task_status(task_id, **final_data)
        
        # 发送WebSocket通知（添加task_id用于WebSocket消息）
        websocket_data = {"task_id": task_id, **final_data}
        redis_service.publish_task_update(task_id, websocket_data)
        
        logger.info(f"任务完成: task_id={task_id}")
        
        # 返回结果时也包含task_id
        return {"task_id": task_id, **final_data}
        
    except Exception as e:
        logger.exception(f"PPT生成任务失败: {str(e)}")
        
        # 构建错误数据
        error_data = {
            "status": "failed",
            "current_step": "error",
            "step_description": f"PPT生成失败: {str(e)}",
            "progress": 0,
            "updated_at": datetime.utcnow().isoformat(),
            "error": {
                "has_error": True,
                "error_code": "GENERATION_ERROR",
                "error_message": str(e),
                "can_retry": True
            }
        }
        
        # 更新Redis状态
        redis_service.update_task_status(task_id, **error_data)
        
        # 发送WebSocket通知（添加task_id用于WebSocket消息）
        websocket_data = {"task_id": task_id, **error_data}
        redis_service.publish_task_update(task_id, websocket_data)
        
        # 重试任务
        raise self.retry(countdown=60, max_retries=3)

def generate_preview_images(ppt_path: str) -> list:
    """生成PPT预览图
    
    Args:
        ppt_path: PPT文件路径，可能为None
        
    Returns:
        预览图URL列表，格式为 [{"slide_index": 0, "preview_url": "..."}, ...]
    """
    # 如果ppt_path为None，则返回空列表
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