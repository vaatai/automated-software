"""Unit tests for otp/otp_parser.py — regex extraction, multi-source parsing."""

import pytest

from otp.otp_parser import DEFAULT_PATTERNS, OTPParser, OTPPattern


@pytest.mark.unit
class TestOTPParserExtract:
    def setup_method(self):
        self.parser = OTPParser()

    def test_labeled_verification_code(self):
        result = self.parser.extract("Your verification code: 483921")
        assert result.otp == "483921"
        assert result.pattern_name == "labeled_code"
        assert result.confidence > 0.5

    def test_labeled_otp(self):
        result = self.parser.extract("OTP: 7291")
        assert result.otp == "7291"
        assert result.pattern_name == "labeled_code"

    def test_labeled_pin(self):
        result = self.parser.extract("Your PIN is 582941")
        assert result.otp == "582941"

    def test_code_is_your_pattern(self):
        result = self.parser.extract("384719 is your verification code")
        assert result.otp == "384719"
        assert result.pattern_name == "code_is_your"

    def test_use_code_pattern(self):
        result = self.parser.extract("Please use 291847 to verify")
        assert result.otp == "291847"
        assert result.pattern_name == "use_code"

    def test_enter_code_pattern(self):
        result = self.parser.extract("Enter 483721 on the form")
        assert result.otp == "483721"

    def test_bold_html_code(self):
        result = self.parser.extract("Your code is <b>192837</b>")
        assert result.otp == "192837"
        assert result.pattern_name == "code_in_bold"

    def test_strong_html_code(self):
        result = self.parser.extract("Use <strong>847291</strong> to verify")
        assert result.otp == "847291"
        assert result.pattern_name == "code_in_strong"

    def test_standalone_6digit(self):
        result = self.parser.extract("Hello world 384729 end")
        assert result.otp == "384729"
        assert result.pattern_name == "standalone_6digit"

    def test_standalone_4digit(self):
        result = self.parser.extract("Code sent: 4829")
        assert result.otp == "4829"

    def test_8digit_code(self):
        result = self.parser.extract("Your code: 12345678")
        assert result.otp == "12345678"

    def test_no_match(self):
        result = self.parser.extract("No codes here at all")
        assert result.otp is None
        assert result.confidence == 0.0

    def test_empty_string(self):
        result = self.parser.extract("")
        assert result.otp is None

    def test_none_guard(self):
        result = self.parser.extract("")
        assert result.otp is None

    def test_case_insensitive(self):
        result = self.parser.extract("VERIFICATION CODE: 847291")
        assert result.otp == "847291"

    def test_priority_order(self):
        """Labeled code (priority 10) should win over standalone (priority 3)."""
        result = self.parser.extract("Your code: 483921 and also 111111")
        assert result.otp == "483921"
        assert result.pattern_name == "labeled_code"

    def test_min_digits_filter(self):
        parser = OTPParser(min_digits=6)
        result = parser.extract("Your code: 1234")  # only 4 digits
        # 4-digit codes should still match labeled_code but fail length check
        assert result.otp is None or len(result.otp) >= 6

    def test_max_digits_filter(self):
        parser = OTPParser(max_digits=6)
        result = parser.extract("Code: 123456789")  # 9 digits
        assert result.otp is None or len(result.otp) <= 6


@pytest.mark.unit
class TestOTPParserCustomPatterns:
    def test_add_custom_pattern(self):
        parser = OTPParser()
        parser.add_pattern(OTPPattern(
            name="custom_token",
            pattern=r"TOKEN-(\d{6})",
            priority=15,
        ))
        result = parser.extract("Your TOKEN-938271 for login")
        assert result.otp == "938271"
        assert result.pattern_name == "custom_token"

    def test_custom_pattern_takes_priority(self):
        custom = OTPPattern(name="site_specific", pattern=r"#(\d{6})#", priority=20)
        parser = OTPParser()
        parser.add_pattern(custom)
        result = parser.extract("code: 111111 and also #222222#")
        assert result.otp == "222222"
        assert result.pattern_name == "site_specific"

    def test_init_with_custom_patterns_only(self):
        custom = [OTPPattern(name="only", pattern=r"X(\d{4})X", priority=5)]
        parser = OTPParser(custom_patterns=custom)
        result = parser.extract("Code: 123456")  # default patterns not present
        assert result.otp is None  # only custom pattern available
        result2 = parser.extract("X1234X")
        assert result2.otp == "1234"


@pytest.mark.unit
class TestOTPParserFromEmail:
    def setup_method(self):
        self.parser = OTPParser()

    def test_extracts_from_body(self):
        result = self.parser.extract_from_email(body="Your code: 384729")
        assert result.otp == "384729"
        assert result.source == "body"

    def test_extracts_from_subject(self):
        result = self.parser.extract_from_email(
            body="No codes here",
            subject="Your verification code: 192847",
        )
        assert result.otp == "192847"
        assert result.source == "subject"

    def test_extracts_from_html_body(self):
        result = self.parser.extract_from_email(
            body=None,
            subject=None,
            html_body="<p>Code: <b>847291</b></p>",
        )
        assert result.otp == "847291"
        assert result.source == "html_body"

    def test_body_takes_priority(self):
        result = self.parser.extract_from_email(
            body="Code: 111111",
            subject="Code: 222222",
        )
        assert result.otp == "111111"

    def test_all_none(self):
        result = self.parser.extract_from_email()
        assert result.otp is None

    def test_no_codes_anywhere(self):
        result = self.parser.extract_from_email(
            body="Welcome!",
            subject="Account created",
            html_body="<p>Thank you</p>",
        )
        assert result.otp is None


@pytest.mark.unit
class TestDefaultPatterns:
    def test_patterns_sorted_by_priority(self):
        priorities = [p.priority for p in DEFAULT_PATTERNS]
        assert priorities == sorted(priorities, reverse=True)

    def test_all_patterns_have_capture_group(self):
        import re
        for pat in DEFAULT_PATTERNS:
            compiled = re.compile(pat.pattern, pat.flags)
            assert compiled.groups >= 1, f"{pat.name} has no capture group"
