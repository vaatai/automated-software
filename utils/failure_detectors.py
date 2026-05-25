"""Failure detector modules for specific registration failure modes.

Each detector runs against page state, session data, or error context
to identify specific failure patterns and provide actionable diagnostics.
"""

import logging
import re
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ── CAPTCHA Detector ────────────────────────────────────────


@dataclass
class CaptchaDetectionResult:
    detected: bool = False
    captcha_type: str = ""
    site_key: str = ""
    challenge_url: str = ""
    indicators: list[str] = field(default_factory=list)


class CaptchaDetector:
    """Scans page HTML and network activity for CAPTCHA indicators."""

    # Pattern → captcha type mapping
    INDICATORS = {
        r"g-recaptcha": "recaptcha",
        r'class="g-recaptcha"': "recaptcha_v2",
        r"recaptcha/enterprise": "recaptcha_enterprise",
        r"recaptcha/api\.js\?.*render=": "recaptcha_v3",
        r"h-captcha": "hcaptcha",
        r"hcaptcha\.com": "hcaptcha",
        r"cf-turnstile": "cloudflare_turnstile",
        r"challenges\.cloudflare\.com/turnstile": "cloudflare_turnstile",
        r"funcaptcha": "funcaptcha",
        r"arkoselabs\.com": "funcaptcha",
        r"geetest\.com": "geetest",
        r'id="captcha"': "generic_captcha",
        r"captcha[-_]image": "image_captcha",
    }

    # Regex patterns to extract site keys
    SITE_KEY_PATTERNS = [
        r'data-sitekey=["\']([^"\']+)["\']',
        r'sitekey:\s*["\']([^"\']+)["\']',
        r"siteKey:\s*['\"]([^'\"]+)['\"]",
        r'data-site-key=["\']([^"\']+)["\']',
    ]

    def detect(self, html: str, network_urls: list[str] | None = None) -> CaptchaDetectionResult:
        """Scan HTML and optional network URLs for CAPTCHA presence."""
        result = CaptchaDetectionResult()
        html_lower = html.lower()

        for pattern, captcha_type in self.INDICATORS.items():
            if re.search(pattern, html_lower):
                result.detected = True
                result.indicators.append(pattern)
                if not result.captcha_type or captcha_type != "recaptcha":
                    result.captcha_type = captcha_type

        # Extract site key
        for pattern in self.SITE_KEY_PATTERNS:
            match = re.search(pattern, html)
            if match:
                result.site_key = match.group(1)
                break

        # Check network URLs for CAPTCHA service calls
        if network_urls:
            captcha_domains = [
                "google.com/recaptcha",
                "hcaptcha.com",
                "challenges.cloudflare.com",
                "arkoselabs.com",
                "geetest.com",
            ]
            for url in network_urls:
                for domain in captcha_domains:
                    if domain in url:
                        result.detected = True
                        result.challenge_url = url
                        result.indicators.append(f"network:{domain}")
                        break

        return result


# ── Selector Change Detector ────────────────────────────────


@dataclass
class SelectorCheckResult:
    selector: str = ""
    found: bool = False
    alternatives: list[str] = field(default_factory=list)
    error: str = ""


