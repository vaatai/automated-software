"""Unit tests for utils/failure_detectors.py — CAPTCHA, OTP timeout, proxy ban detectors."""


import pytest

from utils.failure_detectors import (
    CaptchaDetector,
    OTPTimeoutDetector,
    ProxyBanDetector,
)


@pytest.mark.unit
class TestCaptchaDetector:
    def setup_method(self):
        self.detector = CaptchaDetector()

    def test_detects_recaptcha_v2(self):
        html = '<div class="g-recaptcha" data-sitekey="6Le..."></div>'
        result = self.detector.detect(html)
        assert result.detected is True
        assert "recaptcha" in result.captcha_type
        assert result.site_key == "6Le..."

    def test_detects_hcaptcha(self):
        html = '<div class="h-captcha" data-sitekey="abc-123"></div>'
        result = self.detector.detect(html)
        assert result.detected is True
        assert result.captcha_type == "hcaptcha"

    def test_detects_cloudflare_turnstile(self):
        html = '<div class="cf-turnstile" data-sitekey="0x4A..."></div>'
        result = self.detector.detect(html)
        assert result.detected is True
        assert result.captcha_type == "cloudflare_turnstile"

    def test_detects_funcaptcha(self):
        html = '<script src="https://arkoselabs.com/v2/api.js"></script>'
        result = self.detector.detect(html)
        assert result.detected is True
        assert result.captcha_type == "funcaptcha"

    def test_detects_geetest(self):
        html = '<script src="https://geetest.com/api.js"></script>'
        result = self.detector.detect(html)
        assert result.detected is True

    def test_detects_from_network_urls(self):
        html = "<html><body></body></html>"
        urls = ["https://www.google.com/recaptcha/api.js"]
        result = self.detector.detect(html, network_urls=urls)
        assert result.detected is True

    def test_no_captcha_on_normal_page(self):
        html = "<html><body><form><input name='email'></form></body></html>"
        result = self.detector.detect(html)
        assert result.detected is False
        assert result.captcha_type == ""

    def test_extracts_site_key_from_data_attribute(self):
        html = '<div class="g-recaptcha" data-sitekey="test-key-123"></div>'
        result = self.detector.detect(html)
        assert result.site_key == "test-key-123"

    def test_generic_captcha_id(self):
        html = '<div id="captcha"><img src="/captcha.png"></div>'
        result = self.detector.detect(html)
        assert result.detected is True


@pytest.mark.unit
class TestOTPTimeoutDetector:
    def test_no_timeout_initially(self):
        detector = OTPTimeoutDetector(max_wait_seconds=60)
        detector.start_polling()
        result = detector.check_timeout()
        assert result.timed_out is False

    def test_tracks_poll_count(self):
        detector = OTPTimeoutDetector()
        detector.start_polling()
        detector.record_poll()
        detector.record_poll()
        detector.record_poll()
        result = detector.check_timeout()
        assert result.poll_attempts == 3

    def test_timeout_after_max_wait(self):
        detector = OTPTimeoutDetector(max_wait_seconds=0)  # instant timeout
        detector.start_polling()
        result = detector.check_timeout()
        assert result.timed_out is True

    def test_build_timeout_result(self):
        detector = OTPTimeoutDetector()
        detector.start_polling()
        result = detector.build_timeout_result(
            otp_type="email", provider="mailslurp", inbox_id="inbox-123"
        )
        assert result.timed_out is True
        assert result.otp_type == "email"
        assert result.provider == "mailslurp"
        assert result.inbox_id == "inbox-123"

    def test_check_without_start_returns_empty(self):
        detector = OTPTimeoutDetector()
        result = detector.check_timeout()
        assert result.timed_out is False
        assert result.poll_attempts == 0


@pytest.mark.unit
class TestProxyBanDetector:
    def setup_method(self):
        self.detector = ProxyBanDetector()

    def test_detects_403_ban(self):
        result = self.detector.detect_from_page("<html></html>", status_code=403)
        assert result.banned is True

    def test_detects_407_ban(self):
        result = self.detector.detect_from_page("<html></html>", status_code=407)
        assert result.banned is True

    def test_detects_429_rate_limit(self):
        result = self.detector.detect_from_page("<html></html>", status_code=429)
        assert result.rate_limited is True

    def test_detects_ban_from_content(self):
        result = self.detector.detect_from_page(
            "<h1>Access Denied</h1><p>IP blocked</p>"
        )
        assert result.banned is True

    def test_detects_rate_limit_from_content(self):
        result = self.detector.detect_from_page(
            "<h1>Too Many Requests</h1><p>Please slow down</p>"
        )
        assert result.rate_limited is True

    def test_detects_cloudflare_challenge(self):
        html = "<html><body>Checking your browser before accessing. Just a moment... Ray ID: abc</body></html>"
        result = self.detector.detect_from_page(html)
        assert result.banned is True
        assert "cloudflare_challenge" in result.indicators

    def test_normal_response_not_banned(self):
        result = self.detector.detect_from_page(
            "<html><body>Welcome!</body></html>", status_code=200
        )
        assert result.banned is False
        assert result.rate_limited is False

    def test_rate_limit_headers_retry_after(self):
        result = self.detector.detect_from_page(
            "<html></html>",
            status_code=200,
            response_headers={"retry-after": "60"},
        )
        assert result.rate_limited is True

    def test_rate_limit_headers_remaining_zero(self):
        result = self.detector.detect_from_page(
            "<html></html>",
            status_code=200,
            response_headers={"x-ratelimit-remaining": "0"},
        )
        assert result.rate_limited is True

    def test_detect_from_network_proxy_errors(self):
        failed = [
            {"url": "http://example.com", "failure": "net::ERR_PROXY_CONNECTION_FAILED"},
        ]
        result = self.detector.detect_from_network(failed)
        assert result.banned is True

    def test_detect_from_network_no_errors(self):
        result = self.detector.detect_from_network([])
        assert result.banned is False
