from celery import Celery

from app.config import settings

celery_app = Celery(
    "cyberops",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
)

celery_app.conf.beat_schedule = {
    "process-pending-injects": {
        "task": "workers.process_pending_injects",
        "schedule": 30.0,
    },
    "poll-wazuh-alerts": {
        "task": "workers.poll_wazuh_alerts",
        "schedule": settings.wazuh_poll_interval_seconds,
    },
}
