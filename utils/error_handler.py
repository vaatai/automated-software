"""Centralized error handling architecture for the registration platform.

Provides error classification, debugging context capture, and retry decisions.
Every failed registration produces a rich ErrorContext with screenshots,
HTML snapshots, browser logs, and network request traces.
"""

import enum
import json
import logging
import os
import re
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ── directories ─────────────────────────────────────────────
SCREENSHOT_DIR = "screenshots"
HTML_SNAPSHOT_DIR = "html_snapshots"
DEBUG_DIR = "debug_reports"


class ErrorCategory(str, enum.Enum):
    """Classification of errors for retry/routing decisions."""

    TRANSIENT = "transient"
    PERMANENT = "permanent"
    CAPTCHA_DETECTED = "captcha_detected"
    SELECTOR_CHANGED = "selector_changed"
    OTP_TIMEOUT = "otp_timeout"
    PROXY_BAN = "proxy_ban"
    PROXY_RATE_LIMITED = "proxy_rate_limited"
    NAVIGATION_TIMEOUT = "navigation_timeout"
    NETWORK_ERROR = "network_error"
    BROWSER_CRASH = "browser_crash"
    UNKNOWN = "unknown"


# Categories that should be retried with backoff
RETRIABLE_CATEGORIES = frozenset(
    {
        ErrorCategory.TRANSIENT,
        ErrorCategory.NAVIGATION_TIMEOUT,
        ErrorCategory.NETWORK_ERROR,
        ErrorCategory.PROXY_RATE_LIMITED,
    }
)

# Categories that should get a fresh proxy on retry
PROXY_SWAP_CATEGORIES = frozenset(
    {
        ErrorCategory.PROXY_BAN,
        ErrorCategory.PROXY_RATE_LIMITED,
    }
)


@dataclass
class ErrorContext:
    """Rich debugging context captured on every failure.

    Serialized to JSON and stored in task_logs.details for post-mortem analysis.
    """

    registration_id: int
    category: ErrorCategory = ErrorCategory.UNKNOWN
    error_type: str = ""
    error_message: str = ""
    traceback: str = ""

    # Page state at failure time
    page_url: str = ""
    page_title: str = ""
    screenshot_path: str = ""
    html_snapshot_path: str = ""

    # Browser diagnostics
    console_logs: list[dict] = field(default_factory=list)
    network_requests: list[dict] = field(default_factory=list)
    failed_requests: list[dict] = field(default_factory=list)

    # Detection results
    captcha_detected: bool = False
    captcha_type: str = ""
    selector_failures: list[str] = field(default_factory=list)
    otp_timeout_seconds: float = 0.0
    proxy_ban_indicators: list[str] = field(default_factory=list)

    # Execution context
    step_name: str = ""
    attempt_number: int = 0
    elapsed_ms: int = 0
    proxy_used: str = ""
    user_agent: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    @property
    def is_retriable(self) -> bool:
        return self.category in RETRIABLE_CATEGORIES

    @property
    def needs_proxy_swap(self) -> bool:
        return self.category in PROXY_SWAP_CATEGORIES

    def to_dict(self) -> dict:
        return {
            "registration_id": self.registration_id,
            "category": self.category.value,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "traceback": self.traceback,
            "page_url": self.page_url,
            "page_title": self.page_title,
            "screenshot_path": self.screenshot_path,
            "html_snapshot_path": self.html_snapshot_path,
            "console_log_count": len(self.console_logs),
            "network_request_count": len(self.network_requests),
            "failed_request_count": len(self.failed_requests),
            "captcha_detected": self.captcha_detected,
            "captcha_type": self.captcha_type,
            "selector_failures": self.selector_failures,
            "otp_timeout_seconds": self.otp_timeout_seconds,
            "proxy_ban_indicators": self.proxy_ban_indicators,
            "step_name": self.step_name,
            "attempt_number": self.attempt_number,
            "elapsed_ms": self.elapsed_ms,
            "proxy_used": self.proxy_used,
            "user_agent": self.user_agent,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)


