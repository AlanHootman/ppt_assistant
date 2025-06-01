from apps.api.celery_app import celery_app
from apps.api.services.redis_service import RedisService
from core.agents.ppt_analysis_agent import PPTAnalysisAgent
from apps.api.services.file_service import FileService
from core.engine.state import AgentState
from core.engine.cache_manager import CacheManager
from config.settings import settings
from pathlib import Path
import asyncio
import json
import os
from datetime import datetime
import logging
from apps.api.models.database import Template
from apps.api.models import SessionLocal
import time
from typing import Dict, Any, Optional, List, Tuple

# 导入MLflow跟踪功能
try:
    import mlflow
    from core.monitoring import MLflowTracker
    HAS_MLFLOW = True
except ImportError:
    HAS_MLFLOW = False

logger = logging.getLogger(__name__)


class TemplateStatusManager:
    """模板状态管理器 - 统一处理Redis和数据库的数据同步"""
    
    def __init__(self, task_id: str, template_id: int, redis_service: RedisService):
        self.task_id = task_id
        self.template_id = template_id
        self.redis_service = redis_service
        
    def update_task_status(self, status_data: Dict[str, Any]) -> None:
        """更新任务状态（仅Redis）"""
        self.redis_service.update_task_status(self.task_id, **status_data)
        
        # 发送WebSocket通知
        websocket_data = {"task_id": self.task_id, **status_data}
        self.redis_service.publish_task_update(self.task_id, websocket_data)
        
    def update_template_status(self, status: str, analysis_path: str = None, 
                             analysis_time: datetime = None, preview_path: str = None, 
                             error_message: str = None) -> None:
        """更新数据库中的模板状态"""
        try:
            with SessionLocal() as db:
                template = db.query(Template).filter(Template.id == self.template_id).first()
                if not template:
                    logger.error(f"数据库中未找到模板记录: template_id={self.template_id}")
                    return
                
                # 更新状态
                template.status = status
                if analysis_path:
                    template.analysis_path = analysis_path
                if analysis_time:
                    template.analysis_time = analysis_time
                if preview_path:
                    template.preview_path = preview_path
                if error_message:
                    template.error_message = error_message
                elif status == "ready":
                    template.error_message = None
                
                db.commit()
                logger.info(f"已更新模板状态: template_id={self.template_id}, status={status}")
                
        except Exception as e:
            logger.error(f"更新模板状态失败: template_id={self.template_id}, error={str(e)}")
            
    def clear_task_association(self, is_success: bool = True) -> None:
        """清理Redis中的任务ID关联"""
        try:
            self.redis_service.clear_template_analysis_task_id(self.template_id)
            status_msg = "成功" if is_success else "失败"
            logger.info(f"已清理模板分析任务ID关联({status_msg}): template_id={self.template_id}, task_id={self.task_id}")
        except Exception as e:
            logger.warning(f"清理任务关联失败: {str(e)}")


def _check_template_existence_and_status(template_id: int, task_id: str) -> Tuple[Optional[Template], Optional[Dict[str, Any]]]:
    """检查模板存在性和当前状态"""
    with SessionLocal() as db:
        try:
            template = db.query(Template).filter(Template.id == template_id).first()
            if not template:
                error_msg = f"模板不存在: template_id={template_id}"
                logger.error(error_msg)
                return None, {
                    "template_id": template_id,
                    "status": "failed",
                    "error": {
                        "has_error": True,
                        "error_code": "TEMPLATE_NOT_FOUND",
                        "error_message": error_msg,
                        "can_retry": False
                    }
                }
            
            return template, None
            
        except Exception as e:
            logger.error(f"检查模板状态失败: template_id={template_id}, error={str(e)}")
            return None, {
                "template_id": template_id,
                "status": "failed",
                "error": {
                    "has_error": True,
                    "error_code": "STATUS_CHECK_ERROR",
                    "error_message": str(e),
                    "can_retry": True
                }
            }


