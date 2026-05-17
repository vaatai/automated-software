"""Integration tests for failure recovery — retry backoff, error routing, DLQ."""

import pytest

from utils.error_handler import (
    ErrorCategory,
    ErrorClassifier,
    ErrorContext,
)
from utils.failure_detectors import CaptchaDetector, ProxyBanDetector


@pytest.mark.integration
class TestRetryBackoffDecisions:
    def setup_method(self):
        self.classifier = ErrorClassifier()

    def test_transient_error_retried(self):
        ctx = ErrorContext(
            registration_id=1,
            category=ErrorCategory.TRANSIENT,
        )
        assert ctx.is_retriable is True
        assert ctx.needs_proxy_swap is False

    def test_proxy_ban_swaps_and_retries(self):
        ctx = ErrorContext(
            registration_id=1,
            category=ErrorCategory.PROXY_BAN,
        )
        assert ctx.needs_proxy_swap is True

    def test_captcha_goes_to_dlq(self):
        ctx = ErrorContext(
            registration_id=1,
            category=ErrorCategory.CAPTCHA_DETECTED,
            captcha_detected=True,
            captcha_type="recaptcha_v2",
        )
        assert ctx.is_retriable is False

    def test_selector_change_goes_to_dlq(self):
        ctx = ErrorContext(
            registration_id=1,
            category=ErrorCategory.SELECTOR_CHANGED,
        )
        assert ctx.is_retriable is False

    def test_network_error_retried_with_same_proxy(self):
        ctx = ErrorContext(
            registration_id=1,
            category=ErrorCategory.NETWORK_ERROR,
        )
        assert ctx.is_retriable is True
        assert ctx.needs_proxy_swap is False

    def test_rate_limited_proxy_swapped(self):
        ctx = ErrorContext(
            registration_id=1,
            category=ErrorCategory.PROXY_RATE_LIMITED,
        )
        assert ctx.is_retriable is True
        assert ctx.needs_proxy_swap is True


@pytest.mark.integration
class TestErrorContextSerialization:
    def test_to_dict_complete(self):
        ctx = ErrorContext(
            registration_id=42,
            category=ErrorCategory.CAPTCHA_DETECTED,
            error_type="CaptchaError",
            error_message="reCAPTCHA found on page",
            page_url="https://example.com/register",
            screenshot_path="screenshots/42.png",
            captcha_detected=True,
            captcha_type="recaptcha_v2",
            step_name="fill_form",
            attempt_number=2,
        )
        d = ctx.to_dict()
        assert d["registration_id"] == 42
        assert d["category"] == "captcha_detected"
        assert d["captcha_detected"] is True
        assert d["step_name"] == "fill_form"
        assert d["attempt_number"] == 2

    def test_to_json_parseable(self):
        import json

        ctx = ErrorContext(
            registration_id=1,
            category=ErrorCategory.TRANSIENT,
            console_logs=[{"level": "error", "text": "something"}],
            network_requests=[{"url": "http://example.com"}],
        )
        data = json.loads(ctx.to_json())
        assert data["console_log_count"] == 1
        assert data["network_request_count"] == 1


@pytest.mark.integration
class TestDetectorIntegration:
    def test_captcha_then_classify(self):
        """Detector feeds into classifier pipeline."""
        detector = CaptchaDetector()
        html = '<div class="g-recaptcha" data-sitekey="abc"></div>'
        result = detector.detect(html)
        assert result.detected is True

        classifier = ErrorClassifier()
        category = classifier.classify_page_state(html)
        assert category == ErrorCategory.CAPTCHA_DETECTED

    def test_proxy_ban_detector_then_classify(self):
        detector = ProxyBanDetector()
        result = detector.detect_from_page("<h1>Access Denied</h1>", status_code=403)
        assert result.banned is True

        classifier = ErrorClassifier()
        category = classifier.classify_page_state(
            "<h1>Access Denied</h1>", status_code=403
        )
        assert category == ErrorCategory.PROXY_BAN
