"""Integration tests for OTP services — email, mobile, manager."""


import pytest

from otp.sms_provider import RentalResult


@pytest.mark.integration
class TestSMSProviderInterface:
    def test_rental_result_fields(self):
        result = RentalResult(
            order_id="123",
            phone_number="+14155551234",
            provider="fivesim",
            country="US",
            service="any",
        )
        assert result.order_id == "123"
        assert result.phone_number == "+14155551234"
        assert result.provider == "fivesim"
        assert result.country == "US"
        assert result.service == "any"


@pytest.mark.integration
class TestMobileOTPManager:
    def test_imports(self):
        from otp.mobile_otp_manager import MobileOTPManager

        assert MobileOTPManager is not None

    def test_init(self):
        from otp.mobile_otp_manager import MobileOTPManager

        manager = MobileOTPManager()
        assert len(manager._providers) > 0

    def test_providers_sorted_by_priority(self):
        from otp.mobile_otp_manager import MobileOTPManager

        manager = MobileOTPManager()
        priorities = [p.priority for p in manager._providers]
        assert priorities == sorted(priorities)


@pytest.mark.integration
class TestEmailOTPService:
    def test_imports(self):
        from otp.email_otp_service import EmailOTPService

        assert EmailOTPService is not None

    def test_init(self):
        from otp.email_otp_service import EmailOTPService

        service = EmailOTPService(api_key="test-key")
        assert service._api_key == "test-key"


@pytest.mark.integration
class TestOTPEventLogger:
    def test_imports(self):
        from otp.otp_events import OTPEventLogger

        assert OTPEventLogger is not None

    def test_event_logging(self):
        from otp.otp_events import OTPEventLogger, OTPEventType

        event_logger = OTPEventLogger(registration_id=42)
        event_logger.log(OTPEventType.INBOX_CREATED, inbox_id="inbox-abc")
        assert len(event_logger.events) == 1
        assert event_logger.events[0].event_type == OTPEventType.INBOX_CREATED

    def test_multiple_events(self):
        from otp.otp_events import OTPEventLogger, OTPEventType

        event_logger = OTPEventLogger(registration_id=1)
        event_logger.log(OTPEventType.INBOX_CREATED, inbox_id="i1")
        event_logger.log(OTPEventType.POLL_ATTEMPT)
        event_logger.log(OTPEventType.POLL_ATTEMPT)
        event_logger.log(OTPEventType.OTP_EXTRACTED, otp_code="123456")
        assert len(event_logger.events) == 4

    def test_to_dicts(self):
        from otp.otp_events import OTPEventLogger, OTPEventType

        event_logger = OTPEventLogger(registration_id=1)
        event_logger.log(OTPEventType.INBOX_CREATED, inbox_id="i1")
        dicts = event_logger.to_dicts()
        assert len(dicts) == 1
        assert dicts[0]["event_type"] == "inbox_created"
        assert dicts[0]["registration_id"] == 1
