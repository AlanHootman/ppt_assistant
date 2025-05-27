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
    task_routes={
        "apps.api.tasks.ppt_generation.*": {"queue": "ppt_generation"},
        "apps.api.tasks.template_analysis.*": {"queue": "template_analysis"}
    },
    task_annotations={
        "*": {"rate_limit": "10/s"},
        "apps.api.tasks.ppt_generation.generate_ppt_task": {"rate_limit": "2/s"},
    }
) 