from celery import Celery
from apps.api.config import settings

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