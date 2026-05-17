"""Deep coverage tests for utils.error_handler module."""

import pytest


@pytest.mark.unit
class TestErrorHandlerInit:
    def test_create_error_handler(self):
        from utils.error_handler import ErrorHandler

        handler = ErrorHandler(registration_id=1, attempt_number=2)
        assert handler.registration_id == 1
        assert handler.attempt_number == 2

    def test_default_attempt(self):
        from utils.error_handler import ErrorHandler

        handler = ErrorHandler(registration_id=5)
        assert handler.attempt_number == 1

    def test_has_classifier(self):
        from utils.error_handler import ErrorHandler

        handler = ErrorHandler(registration_id=1)
        assert handler.classifier is not None


@pytest.mark.unit
class TestErrorClassifier:
    def test_classify_connection_error(self):
        from utils.error_handler import ErrorCategory, ErrorClassifier

        c = ErrorClassifier()
        assert c.classify_exception(ConnectionError("ECONNREFUSED")) == ErrorCategory.NETWORK_ERROR

    def test_classify_timeout(self):
        from utils.error_handler import ErrorClassifier

        c = ErrorClassifier()
        result = c.classify_exception(TimeoutError("Operation timed out"))
        assert result is not None

    def test_classify_value_error(self):
        from utils.error_handler import ErrorCategory, ErrorClassifier

        c = ErrorClassifier()
        assert c.classify_exception(ValueError("bad")) == ErrorCategory.PERMANENT

    def test_classify_key_error(self):
        from utils.error_handler import ErrorCategory, ErrorClassifier

        c = ErrorClassifier()
        assert c.classify_exception(KeyError("missing")) == ErrorCategory.PERMANENT

    def test_classify_type_error(self):
        from utils.error_handler import ErrorCategory, ErrorClassifier

        c = ErrorClassifier()
        assert c.classify_exception(TypeError("wrong type")) == ErrorCategory.PERMANENT

    def test_classify_generic_as_transient(self):
        from utils.error_handler import ErrorCategory, ErrorClassifier

        c = ErrorClassifier()
        assert c.classify_exception(RuntimeError("generic")) == ErrorCategory.TRANSIENT

    def test_classify_browser_crash(self):
        from utils.error_handler import ErrorCategory, ErrorClassifier

        c = ErrorClassifier()
        assert c.classify_exception(RuntimeError("browser closed")) == ErrorCategory.BROWSER_CRASH

    def test_classify_context_destroyed(self):
        from utils.error_handler import ErrorCategory, ErrorClassifier

        c = ErrorClassifier()
        assert c.classify_exception(RuntimeError("context destroyed")) == ErrorCategory.BROWSER_CRASH

    def test_classify_otp_timeout(self):
        from utils.error_handler import ErrorCategory, ErrorClassifier

        c = ErrorClassifier()
        assert c.classify_exception(RuntimeError("otp timeout")) == ErrorCategory.OTP_TIMEOUT

    def test_classify_proxy_auth(self):
        from utils.error_handler import ErrorCategory, ErrorClassifier

        c = ErrorClassifier()
        assert c.classify_exception(RuntimeError("HTTP 407 proxy auth required")) == ErrorCategory.PROXY_BAN

    def test_classify_network_patterns(self):
        from utils.error_handler import ErrorCategory, ErrorClassifier

        c = ErrorClassifier()
        for pattern in ["net::ERR_CONNECTION_REFUSED", "NS_ERROR_NET", "ERR_PROXY_CONNECTION_FAILED"]:
            assert c.classify_exception(RuntimeError(pattern)) == ErrorCategory.NETWORK_ERROR

    def test_classify_page_state_captcha(self):
        from utils.error_handler import ErrorCategory, ErrorClassifier

        c = ErrorClassifier()
        assert c.classify_page_state('<div class="g-recaptcha">') == ErrorCategory.CAPTCHA_DETECTED

    def test_classify_page_state_ban(self):
        from utils.error_handler import ErrorCategory, ErrorClassifier

        c = ErrorClassifier()
        assert c.classify_page_state("Access Denied - Your IP has been blocked") == ErrorCategory.PROXY_BAN

    def test_classify_page_state_http_403(self):
        from utils.error_handler import ErrorCategory, ErrorClassifier

        c = ErrorClassifier()
        assert c.classify_page_state("<html>Forbidden</html>", status_code=403) == ErrorCategory.PROXY_BAN

    def test_classify_page_state_http_429(self):
        from utils.error_handler import ErrorCategory, ErrorClassifier

        c = ErrorClassifier()
        assert c.classify_page_state("<html>Slow down</html>", status_code=429) == ErrorCategory.PROXY_RATE_LIMITED

    def test_classify_page_state_clean(self):
        from utils.error_handler import ErrorClassifier

        c = ErrorClassifier()
        assert c.classify_page_state("<html>Welcome</html>", status_code=200) is None

    def test_detect_captcha_type_recaptcha(self):
        from utils.error_handler import ErrorClassifier

        c = ErrorClassifier()
        assert "recaptcha" in c.detect_captcha_type('<div class="g-recaptcha">').lower()

    def test_detect_captcha_type_hcaptcha(self):
        from utils.error_handler import ErrorClassifier

        c = ErrorClassifier()
        assert "hcaptcha" in c.detect_captcha_type('<div class="h-captcha">').lower()

    def test_detect_captcha_type_turnstile(self):
        from utils.error_handler import ErrorClassifier

        c = ErrorClassifier()
        result = c.detect_captcha_type('<div class="cf-turnstile">')
        assert "turnstile" in result.lower()

    def test_detect_captcha_type_none(self):
        from utils.error_handler import ErrorClassifier

        c = ErrorClassifier()
        result = c.detect_captcha_type("<html>Clean page</html>")
        assert result == "" or result is None or result == "unknown"


