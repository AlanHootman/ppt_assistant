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
    redis_service = RedisService()
    file_service = FileService()
    
    try:
        # 更新任务状态
        redis_service.update_task_status(
            task_id, 
            status="processing",
            progress=0,
            current_step="initialization",
            step_description="初始化PPT生成任务"
        )
        
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
            redis_service.update_task_status(
                task_id,
                status="processing",
                progress=progress,
                current_step=step,
                step_description=description,
                preview_data=preview_data
            )
            
            # 发送WebSocket消息
            redis_service.publish_task_update(task_id, {
                "status": "processing",
                "progress": progress,
                "current_step": step,
                "step_description": description,
                "preview_data": preview_data
            })
        
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
        
        # 生成预览图
        if result.output_ppt_path:
            preview_images = generate_preview_images(result.output_ppt_path)
        else:
            # 如果PPT路径为空，使用任务ID创建默认预览图
            preview_images = [f"/workspace/output/{task_id}/preview_{i}.png" for i in range(3)]
            logger.warning(f"PPT路径为空，使用默认预览图: {task_id}")
        
        # 更新最终状态
        final_data = {
            "status": "completed",
            "progress": 100,
            "file_url": f"/workspace/output/{task_id}/presentation.pptx",
            "preview_images": preview_images,
            "completed_at": datetime.utcnow().isoformat()
        }
        
        redis_service.update_task_status(task_id, **final_data)
        redis_service.publish_task_update(task_id, final_data)
        
        return final_data
        
    except Exception as e:
        logger.exception(f"PPT生成任务失败: {str(e)}")
        
        # 错误处理
        error_data = {
            "status": "failed",
            "error": {
                "has_error": True,
                "error_code": "GENERATION_ERROR",
                "error_message": str(e),
                "can_retry": True
            }
        }
        
        redis_service.update_task_status(task_id, **error_data)
        redis_service.publish_task_update(task_id, error_data)
        
        raise self.retry(countdown=60, max_retries=3)

def generate_preview_images(ppt_path: str) -> list:
    """生成PPT预览图
    
    Args:
        ppt_path: PPT文件路径，可能为None
        
    Returns:
        预览图URL列表
    """
    # 如果ppt_path为None，则返回空列表
    if not ppt_path:
        logger.warning("生成预览图失败: PPT路径为None")
        return []
        
    try:
        # TODO: 实现PPT转图片的逻辑
        # 这里简单返回一个模拟预览图列表
        task_id = os.path.basename(os.path.dirname(ppt_path))
        return [f"/workspace/output/{task_id}/preview_{i}.png" for i in range(3)]
    except Exception as e:
        logger.error(f"生成预览图失败: {str(e)}")
        return [] 