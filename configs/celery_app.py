from celery import Celery

from configs.settings import settings

celery_app = Celery(
    "automated_software",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["workers.registration_worker"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_concurrency=settings.MAX_CONCURRENT_WORKERS,
    task_soft_time_limit=300,
    task_time_limit=600,
    beat_schedule={
        "reset-daily-counters": {
            "task": "workers.registration_worker.reset_daily_counters",
            "schedule": 86400.0,
        },
    },
)
