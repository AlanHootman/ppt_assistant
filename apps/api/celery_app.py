from celery import Celery
from celery.signals import task_postrun, task_failure, task_success, task_retry
from apps.api.config import settings
import logging
import asyncio
import gc

logger = logging.getLogger(__name__)

celery_app = Celery(
    "ppt_assistant",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "apps.api.tasks.ppt_generation",
        "apps.api.tasks.template_analysis"
    ]
)

# Celery配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30分钟超时
    task_soft_time_limit=25 * 60,  # 25分钟软超时
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # 禁用任务重试和重新排队机制
    task_acks_late=False,  # 立即确认任务，不等待完成
    task_reject_on_worker_lost=False,  # worker丢失时不重新排队任务
    task_default_retry_delay=0,  # 禁用默认重试延迟
    task_max_retries=0,  # 全局禁用重试
    task_retry_jitter=False,  # 禁用重试抖动
    worker_disable_rate_limits=True,  # 禁用速率限制重试
    
    # 任务路由配置
    task_routes={
        "apps.api.tasks.ppt_generation.*": {"queue": "ppt_generation"},
        "apps.api.tasks.template_analysis.*": {"queue": "template_analysis"}
    },
    
    # 任务注解配置 - 为所有任务禁用重试
    task_annotations={
        "*": {
            "rate_limit": "10/s",
            "autoretry_for": (),  # 不为任何异常自动重试
            "max_retries": 0,  # 最大重试次数设为0
            "default_retry_delay": 0,  # 重试延迟设为0
        },
        "apps.api.tasks.ppt_generation.generate_ppt_task": {
            "rate_limit": "2/s",
            "autoretry_for": (),  # 不为任何异常自动重试
            "max_retries": 0,  # 最大重试次数设为0
            "default_retry_delay": 0,  # 重试延迟设为0
        },
    }
)

def cleanup_async_resources():
    """
    清理异步资源，特别是AsyncOpenAI客户端
    """
    try:
        logger.debug("开始清理异步资源")
        
        # 导入ModelManager和全局实例注册表（延迟导入避免循环依赖）
        from core.llm.model_manager import ModelManager, _model_manager_instances
        
        # 清理所有活跃的ModelManager实例
        instances_cleaned = 0
        for instance in list(_model_manager_instances):
            try:
                # 检查是否有运行中的事件循环
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 如果事件循环正在运行，创建清理任务
                        loop.create_task(instance.close_clients())
                    else:
                        # 如果事件循环未运行，运行清理任务
                        loop.run_until_complete(instance.close_clients())
                except RuntimeError:
                    # 事件循环不可用，直接标记实例为已关闭
                    instance._is_closed = True
                    instance._clients.clear()
                
                instances_cleaned += 1
                
            except Exception as e:
                logger.warning(f"清理ModelManager实例时出错: {e}")
        
        if instances_cleaned > 0:
            logger.debug(f"已清理 {instances_cleaned} 个ModelManager实例")
        
        # 执行垃圾收集
        gc.collect()
        
        logger.debug("异步资源清理完成")
        
    except Exception as e:
        logger.warning(f"清理异步资源时出错: {e}")

@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """
    任务完成后的清理处理器（成功或失败都会调用）
    """
    logger.debug(f"任务 {task_id} 执行完成，开始清理资源")
    
    try:
        # 清理异步资源
        cleanup_async_resources()
        
        # 手动垃圾回收
        gc.collect()
        
        logger.debug(f"任务 {task_id} 资源清理完成")
        
    except Exception as e:
        logger.error(f"任务 {task_id} 清理资源时出错: {e}")

@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
    """
    任务失败时的处理器
    """
    logger.error(f"任务 {task_id} 执行失败: {exception}")
    
    # 确保失败的任务也进行资源清理
    try:
        cleanup_async_resources()
        gc.collect()
    except Exception as e:
        logger.error(f"任务 {task_id} 失败后清理资源时出错: {e}")

@task_success.connect 
def task_success_handler(sender=None, result=None, **kwargs):
    """
    任务成功时的处理器
    """
    task_id = kwargs.get('task_id', 'unknown')
    logger.debug(f"任务 {task_id} 执行成功")

@task_retry.connect
def task_retry_handler(sender=None, task_id=None, reason=None, einfo=None, **kwds):
    """
    任务重试时的处理器（虽然我们禁用了重试，但保留此处理器以防万一）
    """
    logger.warning(f"任务 {task_id} 重试: {reason}")
    
    # 重试前也进行资源清理
    try:
        cleanup_async_resources()
        gc.collect()
    except Exception as e:
        logger.error(f"任务 {task_id} 重试前清理资源时出错: {e}") 