def _handle_completed_template(template: Template, template_id: int) -> Optional[Dict[str, Any]]:
    """处理已完成分析的模板"""
    if template.status == "ready" and template.analysis_path:
        logger.info(f"模板已完成分析，跳过重复分析: template_id={template_id}, status={template.status}")
        return {
            "template_id": template_id,
            "status": "completed",
            "message": "模板分析已完成",
            "analysis_file_path": template.analysis_path,
            "preview_images": []
        }
    return None


def _handle_analyzing_template(template: Template, template_id: int, task_id: str, 
                             redis_service: RedisService) -> Optional[Dict[str, Any]]:
    """处理正在分析中的模板"""
    if template.status == "analyzing":
        existing_task_id = redis_service.get_template_analysis_task_id(template_id)
        if existing_task_id and existing_task_id != task_id:
            existing_task_status = redis_service.get_task_status(existing_task_id)
            if existing_task_status and existing_task_status.get("status") == "analyzing":
                logger.warning(f"模板正在分析中，跳过重复任务: template_id={template_id}, existing_task_id={existing_task_id}, current_task_id={task_id}")
                return {
                    "template_id": template_id,
                    "status": "analyzing",
                    "message": f"模板正在分析中，任务ID: {existing_task_id}",
                    "existing_task_id": existing_task_id
                }
    return None


def _set_template_analyzing_status(template: Template, template_id: int, task_id: str) -> None:
    """设置模板为分析中状态"""
    with SessionLocal() as db:
        try:
            # 重新查询模板以获取最新状态
            template = db.query(Template).filter(Template.id == template_id).first()
            if template:
                template.status = "analyzing"
                db.commit()
                logger.info(f"开始分析模板: template_id={template_id}, task_id={task_id}")
        except Exception as e:
            logger.error(f"设置模板分析状态失败: template_id={template_id}, error={str(e)}")
            db.rollback()
            raise


def _initialize_mlflow_tracking(template_data: Dict[str, Any], task_id: str) -> Tuple[Optional[Any], bool]:
    """初始化MLflow跟踪器"""
    tracker = None
    enable_tracking = template_data.get("enable_tracking", False) and HAS_MLFLOW
    
    if enable_tracking:
        try:
            experiment_name = "ppt_template_analysis"
            tracker = MLflowTracker(experiment_name=experiment_name)
            logger.info(f"已启用MLflow模板分析跟踪: {experiment_name}")
            tracker.start_workflow_run(task_id, "template_analysis")
        except Exception as e:
            logger.error(f"初始化MLflow跟踪器失败: {str(e)}")
            enable_tracking = False
    
    return tracker, enable_tracking


def _create_progress_callback(task_id: str, status_manager: TemplateStatusManager, 
                            tracker: Optional[Any], enable_tracking: bool):
    """创建进度回调函数"""
    def progress_callback(step: str, progress: int, description: str, preview_data: dict = None):
        # 更新Redis任务状态
        status_manager.update_task_status({
            "status": "analyzing",
            "progress": progress,
            "message": description,
            "current_step": step,
            "preview_data": preview_data
        })
        
        # 记录进度到MLflow
        if enable_tracking and tracker and HAS_MLFLOW:
            try:
                mlflow.log_metric("progress", progress)
                
                current_step = f"{step}_{progress}"
                with mlflow.start_run(run_name=current_step, nested=True):
                    mlflow.log_param("step_name", step)
                    mlflow.log_param("step_description", description)
                    mlflow.log_metric("step_progress", progress)
                    
                    if preview_data:
                        try:
                            preview_summary = json.dumps(preview_data)
                            mlflow.log_text(preview_summary, f"preview_{step}_{progress}.json")
                        except:
                            pass
            except Exception as e:
                logger.warning(f"记录进度到MLflow失败: {str(e)}")
    
    return progress_callback


def _execute_template_analysis(template_data: Dict[str, Any], task_id: str, 
                             progress_callback) -> AgentState:
    """执行模板分析"""
    # 创建分析Agent
    agent = PPTAnalysisAgent({
        "enable_tracking": False  # Agent层面的跟踪在上层处理
    })
    
    # 创建状态对象
    state = AgentState(session_id=task_id)
    state.ppt_template_path = template_data["file_path"]
    
    # 设置进度回调
    agent.node_executor.set_progress_callback(progress_callback)
    
    # 执行分析
    return asyncio.run(agent.run(state, progress_callback=progress_callback))


