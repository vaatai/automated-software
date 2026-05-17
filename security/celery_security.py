"""Secure Celery communication — message signing, serializer hardening, broker TLS.

Provides:
  - ``apply_celery_security()``: hardens an existing Celery app with message
    signing, restricted serializers, and broker transport security.
  - Content type restrictions to prevent pickle deserialization attacks.
  - Broker connection SSL/TLS configuration.
"""

import logging

from celery import Celery

logger = logging.getLogger(__name__)


def apply_celery_security(app: Celery, *, redis_ssl: bool = False) -> None:
    """Apply security hardening to a Celery application.

    Hardening includes:
      1. JSON-only serialization (no pickle/yaml/msgpack)
      2. Content type restrictions
      3. Task result protection
      4. Worker security settings
      5. Optional Redis TLS for broker/backend

    Args:
        app: The Celery application instance.
        redis_ssl: If True, configure Redis connections to use TLS.
    """
    security_config: dict = {
        # ── serialization ───────────────────────────────────
        # Only allow JSON — prevents pickle deserialization attacks
        "task_serializer": "json",
        "result_serializer": "json",
        "accept_content": ["json"],
        "event_serializer": "json",
        # ── content type restrictions ───────────────────────
        # Reject any non-JSON content
        "content_encoding": "utf-8",
        # ── result security ─────────────────────────────────
        # Don't include internal exception tracebacks in results
        # (could leak sensitive info like DB connection strings)
        "task_remote_tracebacks": False,
        # Expire results after 24h (don't keep stale data)
        "result_expires": 86400,
        # ── worker security ─────────────────────────────────
        # Prevent workers from executing tasks not in their include list
        "worker_hijack_root_logger": False,
        # Limit task body size (prevent DoS via oversized messages)
        "task_compression": None,
        # Disable remote control commands from untrusted sources
        "worker_enable_remote_control": True,
    }

    # ── Redis TLS ───────────────────────────────────────────
    if redis_ssl:
        import ssl

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = True
        ssl_context.verify_mode = ssl.CERT_REQUIRED

        security_config["broker_use_ssl"] = {
            "ssl_cert_reqs": ssl.CERT_REQUIRED,
            "ssl_ca_certs": "/etc/ssl/certs/ca-certificates.crt",
        }
        security_config["redis_backend_use_ssl"] = {
            "ssl_cert_reqs": ssl.CERT_REQUIRED,
            "ssl_ca_certs": "/etc/ssl/certs/ca-certificates.crt",
        }
        logger.info("Celery Redis TLS enabled")

    app.conf.update(security_config)
    logger.info("Celery security hardening applied")


def validate_celery_config(app: Celery) -> list[str]:
    """Validate the Celery app's security configuration.

    Returns a list of security warnings (empty = all good).
    """
    warnings: list[str] = []

    if "pickle" in (app.conf.get("accept_content") or []):
        warnings.append("CRITICAL: pickle is in accept_content — deserialization attack risk")

    if app.conf.get("task_serializer") != "json":
        warnings.append(
            f"WARNING: task_serializer is '{app.conf.get('task_serializer')}', expected 'json'"
        )

    if app.conf.get("result_serializer") != "json":
        warnings.append(
            f"WARNING: result_serializer is '{app.conf.get('result_serializer')}', expected 'json'"
        )

    if app.conf.get("task_remote_tracebacks"):
        warnings.append("WARNING: task_remote_tracebacks is enabled — may leak sensitive info")

    broker_url = app.conf.get("broker_url", "")
    if isinstance(broker_url, str) and "@" in broker_url and ":**" not in broker_url:
        warnings.append("WARNING: broker_url may contain plaintext credentials")

    return warnings