class SelectorChangeDetector:
    """Detects when configured CSS/XPath selectors no longer match page elements.

    Checks each selector from the website config against the live page
    and suggests alternatives when selectors fail.
    """

    # Common fallback selector strategies
    ALTERNATIVE_STRATEGIES = [
        ("input[type='email']", "email input by type"),
        ("input[type='password']", "password input by type"),
        ("input[type='text']", "text input by type"),
        ("input[type='tel']", "phone input by type"),
        ("input[name*='email']", "email input by name"),
        ("input[name*='pass']", "password input by name"),
        ("input[name*='user']", "username input by name"),
        ("input[name*='phone']", "phone input by name"),
        ("input[name*='mobile']", "mobile input by name"),
        ("button[type='submit']", "submit button"),
        ("input[type='submit']", "submit input"),
        ("form button", "form button"),
    ]

    async def check_selectors(
        self,
        page: object,
        form_config: dict,
    ) -> list[SelectorCheckResult]:
        """Validate all selectors from a website's form_config against the live page.

        Returns a list of SelectorCheckResult for each configured selector,
        including alternative selectors found when the original fails.
        """
        results: list[SelectorCheckResult] = []
        steps = form_config.get("steps", [])

        for step in steps:
            # Check field selectors
            for field_name, field_cfg in step.get("fields", {}).items():
                sel = field_cfg.get("selector", "")
                if not sel:
                    continue
                result = await self._check_single_selector(page, sel, field_name)
                results.append(result)

            # Check submit button
            submit = step.get("submit_button", {})
            if submit and submit.get("selector"):
                result = await self._check_single_selector(
                    page, submit["selector"], "submit_button"
                )
                results.append(result)

        # Check OTP selectors
        otp_settings = form_config.get("otp_settings") or {}
        for key in ("email_otp_field", "email_otp_submit", "phone_otp_field", "phone_otp_submit"):
            field_cfg = otp_settings.get(key, {})
            if isinstance(field_cfg, dict) and field_cfg.get("selector"):
                result = await self._check_single_selector(page, field_cfg["selector"], key)
                results.append(result)

        # Check success indicator
        success = form_config.get("success_indicator") or {}
        if success and success.get("selector"):
            result = await self._check_single_selector(
                page, success["selector"], "success_indicator"
            )
            results.append(result)

        return results

    async def _check_single_selector(
        self,
        page: object,
        selector: str,
        label: str,
    ) -> SelectorCheckResult:
        """Test a single selector and find alternatives if it fails."""
        result = SelectorCheckResult(selector=selector)
        try:
            el = await page.query_selector(selector)  # type: ignore[union-attr]
            result.found = el is not None
        except Exception as e:
            result.found = False
            result.error = str(e)

        if not result.found:
            result.alternatives = await self._find_alternatives(page, label)
            logger.warning(
                "Selector '%s' (%s) not found. Alternatives: %s",
                selector,
                label,
                result.alternatives or "none",
            )

        return result

    async def _find_alternatives(
        self,
        page: object,
        field_label: str,
    ) -> list[str]:
        """Try common selector patterns to suggest alternatives."""
        found: list[str] = []
        for sel, _desc in self.ALTERNATIVE_STRATEGIES:
            try:
                el = await page.query_selector(sel)  # type: ignore[union-attr]
                if el:
                    found.append(sel)
            except Exception:
                continue
        return found[:5]


# ── OTP Timeout Detector ────────────────────────────────────


@dataclass
class OTPTimeoutResult:
    timed_out: bool = False
    otp_type: str = ""
    wait_seconds: float = 0.0
    max_seconds: float = 0.0
    provider: str = ""
    inbox_id: str = ""
    poll_attempts: int = 0


class OTPTimeoutDetector:
    """Tracks OTP polling state and detects timeout conditions.

    Wraps OTP polling calls to record timing and detect patterns
    like consistently slow providers or inbox delivery failures.
    """

    def __init__(self, max_wait_seconds: float = 120.0) -> None:
        self.max_wait_seconds = max_wait_seconds
        self._start_time: float | None = None
        self._poll_count = 0

    def start_polling(self) -> None:
        self._start_time = time.monotonic()
        self._poll_count = 0

    def record_poll(self) -> None:
        self._poll_count += 1

    def check_timeout(self) -> OTPTimeoutResult:
        """Check if we've exceeded the configured OTP wait time."""
        if self._start_time is None:
            return OTPTimeoutResult()

        elapsed = time.monotonic() - self._start_time
        return OTPTimeoutResult(
            timed_out=elapsed >= self.max_wait_seconds,
            wait_seconds=elapsed,
            max_seconds=self.max_wait_seconds,
            poll_attempts=self._poll_count,
        )

    def build_timeout_result(
        self,
        otp_type: str = "",
        provider: str = "",
        inbox_id: str = "",
    ) -> OTPTimeoutResult:
        """Build a full timeout result with provider details."""
        result = self.check_timeout()
        result.otp_type = otp_type
        result.provider = provider
        result.inbox_id = inbox_id
        result.timed_out = True
        return result