def _save_analysis_results(template_data: Dict[str, Any], analysis_result: Dict[str, Any]) -> str:
    """保存分析结果到缓存"""
    cache_manager = CacheManager()
    ppt_path = Path(template_data["file_path"])
    return cache_manager.save_ppt_analysis_cache(str(ppt_path), analysis_result)


def _log_mlflow_results(analysis_result: Dict[str, Any], template_data: Dict[str, Any], 
                       task_id: str, cache_path: str, tracker: Optional[Any], 
                       enable_tracking: bool) -> None:
    """记录分析结果到MLflow"""
    if not (enable_tracking and tracker and HAS_MLFLOW):
        return
        
    try:
        # 记录关键结果指标
        mlflow.log_param("template_name", analysis_result.get("templateName", "未知"))
        mlflow.log_param("slide_count", len(analysis_result.get("slides", [])))
        mlflow.log_param("template_id", template_data.get("template_id", 0))
        mlflow.log_param("template_path", template_data["file_path"])
        mlflow.log_param("cache_path", str(cache_path))
        
        # 记录分析结果摘要
        try:
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


def _complete_analysis_task(template_data: Dict[str, Any], analysis_result: Dict[str, Any], 
                          cache_path: str, task_id: str, status_manager: TemplateStatusManager,
                          tracker: Optional[Any], enable_tracking: bool) -> Dict[str, Any]:
    """完成分析任务"""
    # 生成预览图
    preview_images = generate_template_previews(
        template_data["file_path"],
        template_data["template_id"],
        analysis_result
    )
    
    # 更新任务完成状态
    status_manager.update_task_status({
        "status": "completed",
        "progress": 100,
        "message": "模板分析完成",
        "analysis_file_path": str(cache_path),
        "preview_images": preview_images,
        "completed_at": datetime.utcnow().isoformat()
    })
    
    # 更新数据库中的模板状态
    status_manager.update_template_status(
        status="ready",
        analysis_path=str(cache_path),
        analysis_time=datetime.utcnow(),
        preview_path=preview_images[0] if preview_images else None
    )
    
    # 清理任务关联
    status_manager.clear_task_association(is_success=True)
    
    # 结束MLflow跟踪
    if enable_tracking and tracker:
        tracker.end_workflow_run("FINISHED")
    
    return {
        "analysis_result": analysis_result,
        "analysis_file_path": str(cache_path),
        "preview_images": preview_images,
        "template_id": template_data['template_id']
    }


def _handle_analysis_exception(e: Exception, template_data: Dict[str, Any], task_id: str,
                             status_manager: TemplateStatusManager, tracker: Optional[Any],
                             enable_tracking: bool) -> Dict[str, Any]:
    """处理分析异常"""
    logger.exception(f"模板分析任务失败: {str(e)}")
    
    error_data = {
        "status": "failed",
        "error": {
            "has_error": True,
            "error_code": "ANALYSIS_ERROR",
            "error_message": str(e),
            "can_retry": True
        }
    }
    
    # 更新任务状态
    status_manager.update_task_status(error_data)
    
    # 更新数据库模板状态
    status_manager.update_template_status(status="failed", error_message=str(e))
    
    # 清理任务关联
    status_manager.clear_task_association(is_success=False)
    
    # 记录失败到MLflow
    if enable_tracking and tracker and HAS_MLFLOW:
        try:
            mlflow.log_param("error_message", str(e))
            tracker.end_workflow_run("FAILED")
        except Exception as log_error:
            logger.warning(f"记录失败到MLflow失败: {str(log_error)}")
    
    return {
        "template_id": template_data.get("template_id"),
        **error_data
    }