class ErrorClassifier:
    """Classifies exceptions and page states into ErrorCategory values."""

    # Patterns indicating CAPTCHA on the page
    CAPTCHA_PATTERNS = [
        r"g-recaptcha",
        r"h-captcha",
        r"cf-turnstile",
        r"captcha",
        r"recaptcha/api",
        r"hcaptcha\.com",
        r"challenges\.cloudflare\.com",
        r"funcaptcha",
        r"arkose",
    ]

    # Patterns indicating proxy ban
    BAN_PATTERNS = [
        "access denied",
        "ip blocked",
        "ip banned",
        "your ip has been",
        "blocked by",
        "request blocked",
        "too many requests from your ip",
        "temporarily banned",
        "suspicious activity",
    ]

    # Playwright timeout exception names
    TIMEOUT_ERRORS = (
        "TimeoutError",
        "NavigationTimedOut",
    )

    # Network-related exception patterns
    NETWORK_PATTERNS = [
        "net::ERR_",
        "NS_ERROR_",
        "ERR_CONNECTION",
        "ERR_NAME_NOT_RESOLVED",
        "ERR_TUNNEL_CONNECTION_FAILED",
        "ERR_PROXY_CONNECTION_FAILED",
        "ECONNREFUSED",
        "ECONNRESET",
        "ETIMEDOUT",
    ]

    def classify_exception(self, exc: Exception) -> ErrorCategory:
        """Classify a Python exception into an error category."""
        exc_type = type(exc).__name__
        exc_msg = str(exc).lower()

        # Browser crash
        if "browser" in exc_msg and ("closed" in exc_msg or "disconnected" in exc_msg):
            return ErrorCategory.BROWSER_CRASH
        if "target closed" in exc_msg or "context destroyed" in exc_msg:
            return ErrorCategory.BROWSER_CRASH

        # Timeout errors
        if exc_type in self.TIMEOUT_ERRORS or "timeout" in exc_type.lower():
            if "navigation" in exc_msg:
                return ErrorCategory.NAVIGATION_TIMEOUT
            return ErrorCategory.TRANSIENT

        # OTP-related timeouts
        if "otp" in exc_msg and ("timeout" in exc_msg or "not received" in exc_msg):
            return ErrorCategory.OTP_TIMEOUT

        # Network errors
        for pattern in self.NETWORK_PATTERNS:
            if pattern.lower() in exc_msg:
                return ErrorCategory.NETWORK_ERROR

        # Proxy auth failures
        if "407" in exc_msg or "proxy auth" in exc_msg:
            return ErrorCategory.PROXY_BAN

        # Permanent failures (config errors, missing data)
        if isinstance(exc, (ValueError, KeyError, TypeError)):
            return ErrorCategory.PERMANENT

        return ErrorCategory.TRANSIENT

    def classify_page_state(
        self,
        html: str,
        page_url: str = "",
        status_code: int | None = None,
    ) -> ErrorCategory | None:
        """Inspect page HTML/URL for known failure patterns.

        Returns a category if a specific failure is detected, else None.
        """
        html_lower = html.lower()

        # CAPTCHA detection
        for pattern in self.CAPTCHA_PATTERNS:
            if re.search(pattern, html_lower):
                return ErrorCategory.CAPTCHA_DETECTED

        # Proxy ban detection from page content
        for pattern in self.BAN_PATTERNS:
            if pattern in html_lower:
                return ErrorCategory.PROXY_BAN

        # HTTP status-based detection
        if status_code in (403, 407):
            return ErrorCategory.PROXY_BAN
        if status_code == 429:
            return ErrorCategory.PROXY_RATE_LIMITED

        return None

    def detect_captcha_type(self, html: str) -> str:
        """Identify the specific CAPTCHA provider from page HTML."""
        html_lower = html.lower()
        if "g-recaptcha" in html_lower or "recaptcha/api" in html_lower:
            if "recaptcha/enterprise" in html_lower:
                return "recaptcha_enterprise"
            if "size=invisible" in html_lower or "recaptcha-v3" in html_lower:
                return "recaptcha_v3"
            return "recaptcha_v2"
        if "h-captcha" in html_lower or "hcaptcha.com" in html_lower:
            return "hcaptcha"
        if "cf-turnstile" in html_lower or "challenges.cloudflare.com" in html_lower:
            return "cloudflare_turnstile"
        if "funcaptcha" in html_lower or "arkose" in html_lower:
            return "funcaptcha"
        return "unknown"


