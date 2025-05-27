from apps.api.celery_app import celery_app
from apps.api.services.redis_service import RedisService
from core.agents.ppt_analysis_agent import PPTAnalysisAgent
from apps.api.services.file_service import FileService
from core.engine.state import AgentState
import asyncio
import json
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def analyze_template_task(self, template_data: dict):
    """
    模板分析异步任务
    
    Args:
        template_data: 包含template_id, file_path等信息
    """
    task_id = self.request.id
    redis_service = RedisService()
    file_service = FileService()
    
    try:
        # 更新任务状态
        redis_service.update_task_status(
            task_id,
            status="analyzing",
            progress=10,
            message="开始分析PPT模板"
        )
        
        # 创建分析Agent
        agent = PPTAnalysisAgent({})
        
        # 进度回调函数
        def progress_callback(progress: int, message: str):
            redis_service.update_task_status(
                task_id, 
                progress=progress, 
                message=message
            )
            
            # 发送WebSocket消息
            redis_service.publish_task_update(task_id, {
                "status": "analyzing",
                "progress": progress,
                "message": message
            })
        
        # 创建一个状态对象并设置必要的属性
        state = AgentState(session_id=task_id)
        state.ppt_template_path = template_data["file_path"]
        
        # 执行模板分析
        updated_state = asyncio.run(agent.run(state))
        
        # 获取分析结果
        analysis_result = updated_state.layout_features
        
        # 获取模板目录
        template_dir = os.path.join(file_service.templates_dir, str(template_data['template_id']))
        os.makedirs(template_dir, exist_ok=True)
        
        # 保存分析结果
        analysis_file_path = os.path.join(template_dir, "analysis.json")
        with open(analysis_file_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, ensure_ascii=False, indent=2)
        
        # 生成预览图
        preview_images = generate_template_previews(template_data["file_path"], template_data["template_id"])
        
        # 更新完成状态
        redis_service.update_task_status(
            task_id,
            status="completed",
            progress=100,
            message="模板分析完成",
            analysis_file_path=analysis_file_path,
            preview_images=preview_images,
            completed_at=datetime.utcnow().isoformat()
        )
        
        return {
            "analysis_result": analysis_result,
            "analysis_file_path": analysis_file_path,
            "preview_images": preview_images,
            "template_id": template_data['template_id']
        }
        
    except Exception as e:
        logger.exception(f"模板分析任务失败: {str(e)}")
        
        # 错误处理
        error_data = {
            "status": "failed",
            "error": {
                "has_error": True,
                "error_code": "ANALYSIS_ERROR",
                "error_message": str(e),
                "can_retry": True
            }
        }
        
        redis_service.update_task_status(task_id, **error_data)
        redis_service.publish_task_update(task_id, error_data)
        
        raise self.retry(countdown=30, max_retries=2)

def generate_template_previews(template_path: str, template_id: int) -> list:
    """生成模板预览图
    
    Args:
        template_path: 模板文件路径
        template_id: 模板ID
        
    Returns:
        预览图URL列表
    """
    # TODO: 实现PPT转图片的逻辑
    # 这里简单返回一个模拟预览图列表
    return [f"/static/templates/{template_id}/preview_{i}.png" for i in range(3)] 