@celery_app.task(bind=True, autoretry_for=(), max_retries=0, default_retry_delay=0)
def analyze_template_task(self, template_data: dict):
    """
    模板分析异步任务
    
    Args:
        template_data: 包含template_id, file_path等信息
    """
    task_id = self.request.id
    template_id = template_data.get("template_id")
    
    # 初始化服务
    redis_service = RedisService()
    status_manager = TemplateStatusManager(task_id, template_id, redis_service)
    
    # 保存任务ID与模板ID的关联
    if template_id:
        redis_service.save_template_analysis_task_id(template_id, task_id)
    
    try:
        # 1. 检查模板存在性和状态
        template, error_response = _check_template_existence_and_status(template_id, task_id)
        if error_response:
            return error_response
        
        # 2. 处理已完成的模板
        completed_response = _handle_completed_template(template, template_id)
        if completed_response:
            return completed_response
        
        # 3. 处理正在分析中的模板
        analyzing_response = _handle_analyzing_template(template, template_id, task_id, redis_service)
        if analyzing_response:
            return analyzing_response
        
        # 4. 设置模板为分析中状态
        _set_template_analyzing_status(template, template_id, task_id)
        
        # 5. 初始化MLflow跟踪
        tracker, enable_tracking = _initialize_mlflow_tracking(template_data, task_id)
        
        # 6. 开始分析任务
        status_manager.update_task_status({
            "status": "analyzing",
            "progress": 10,
            "message": "开始分析PPT模板"
        })
        
        # 7. 创建进度回调
        progress_callback = _create_progress_callback(task_id, status_manager, tracker, enable_tracking)
        
        # 8. 执行模板分析
        updated_state = _execute_template_analysis(template_data, task_id, progress_callback)
        
        # 9. 获取和保存分析结果
        analysis_result = updated_state.layout_features
        cache_path = _save_analysis_results(template_data, analysis_result)
        
        # 10. 记录结果到MLflow
        _log_mlflow_results(analysis_result, template_data, task_id, cache_path, tracker, enable_tracking)
        
        # 11. 完成任务
        return _complete_analysis_task(template_data, analysis_result, cache_path, task_id, 
                                     status_manager, tracker, enable_tracking)
        
    except Exception as e:
        # 统一异常处理
        return _handle_analysis_exception(e, template_data, task_id, status_manager, tracker if 'tracker' in locals() else None, enable_tracking if 'enable_tracking' in locals() else False)


def generate_template_previews(template_path: str, template_id: int, analysis_result: dict = None) -> List[str]:
    """生成模板预览图，将渲染好的PPT图片移动到对应template_id目录下
    
    Args:
        template_path: 模板文件路径
        template_id: 模板ID
        analysis_result: 分析结果，包含slideImages字段
        
    Returns:
        预览图URL列表
    """
    import shutil
    
    # 如果没有分析结果或者不包含slideImages，返回空列表
    if not analysis_result or "slideImages" not in analysis_result:
        logger.warning(f"没有找到PPT渲染图片数据，template_id={template_id}")
        return []
    
    # 获取图片路径列表
    slide_images = analysis_result.get("slideImages", [])
    if not slide_images:
        logger.warning(f"PPT渲染图片列表为空，template_id={template_id}")
        return []
    
    # 确保目标目录存在
    target_dir = Path(settings.WORKSPACE_DIR) / "cache" / "ppt_analysis" / str(template_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # 存储新的图片路径
    new_image_paths = []
    
    # 处理每个图片
    for i, image_path in enumerate(slide_images):
        if not image_path or not os.path.exists(image_path):
            logger.warning(f"图片路径不存在: {image_path}")
            continue
        
        # 构建新的文件名和路径
        image_filename = f"slide_{i+1}.png"
        target_path = target_dir / image_filename
        
        try:
            # 移动图片文件
            shutil.copy2(image_path, target_path)
            
            # 记录新路径
            new_path = f"/workspace/cache/ppt_analysis/{template_id}/{image_filename}"
            new_image_paths.append(new_path)
            
            # 删除原文件
            os.remove(image_path)
            logger.info(f"已移动并删除原图片: {image_path} -> {target_path}")
        except Exception as e:
            logger.error(f"移动图片时出错: {str(e)}")
    
    return new_image_paths