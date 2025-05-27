from apps.api.celery_app import celery_app
from apps.api.services.redis_service import RedisService
from core.agents.ppt_analysis_agent import PPTAnalysisAgent
from apps.api.services.file_service import FileService
from core.engine.state import AgentState
from core.engine.cache_manager import CacheManager
from pathlib import Path
import asyncio
import json
import os
from datetime import datetime
import logging

# 导入MLflow跟踪功能
try:
    import mlflow
    from core.monitoring import MLflowTracker
    HAS_MLFLOW = True
except ImportError:
    HAS_MLFLOW = False

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
    cache_manager = CacheManager()
    
    # 初始化MLflow跟踪器
    tracker = None
    enable_tracking = template_data.get("enable_tracking", False) and HAS_MLFLOW
    
    if enable_tracking:
        try:
            experiment_name = "ppt_template_analysis"
            tracker = MLflowTracker(experiment_name=experiment_name)
            logger.info(f"已启用MLflow模板分析跟踪: {experiment_name}")
            # 开始跟踪会话
            tracker.start_workflow_run(task_id, "template_analysis")
        except Exception as e:
            logger.error(f"初始化MLflow跟踪器失败: {str(e)}")
            enable_tracking = False
    
    try:
        # 更新任务状态
        redis_service.update_task_status(
            task_id,
            status="analyzing",
            progress=10,
            message="开始分析PPT模板"
        )
        
        # 创建分析Agent
        agent = PPTAnalysisAgent({
            # 将跟踪器信息传递给Agent，尽管Agent目前可能不直接使用
            "enable_tracking": enable_tracking
        })
        
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
            
            # 记录进度到MLflow
            if enable_tracking and tracker and HAS_MLFLOW:
                try:
                    mlflow.log_metric(f"progress", progress)
                    mlflow.log_param(f"status_message", message)
                except Exception as e:
                    logger.warning(f"记录进度到MLflow失败: {str(e)}")
        
        # 创建一个状态对象并设置必要的属性
        state = AgentState(session_id=task_id)
        state.ppt_template_path = template_data["file_path"]
        
        # 执行模板分析
        updated_state = asyncio.run(agent.run(state))
        
        # 获取分析结果
        analysis_result = updated_state.layout_features
        
        # 保存分析结果到缓存系统
        ppt_path = Path(template_data["file_path"])
        template_id = template_data.get("template_id")
        cache_path = cache_manager.save_ppt_analysis_cache(str(ppt_path), analysis_result, template_id=template_id)
        
        # 记录分析结果到MLflow
        if enable_tracking and tracker and HAS_MLFLOW:
            try:
                # 记录关键结果指标
                mlflow.log_param("template_name", analysis_result.get("templateName", "未知"))
                mlflow.log_param("slide_count", len(analysis_result.get("slides", [])))
                mlflow.log_param("template_id", template_data.get("template_id", 0))
                mlflow.log_param("template_path", template_data["file_path"])
                
                # 记录缓存路径
                mlflow.log_param("cache_path", str(cache_path))
                
                # 尝试记录分析结果摘要
                try:
                    # 创建一个摘要文件记录关键信息
                    summary_path = f"/tmp/template_analysis_{task_id}_summary.json"
                    with open(summary_path, "w") as f:
                        json.dump({
                            "templateName": analysis_result.get("templateName", "未知"),
                            "slideCount": len(analysis_result.get("slides", [])),
                            "layouts": [slide.get("layoutName", "未知") for slide in analysis_result.get("slides", [])],
                            "themeColors": analysis_result.get("themeColors", []),
                            "fontFamilies": analysis_result.get("fontFamilies", [])
                        }, f, indent=2)
                    mlflow.log_artifact(summary_path, "analysis_summary")
                    os.remove(summary_path)
                except Exception as e:
                    logger.warning(f"记录分析结果摘要到MLflow失败: {str(e)}")
            except Exception as e:
                logger.warning(f"记录分析结果到MLflow失败: {str(e)}")
        
        # 生成预览图
        preview_images = generate_template_previews(template_data["file_path"], template_data["template_id"])
        
        # 更新完成状态
        redis_service.update_task_status(
            task_id,
            status="completed",
            progress=100,
            message="模板分析完成",
            analysis_file_path=str(cache_path),
            preview_images=preview_images,
            completed_at=datetime.utcnow().isoformat()
        )
        
        # 结束MLflow跟踪
        if enable_tracking and tracker:
            tracker.end_workflow_run("completed")
        
        return {
            "analysis_result": analysis_result,
            "analysis_file_path": str(cache_path),
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
        
        # 记录失败到MLflow
        if enable_tracking and tracker and HAS_MLFLOW:
            try:
                mlflow.log_param("error_message", str(e))
                tracker.end_workflow_run("failed")
            except Exception as log_error:
                logger.warning(f"记录失败到MLflow失败: {str(log_error)}")
        
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
    return [f"/workspace/cache/ppt_analysis/{template_id}/preview_{i}.png" for i in range(3)] 