class ErrorHandler:
    """Orchestrates error detection, context capture, and storage.

    Usage in RegistrationBot::

        handler = ErrorHandler(registration_id=42)
        try:
            ...
        except Exception as exc:
            ctx = await handler.handle_error(exc, session=browser_session, step="form_fill")
            # ctx.is_retriable, ctx.category, ctx.screenshot_path, etc.
    """

    def __init__(self, registration_id: int, attempt_number: int = 1) -> None:
        self.registration_id = registration_id
        self.attempt_number = attempt_number
        self.classifier = ErrorClassifier()

    async def handle_error(
        self,
        exc: Exception,
        session: object | None = None,
        step: str = "",
        elapsed_ms: int = 0,
        proxy_used: str = "",
    ) -> ErrorContext:
        """Build a complete ErrorContext from an exception and optional browser session.

        Args:
            exc: The caught exception.
            session: A BrowserSession instance (optional, for page capture).
            step: Current registration step name (e.g., "form_fill", "otp_email").
            elapsed_ms: Time elapsed since task start.
            proxy_used: Proxy URL used for this attempt.
        """
        ctx = ErrorContext(
            registration_id=self.registration_id,
            error_type=type(exc).__name__,
            error_message=str(exc),
            traceback=traceback.format_exc(),
            step_name=step,
            attempt_number=self.attempt_number,
            elapsed_ms=elapsed_ms,
            proxy_used=proxy_used,
        )

        # Classify the exception
        ctx.category = self.classifier.classify_exception(exc)

        # Capture browser state if session is available
        if session is not None:
            await self._capture_browser_state(ctx, session)

        # Save debug report to disk
        self._save_debug_report(ctx)

        logger.warning(
            "Registration %d error [%s] at step '%s': %s",
            self.registration_id,
            ctx.category.value,
            step,
            ctx.error_message,
        )

        return ctx

    async def check_page_state(
        self,
        session: object,
        step: str = "",
    ) -> ErrorContext | None:
        """Proactively inspect the current page for failure indicators.

        Call this after navigation or form submission to detect
        CAPTCHA walls, proxy bans, etc. before they cause exceptions.

        Returns an ErrorContext if a problem is detected, else None.
        """
        page = getattr(session, "page", None)
        if page is None:
            return None

        try:
            html = await page.content()
        except Exception:
            return None

        category = self.classifier.classify_page_state(
            html=html,
            page_url=page.url,
        )
        if category is None:
            return None

        ctx = ErrorContext(
            registration_id=self.registration_id,
            category=category,
            error_type="PageStateDetection",
            error_message=f"Detected {category.value} on page",
            page_url=page.url,
            step_name=step,
            attempt_number=self.attempt_number,
        )

        if category == ErrorCategory.CAPTCHA_DETECTED:
            ctx.captcha_detected = True
            ctx.captcha_type = self.classifier.detect_captcha_type(html)

        if category == ErrorCategory.PROXY_BAN:
            ctx.proxy_ban_indicators = [
                p for p in ErrorClassifier.BAN_PATTERNS if p in html.lower()
            ]

        await self._capture_browser_state(ctx, session)
        self._save_debug_report(ctx)
        return ctx

    async def _capture_browser_state(
        self,
        ctx: ErrorContext,
        session: object,
    ) -> None:
        """Capture screenshot, HTML snapshot, console logs, and network logs."""
        page = getattr(session, "page", None)

        # Page URL + title
        if page is not None:
            try:
                ctx.page_url = page.url
                ctx.page_title = await page.title()
            except Exception:
                pass

        # Screenshot
        try:
            screenshot_fn = getattr(session, "screenshot", None)
            if screenshot_fn is not None:
                ctx.screenshot_path = await screenshot_fn(f"error_{ctx.category.value}")
        except Exception as e:
            logger.debug("Screenshot capture failed: %s", e)

        # HTML snapshot
        if page is not None:
            try:
                html = await page.content()
                ctx.html_snapshot_path = self._save_html_snapshot(html)
                # Run CAPTCHA detection on the captured HTML
                if not ctx.captcha_detected:
                    for pattern in ErrorClassifier.CAPTCHA_PATTERNS:
                        if re.search(pattern, html.lower()):
                            ctx.captcha_detected = True
                            ctx.captcha_type = self.classifier.detect_captcha_type(html)
                            if ctx.category == ErrorCategory.UNKNOWN:
                                ctx.category = ErrorCategory.CAPTCHA_DETECTED
                            break
            except Exception as e:
                logger.debug("HTML snapshot capture failed: %s", e)

        # Console logs
        console_logs = getattr(session, "console_logs", None)
        if console_logs is not None:
            ctx.console_logs = list(console_logs)

        # Network request logs (failed + all)
        request_logs = getattr(session, "request_logs", None)
        if request_logs is not None:
            ctx.failed_requests = list(request_logs)
        network_logs = getattr(session, "network_requests", None)
        if network_logs is not None:
            ctx.network_requests = list(network_logs)

    def _save_html_snapshot(self, html: str) -> str:
        """Write page HTML to disk and return file path."""
        os.makedirs(HTML_SNAPSHOT_DIR, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = f"{HTML_SNAPSHOT_DIR}/reg_{self.registration_id}_{ts}.html"
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        logger.debug("HTML snapshot saved: %s", path)
        return path

    def _save_debug_report(self, ctx: ErrorContext) -> str:
        """Write full debug report as JSON to disk."""
        os.makedirs(DEBUG_DIR, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = f"{DEBUG_DIR}/reg_{self.registration_id}_attempt{ctx.attempt_number}_{ts}.json"
        report = ctx.to_dict()
        report["console_logs"] = ctx.console_logs[-50:]
        report["network_requests"] = ctx.network_requests[-100:]
        report["failed_requests"] = ctx.failed_requests[-50:]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        logger.debug("Debug report saved: %s", path)
        return path
