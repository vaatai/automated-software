"""Celery application configuration with priority queues, DLQ, and Redis broker tuning.

Queue layout:
  - registrations.high   (priority 0-3)  — urgent / VIP registrations
  - registrations        (priority 4-6)  — normal registrations (default)
  - registrations.low    (priority 7-9)  — bulk / background registrations
  - dead_letter          — permanently failed tasks for inspection
  - monitoring           — lightweight health/status tasks
"""

from celery import Celery
from kombu import Exchange, Queue

from configs.settings import settings

# ── exchanges ───────────────────────────────────────────────
registration_exchange = Exchange("registration", type="direct", durable=True)
dlq_exchange = Exchange("dead_letter", type="direct", durable=True)
monitoring_exchange = Exchange("monitoring", type="direct", durable=True)

# ── queues ──────────────────────────────────────────────────
task_queues = [
    Queue(
        "registrations.high",
        exchange=registration_exchange,
        routing_key="registration.high",
        queue_arguments={"x-max-priority": 10},
    ),
    Queue(
        "registrations",
        exchange=registration_exchange,
        routing_key="registration.normal",
        queue_arguments={"x-max-priority": 10},
    ),
    Queue(
        "registrations.low",
        exchange=registration_exchange,
        routing_key="registration.low",
        queue_arguments={"x-max-priority": 10},
    ),
    Queue(
        "dead_letter",
        exchange=dlq_exchange,
        routing_key="dead_letter",
    ),
    Queue(
        "monitoring",
        exchange=monitoring_exchange,
        routing_key="monitoring",
    ),
]

# ── task routing ────────────────────────────────────────────
task_routes = {
    "workers.registration_worker.execute_registration": {
        "queue": "registrations",
        "routing_key": "registration.normal",
    },
    "workers.registration_worker.execute_registration_high": {
        "queue": "registrations.high",
        "routing_key": "registration.high",
    },
    "workers.registration_worker.execute_registration_low": {
        "queue": "registrations.low",
        "routing_key": "registration.low",
    },
    "workers.dead_letter_worker.process_dead_letter": {
        "queue": "dead_letter",
        "routing_key": "dead_letter",
    },
    "workers.registration_worker.reset_daily_counters": {
        "queue": "monitoring",
        "routing_key": "monitoring",
    },
    "workers.task_monitor.check_stale_tasks": {
        "queue": "monitoring",
        "routing_key": "monitoring",
    },
    "workers.daily_limit_worker.process_overflow_queue": {
        "queue": "monitoring",
        "routing_key": "monitoring",
    },
    "workers.daily_limit_worker.cleanup_daily_records": {
        "queue": "monitoring",
        "routing_key": "monitoring",
    },
    "workers.proxy_worker.reset_rate_limited_proxies": {
        "queue": "monitoring",
        "routing_key": "monitoring",
    },
    "workers.proxy_worker.check_proxy_health": {
        "queue": "monitoring",
        "routing_key": "monitoring",
    },
}

# ── celery app ──────────────────────────────────────────────
celery_app = Celery(
    "automated_software",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "workers.registration_worker",
        "workers.dead_letter_worker",
        "workers.task_monitor",
        "workers.daily_limit_worker",
        "workers.proxy_worker",
    ],
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task tracking
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Worker tuning
    worker_prefetch_multiplier=1,
    worker_concurrency=settings.MAX_CONCURRENT_WORKERS,
    worker_max_tasks_per_child=50,
    worker_max_memory_per_child=512_000,  # 512 MB

    # Time limits
    task_soft_time_limit=300,
    task_time_limit=600,

    # Result backend
    result_expires=86400,  # 24 hours
    result_extended=True,

    # Priority queues
    task_queues=task_queues,
    task_routes=task_routes,
    task_default_queue="registrations",
    task_default_exchange="registration",
    task_default_routing_key="registration.normal",
    task_default_priority=5,
    task_queue_max_priority=10,
    task_inherit_parent_priority=True,

    # Redis broker tuning
    broker_transport_options={
        "visibility_timeout": 3600,
        "queue_order_strategy": "priority",
        "priority_steps": list(range(10)),
    },

    # Beat schedule
    beat_schedule={
        "reset-daily-counters": {
            "task": "workers.registration_worker.reset_daily_counters",
            "schedule": 86400.0,
            "options": {"queue": "monitoring"},
        },
        "check-stale-tasks": {
            "task": "workers.task_monitor.check_stale_tasks",
            "schedule": 300.0,  # every 5 minutes
            "options": {"queue": "monitoring"},
        },
        "process-overflow-queue": {
            "task": "workers.daily_limit_worker.process_overflow_queue",
            "schedule": 86400.0,  # daily (runs after midnight reset)
            "options": {"queue": "monitoring"},
        },
        "reset-rate-limited-proxies": {
            "task": "workers.proxy_worker.reset_rate_limited_proxies",
            "schedule": 300.0,  # every 5 minutes
            "options": {"queue": "monitoring"},
        },
        "check-proxy-health": {
            "task": "workers.proxy_worker.check_proxy_health",
            "schedule": 600.0,  # every 10 minutes
            "options": {"queue": "monitoring"},
        },
        "cleanup-daily-records": {
            "task": "workers.daily_limit_worker.cleanup_daily_records",
            "schedule": 604800.0,  # weekly
            "options": {"queue": "monitoring"},
        },
    },
)
