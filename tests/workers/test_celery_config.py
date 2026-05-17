"""Tests for Celery configuration and queue setup."""

import pytest


@pytest.mark.unit
class TestCeleryAppConfig:
    def test_celery_app_imports(self):
        from configs.celery_app import celery_app

        assert celery_app is not None

    def test_broker_configured(self):
        from configs.celery_app import celery_app

        assert celery_app.conf.broker_url is not None

    def test_result_backend_configured(self):
        from configs.celery_app import celery_app

        assert celery_app.conf.result_backend is not None

    def test_json_serializer(self):
        """Verify Celery uses JSON (not pickle) for security."""
        from configs.celery_app import celery_app

        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.result_serializer == "json"
        assert "json" in celery_app.conf.accept_content

    def test_task_queues_defined(self):
        from configs.celery_app import celery_app

        queues = celery_app.conf.task_queues
        if queues:
            queue_names = [q.name for q in queues]
            assert "registrations" in queue_names
            assert "dead_letter" in queue_names


@pytest.mark.unit
class TestCelerySecurity:
    def test_security_module_imports(self):
        from security.celery_security import apply_celery_security

        assert callable(apply_celery_security)

    def test_pickle_disallowed(self):
        from configs.celery_app import celery_app

        accept = celery_app.conf.accept_content
        assert "pickle" not in accept
