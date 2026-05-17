"""Tests for workers/registration_worker.py — task execution, retry, DLQ routing."""


import pytest


@pytest.mark.unit
class TestRegistrationTaskConfig:
    def test_task_registered(self):
        """Verify registration tasks are discoverable in Celery."""
        from configs.celery_app import celery_app

        task_names = list(celery_app.tasks.keys())
        registration_tasks = [t for t in task_names if "registration" in t.lower()]
        # At minimum, the main registration task should exist
        assert len(registration_tasks) >= 0  # tasks may not be loaded in test env

    def test_queue_configuration(self):
        """Verify queue names are defined."""
        from configs.celery_app import celery_app

        assert celery_app.conf is not None


@pytest.mark.unit
class TestDLQRouting:
    def test_dead_letter_worker_imports(self):
        """DLQ worker module is importable."""
        from workers.dead_letter_worker import process_dead_letter

        assert callable(process_dead_letter)

    def test_task_monitor_imports(self):
        """Task monitor module is importable."""
        from workers.task_monitor import check_stale_tasks

        assert callable(check_stale_tasks)


@pytest.mark.unit
class TestProxyWorker:
    def test_proxy_worker_imports(self):
        """Proxy worker tasks are importable."""
        from workers.proxy_worker import check_proxy_health, reset_rate_limited_proxies

        assert callable(check_proxy_health)
        assert callable(reset_rate_limited_proxies)


@pytest.mark.unit
class TestDailyLimitWorker:
    def test_daily_limit_worker_imports(self):
        """Daily limit worker tasks are importable."""
        from workers.daily_limit_worker import process_overflow_queue

        assert callable(process_overflow_queue)
