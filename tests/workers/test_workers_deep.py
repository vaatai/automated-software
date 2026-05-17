"""Deep coverage tests for workers modules."""

import pytest


@pytest.mark.unit
class TestDailyLimitWorker:
    def test_process_overflow_queue_callable(self):
        from workers.daily_limit_worker import process_overflow_queue

        assert callable(process_overflow_queue)

    def test_cleanup_daily_records_callable(self):
        from workers.daily_limit_worker import cleanup_daily_records

        assert callable(cleanup_daily_records)


@pytest.mark.unit
class TestDeadLetterWorker:
    def test_dlq_worker_importable(self):
        from workers.dead_letter_worker import process_dead_letter

        assert callable(process_dead_letter)


@pytest.mark.unit
class TestProxyWorker:
    def test_proxy_health_check_callable(self):
        from workers.proxy_worker import check_proxy_health

        assert callable(check_proxy_health)

    def test_reset_rate_limited_callable(self):
        from workers.proxy_worker import reset_rate_limited_proxies

        assert callable(reset_rate_limited_proxies)


@pytest.mark.unit
class TestTaskMonitor:
    def test_check_stale_tasks_callable(self):
        from workers.task_monitor import check_stale_tasks

        assert callable(check_stale_tasks)


@pytest.mark.unit
class TestRegistrationWorkerDeep:
    def test_execute_registration_callable(self):
        from workers.registration_worker import execute_registration

        assert callable(execute_registration)

    def test_execute_registration_high_callable(self):
        from workers.registration_worker import execute_registration_high

        assert callable(execute_registration_high)

    def test_execute_registration_low_callable(self):
        from workers.registration_worker import execute_registration_low

        assert callable(execute_registration_low)

    def test_task_names_are_distinct(self):
        from workers.registration_worker import (
            execute_registration,
            execute_registration_high,
            execute_registration_low,
        )

        assert execute_registration.name != execute_registration_high.name
        assert execute_registration.name != execute_registration_low.name