@pytest.mark.unit
class TestErrorContext:
    def test_creation(self):
        from utils.error_handler import ErrorContext

        ctx = ErrorContext(registration_id=1)
        assert ctx.registration_id == 1
        assert ctx.timestamp != ""

    def test_to_dict(self):
        from utils.error_handler import ErrorContext

        ctx = ErrorContext(
            registration_id=42,
            error_type="network",
            error_message="Connection failed",
        )
        d = ctx.to_dict()
        assert d["registration_id"] == 42
        assert d["error_type"] == "network"

    def test_to_json(self):
        from utils.error_handler import ErrorContext

        ctx = ErrorContext(registration_id=1)
        j = ctx.to_json()
        assert '"registration_id": 1' in j

    def test_is_retriable(self):
        from utils.error_handler import ErrorCategory, ErrorContext

        ctx = ErrorContext(registration_id=1, category=ErrorCategory.NETWORK_ERROR)
        assert ctx.is_retriable is True

    def test_not_retriable(self):
        from utils.error_handler import ErrorCategory, ErrorContext

        ctx = ErrorContext(registration_id=1, category=ErrorCategory.CAPTCHA_DETECTED)
        assert ctx.is_retriable is False

    def test_needs_proxy_swap(self):
        from utils.error_handler import ErrorCategory, ErrorContext

        ctx = ErrorContext(registration_id=1, category=ErrorCategory.PROXY_BAN)
        assert ctx.needs_proxy_swap is True


@pytest.mark.unit
class TestErrorCategory:
    def test_all_categories_exist(self):
        from utils.error_handler import ErrorCategory

        assert ErrorCategory.NETWORK_ERROR is not None
        assert ErrorCategory.TRANSIENT is not None
        assert ErrorCategory.CAPTCHA_DETECTED is not None
        assert ErrorCategory.PROXY_BAN is not None
        assert ErrorCategory.PERMANENT is not None
        assert ErrorCategory.BROWSER_CRASH is not None
        assert ErrorCategory.OTP_TIMEOUT is not None
        assert ErrorCategory.UNKNOWN is not None

    def test_category_count(self):
        from utils.error_handler import ErrorCategory

        categories = list(ErrorCategory)
        assert len(categories) >= 5