# ── Proxy Ban Detector ──────────────────────────────────────


@dataclass
class ProxyBanResult:
    banned: bool = False
    rate_limited: bool = False
    indicators: list[str] = field(default_factory=list)
    status_code: int | None = None
    response_headers: dict = field(default_factory=dict)


class ProxyBanDetector:
    """Detects proxy bans and rate limiting from page content and response data."""

    BAN_STATUS_CODES = frozenset({403, 407, 451})
    RATE_LIMIT_STATUS_CODES = frozenset({429})

    CONTENT_BAN_PATTERNS = [
        "access denied",
        "ip blocked",
        "ip banned",
        "ip has been blocked",
        "your ip address",
        "blocked by",
        "request blocked",
        "forbidden",
        "you have been blocked",
        "automated access",
        "bot detected",
        "suspicious activity detected",
        "unusual traffic",
    ]

    CONTENT_RATE_LIMIT_PATTERNS = [
        "too many requests",
        "rate limit",
        "slow down",
        "try again later",
        "request limit exceeded",
        "throttled",
    ]

    CLOUDFLARE_PATTERNS = [
        "checking your browser",
        "just a moment",
        "cf-browser-verification",
        "ray id",
        "__cf_chl_",
    ]

    def detect_from_page(
        self,
        html: str,
        status_code: int | None = None,
        response_headers: dict | None = None,
    ) -> ProxyBanResult:
        """Detect proxy ban or rate limiting from page response."""
        result = ProxyBanResult(
            status_code=status_code,
            response_headers=response_headers or {},
        )
        html_lower = html.lower()

        # Status code checks
        if status_code in self.BAN_STATUS_CODES:
            result.banned = True
            result.indicators.append(f"http_{status_code}")

        if status_code in self.RATE_LIMIT_STATUS_CODES:
            result.rate_limited = True
            result.indicators.append(f"http_{status_code}")

        # Content-based ban detection
        for pattern in self.CONTENT_BAN_PATTERNS:
            if pattern in html_lower:
                result.banned = True
                result.indicators.append(f"content:{pattern}")

        # Content-based rate limit detection
        for pattern in self.CONTENT_RATE_LIMIT_PATTERNS:
            if pattern in html_lower:
                result.rate_limited = True
                result.indicators.append(f"content:{pattern}")

        # Cloudflare challenge detection
        cf_count = sum(1 for p in self.CLOUDFLARE_PATTERNS if p in html_lower)
        if cf_count >= 2:
            result.banned = True
            result.indicators.append("cloudflare_challenge")

        # Rate limit headers
        if response_headers:
            remaining = response_headers.get("x-ratelimit-remaining", "")
            if remaining == "0":
                result.rate_limited = True
                result.indicators.append("ratelimit_header_zero")

            retry_after = response_headers.get("retry-after", "")
            if retry_after:
                result.rate_limited = True
                result.indicators.append(f"retry_after:{retry_after}")

        return result

    def detect_from_network(self, failed_requests: list[dict]) -> ProxyBanResult:
        """Detect proxy issues from a list of failed network requests."""
        result = ProxyBanResult()

        proxy_errors = [
            "net::ERR_PROXY_CONNECTION_FAILED",
            "net::ERR_TUNNEL_CONNECTION_FAILED",
            "net::ERR_PROXY_AUTH_REQUESTED",
        ]

        for req in failed_requests:
            failure = req.get("failure", "")
            for err in proxy_errors:
                if err in failure:
                    result.banned = True
                    result.indicators.append(f"network:{err}")
                    break

        return result
