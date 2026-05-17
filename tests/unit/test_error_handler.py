"""Unit tests for utils/error_handler.py — error classification, retry decisions."""

import pytest

from utils.error_handler import (
    PROXY_SWAP_CATEGORIES,
    RETRIABLE_CATEGORIES,
    ErrorCategory,
    ErrorClassifier,
    ErrorContext,
)


@pytest.mark.unit
class TestErrorClassifier:
    def setup_method(self):
        self.classifier = ErrorClassifier()

    def test_timeout_error_classified(self):
        from playwright.async_api import TimeoutError as PlaywrightTimeout

        category = self.classifier.classify_exception(
            PlaywrightTimeout("Timeout 30000ms exceeded")
        )
        assert category in (
            ErrorCategory.NAVIGATION_TIMEOUT,
            ErrorCategory.TRANSIENT,
        )

    def test_connection_error_classified(self):
        category = self.classifier.classify_exception(
            ConnectionError("ECONNREFUSED Connection refused")
        )
        assert category == ErrorCategory.NETWORK_ERROR

    def test_value_error_is_permanent(self):
        category = self.classifier.classify_exception(ValueError("Invalid config"))
        assert category == ErrorCategory.PERMANENT

    def test_type_error_is_permanent(self):
        category = self.classifier.classify_exception(TypeError("Bad argument"))
        assert category == ErrorCategory.PERMANENT

    def test_generic_exception_transient(self):
        category = self.classifier.classify_exception(Exception("something unexpected"))
        assert category == ErrorCategory.TRANSIENT

    def test_browser_crash_target_closed(self):
        category = self.classifier.classify_exception(Exception("Target closed"))
        assert category == ErrorCategory.BROWSER_CRASH

    def test_browser_disconnected(self):
        category = self.classifier.classify_exception(
            Exception("Browser has been disconnected")
        )
        assert category == ErrorCategory.BROWSER_CRASH

    def test_otp_timeout(self):
        category = self.classifier.classify_exception(
            Exception("OTP not received within timeout")
        )
        assert category == ErrorCategory.OTP_TIMEOUT

    def test_proxy_auth_failure(self):
        category = self.classifier.classify_exception(
            Exception("407 Proxy Authentication Required")
        )
        assert category == ErrorCategory.PROXY_BAN

    def test_navigation_timeout(self):
        from playwright.async_api import TimeoutError as PlaywrightTimeout

        category = self.classifier.classify_exception(
            PlaywrightTimeout("Navigation timeout of 30000ms exceeded")
        )
        assert category == ErrorCategory.NAVIGATION_TIMEOUT


@pytest.mark.unit
class TestClassifyPageState:
    def setup_method(self):
        self.classifier = ErrorClassifier()

    def test_detects_recaptcha(self):
        html = '<div class="g-recaptcha" data-sitekey="abc"></div>'
        category = self.classifier.classify_page_state(html)
        assert category == ErrorCategory.CAPTCHA_DETECTED

    def test_detects_hcaptcha(self):
        html = '<script src="https://hcaptcha.com/1/api.js"></script>'
        category = self.classifier.classify_page_state(html)
        assert category == ErrorCategory.CAPTCHA_DETECTED

    def test_detects_cloudflare_turnstile(self):
        html = '<div class="cf-turnstile"></div>'
        category = self.classifier.classify_page_state(html)
        assert category == ErrorCategory.CAPTCHA_DETECTED

    def test_detects_proxy_ban_from_content(self):
        html = "<h1>Access Denied</h1><p>Your IP has been blocked</p>"
        category = self.classifier.classify_page_state(html)
        assert category == ErrorCategory.PROXY_BAN

    def test_detects_403_status(self):
        category = self.classifier.classify_page_state("<html></html>", status_code=403)
        assert category == ErrorCategory.PROXY_BAN

    def test_normal_page_returns_none(self):
        html = "<html><body><h1>Welcome</h1><form>...</form></body></html>"
        category = self.classifier.classify_page_state(html)
        assert category is None


@pytest.mark.unit
class TestRetriableCategories:
    def test_transient_is_retriable(self):
        assert ErrorCategory.TRANSIENT in RETRIABLE_CATEGORIES

    def test_network_error_is_retriable(self):
        assert ErrorCategory.NETWORK_ERROR in RETRIABLE_CATEGORIES

    def test_navigation_timeout_retriable(self):
        assert ErrorCategory.NAVIGATION_TIMEOUT in RETRIABLE_CATEGORIES

    def test_captcha_not_retriable(self):
        assert ErrorCategory.CAPTCHA_DETECTED not in RETRIABLE_CATEGORIES

    def test_selector_changed_not_retriable(self):
        assert ErrorCategory.SELECTOR_CHANGED not in RETRIABLE_CATEGORIES

    def test_permanent_not_retriable(self):
        assert ErrorCategory.PERMANENT not in RETRIABLE_CATEGORIES

    def test_browser_crash_not_retriable(self):
        assert ErrorCategory.BROWSER_CRASH not in RETRIABLE_CATEGORIES


@pytest.mark.unit
class TestProxySwapCategories:
    def test_proxy_ban_needs_swap(self):
        assert ErrorCategory.PROXY_BAN in PROXY_SWAP_CATEGORIES

    def test_proxy_rate_limited_needs_swap(self):
        assert ErrorCategory.PROXY_RATE_LIMITED in PROXY_SWAP_CATEGORIES

    def test_transient_no_swap(self):
        assert ErrorCategory.TRANSIENT not in PROXY_SWAP_CATEGORIES


@pytest.mark.unit
class TestErrorContext:
    def test_is_retriable_property(self):
        ctx = ErrorContext(registration_id=1, category=ErrorCategory.TRANSIENT)
        assert ctx.is_retriable is True

    def test_permanent_not_retriable(self):
        ctx = ErrorContext(registration_id=1, category=ErrorCategory.PERMANENT)
        assert ctx.is_retriable is False

    def test_needs_proxy_swap(self):
        ctx = ErrorContext(registration_id=1, category=ErrorCategory.PROXY_BAN)
        assert ctx.needs_proxy_swap is True

    def test_to_dict_has_required_fields(self):
        ctx = ErrorContext(
            registration_id=42,
            category=ErrorCategory.CAPTCHA_DETECTED,
            error_message="CAPTCHA found",
        )
        d = ctx.to_dict()
        assert d["registration_id"] == 42
        assert d["category"] == "captcha_detected"
        assert d["error_message"] == "CAPTCHA found"
        assert "timestamp" in d

    def test_to_json_valid(self):
        import json

        ctx = ErrorContext(registration_id=1)
        data = json.loads(ctx.to_json())
        assert data["registration_id"] == 1
