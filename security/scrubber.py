"""Credential leakage prevention — log scrubbing and secret masking.

Provides:
  - ``SensitiveFilter``: Python logging filter that scrubs secrets from log output.
  - ``scrub_dict``: Recursively mask sensitive keys in dictionaries.
  - ``SecureLoggingMiddleware``: FastAPI middleware that scrubs request/response headers.

Prevents accidental leakage of API keys, passwords, OTP codes, and session
tokens through application logs, error reports, and debug output.
"""

import logging
import re

from security.vault import mask_secret

# Keys whose values should be scrubbed in dicts and logs
SENSITIVE_KEYS = frozenset(
    {
        "password",
        "password_hash",
        "api_key",
        "api_secret",
        "secret_key",
        "access_token",
        "refresh_token",
        "authorization",
        "cookie",
        "x-api-key",
        "mailslurp_api_key",
        "fivesim_api_key",
        "pvapins_api_key",
        "smsactivate_api_key",
        "otp",
        "otp_code",
        "token",
        "session_token",
        "csrf_token",
        "proxy_url",
    }
)

# Regex patterns to detect secrets in free-form text
_SECRET_PATTERNS = [
    # API keys (common prefixes)
    (re.compile(r"(sk[_-][a-zA-Z0-9]{20,})"), "API_KEY"),
    # Bearer tokens
    (re.compile(r"(Bearer\s+[a-zA-Z0-9._\-]{20,})"), "BEARER_TOKEN"),
    # JWT tokens
    (re.compile(r"(eyJ[a-zA-Z0-9_\-]+\.eyJ[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+)"), "JWT"),
    # Passwords in URLs
    (re.compile(r"(://[^:]+:)([^@]{3,})(@)"), "URL_PASSWORD"),
    # Generic long hex strings (potential keys)
    (re.compile(r"(?<![a-fA-F0-9])([a-fA-F0-9]{32,})(?![a-fA-F0-9])"), "HEX_SECRET"),
]


def scrub_dict(data: dict, depth: int = 0, max_depth: int = 10) -> dict:
    """Recursively mask sensitive values in a dictionary.

    Keys matching ``SENSITIVE_KEYS`` (case-insensitive) have their values
    replaced with ``***``. Nested dicts and lists are recursed.
    """
    if depth > max_depth:
        return data

    result = {}
    for key, value in data.items():
        if key.lower() in SENSITIVE_KEYS:
            if isinstance(value, str) and value:
                result[key] = mask_secret(value)
            else:
                result[key] = "***"
        elif isinstance(value, dict):
            result[key] = scrub_dict(value, depth + 1, max_depth)
        elif isinstance(value, list):
            result[key] = [
                scrub_dict(item, depth + 1, max_depth) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value
    return result


def scrub_text(text: str) -> str:
    """Scrub known secret patterns from free-form text."""
    result = text
    for pattern, label in _SECRET_PATTERNS:
        if label == "URL_PASSWORD":
            result = pattern.sub(r"\1***\3", result)
        else:
            result = pattern.sub(f"[REDACTED_{label}]", result)
    return result


class SensitiveFilter(logging.Filter):
    """Logging filter that scrubs secrets from log records.

    Attach to any logger or handler to prevent accidental secret leakage::

        handler.addFilter(SensitiveFilter())
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = scrub_text(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: scrub_text(str(v)) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    scrub_text(str(a)) if isinstance(a, str) else a for a in record.args
                )
        return True


# ── headers to scrub from request/response logging ──────────
SENSITIVE_HEADERS = frozenset(
    {
        "authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "proxy-authorization",
    }
)


def scrub_headers(headers: dict) -> dict:
    """Mask sensitive HTTP headers."""
    return {k: mask_secret(v) if k.lower() in SENSITIVE_HEADERS else v for k, v in headers.items()}
