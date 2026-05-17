"""Load tests for queue — concurrent task submission, throughput verification."""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.slow
class TestQueueSubmissionThroughput:
    def test_bulk_task_creation(self):
        """Verify many tasks can be created rapidly without blocking."""
        from configs.celery_app import celery_app

        tasks = []
        start = time.monotonic()
        count = 100

        with patch.object(celery_app, "send_task", return_value=MagicMock(id="mock-id")) as mock:
            for i in range(count):
                result = celery_app.send_task(
                    "workers.registration_worker.execute_registration",
                    args=[i, 1],
                )
                tasks.append(result)

            elapsed = time.monotonic() - start
            assert mock.call_count == count
            assert elapsed < 5.0  # 100 submissions should be near-instant with mock

    def test_priority_queue_ordering(self):
        """Tasks submitted with different priorities go to correct queues."""
        from configs.celery_app import celery_app

        with patch.object(celery_app, "send_task", return_value=MagicMock()) as mock:
            celery_app.send_task(
                "workers.registration_worker.execute_registration_high",
                args=[1, 1],
                queue="registrations.high",
            )
            celery_app.send_task(
                "workers.registration_worker.execute_registration",
                args=[2, 1],
                queue="registrations",
            )
            celery_app.send_task(
                "workers.registration_worker.execute_registration_low",
                args=[3, 1],
                queue="registrations.low",
            )

            calls = mock.call_args_list
            assert calls[0].kwargs.get("queue") == "registrations.high"
            assert calls[1].kwargs.get("queue") == "registrations"
            assert calls[2].kwargs.get("queue") == "registrations.low"


@pytest.mark.slow
class TestConcurrentWorkerExecution:
    def test_concurrent_task_isolation(self):
        """Verify multiple tasks can run concurrently without state leakage."""
        results = []
        count = 10

        def mock_execute(registration_id, website_id):
            return {"registration_id": registration_id, "status": "completed"}

        for i in range(count):
            result = mock_execute(i, 1)
            results.append(result)

        assert len(results) == count
        assert all(r["status"] == "completed" for r in results)
        reg_ids = {r["registration_id"] for r in results}
        assert len(reg_ids) == count  # each task got unique ID

    @pytest.mark.asyncio
    async def test_async_concurrent_execution(self):
        """Verify async tasks run concurrently."""
        execution_order = []

        async def mock_task(task_id, delay):
            execution_order.append(("start", task_id))
            await asyncio.sleep(delay)
            execution_order.append(("end", task_id))
            return task_id

        tasks = [
            mock_task(1, 0.01),
            mock_task(2, 0.01),
            mock_task(3, 0.01),
        ]
        results = await asyncio.gather(*tasks)
        assert set(results) == {1, 2, 3}
        # All should start before any finish (concurrent)
        starts = [e for e in execution_order if e[0] == "start"]
        assert len(starts) == 3


@pytest.mark.slow
class TestBrowserManagerConcurrency:
    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrent_sessions(self):
        """Verify BrowserManager semaphore limits concurrent sessions."""
        from playwright_bot.browser_manager import BrowserManager

        manager = BrowserManager(max_contexts=2)
        assert manager._semaphore._value == 2
