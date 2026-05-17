"""Deep OTP module coverage tests."""


import pytest


@pytest.mark.unit
class TestSMSProviderBase:
    def test_sms_result_class(self):
        from otp.sms_provider import SMSResult

        r = SMSResult(otp="123456", raw_message="Your code is 123456", provider="5sim", order_id="ord-1")
        assert r.otp == "123456"
        assert r.raw_message == "Your code is 123456"
        assert r.provider == "5sim"

    def test_rental_result_class(self):
        from otp.sms_provider import RentalResult

        r = RentalResult(
            order_id="ord-1",
            phone_number="+14155551234",
            provider="5sim",
            country="US",
            service="any",
        )
        assert r.order_id == "ord-1"
        assert r.phone_number == "+14155551234"
        assert r.provider == "5sim"

    def test_rental_result_optional_fields(self):
        from otp.sms_provider import RentalResult

        r = RentalResult(
            order_id="o",
            phone_number="+1",
            provider="test",
            country="US",
            service="ig",
        )
        assert r.country == "US"
        assert r.service == "ig"


@pytest.mark.unit
class TestFiveSimServiceInit:
    def test_init(self):
        from otp.fivesim_service import FiveSimService

        svc = FiveSimService()
        assert svc.provider_name == "5sim"

    def test_has_rent_number(self):
        from otp.fivesim_service import FiveSimService

        svc = FiveSimService()
        assert hasattr(svc, "rent_number")
        assert callable(svc.rent_number)

    def test_has_poll_for_otp(self):
        from otp.fivesim_service import FiveSimService

        svc = FiveSimService()
        assert hasattr(svc, "poll_for_otp")

    def test_has_release_number(self):
        from otp.fivesim_service import FiveSimService

        svc = FiveSimService()
        assert hasattr(svc, "release_number")


@pytest.mark.unit
class TestPVAPinsServiceInit:
    def test_init(self):
        from otp.pvapins_service import PVAPinsService

        svc = PVAPinsService()
        assert svc.provider_name == "pvapins"

    def test_has_methods(self):
        from otp.pvapins_service import PVAPinsService

        svc = PVAPinsService()
        assert hasattr(svc, "rent_number")
        assert hasattr(svc, "poll_for_otp")
        assert hasattr(svc, "release_number")


@pytest.mark.unit
class TestSMSActivateServiceInit:
    def test_init(self):
        from otp.smsactivate_service import SMSActivateService

        svc = SMSActivateService()
        assert svc.provider_name == "sms-activate"

    def test_has_methods(self):
        from otp.smsactivate_service import SMSActivateService

        svc = SMSActivateService()
        assert hasattr(svc, "rent_number")
        assert hasattr(svc, "poll_for_otp")


@pytest.mark.unit
class TestEmailOTPServiceInit:
    def test_init(self):
        from otp.email_otp_service import EmailOTPService

        svc = EmailOTPService()
        assert svc is not None

    def test_has_create_inbox(self):
        from otp.email_otp_service import EmailOTPService

        svc = EmailOTPService()
        assert hasattr(svc, "create_inbox")

    def test_has_poll_for_otp(self):
        from otp.email_otp_service import EmailOTPService

        svc = EmailOTPService()
        assert hasattr(svc, "poll_for_otp")


@pytest.mark.unit
class TestMobileOTPManagerInit:
    def test_init_default(self):
        from otp.mobile_otp_manager import MobileOTPManager

        mgr = MobileOTPManager()
        assert mgr is not None
        assert hasattr(mgr, "rent_number")
        assert hasattr(mgr, "rent_and_verify")

    def test_init_with_providers(self):
        from otp.mobile_otp_manager import MobileOTPManager

        mgr = MobileOTPManager()
        assert len(mgr._providers) >= 1

    def test_active_rentals_empty(self):
        from otp.mobile_otp_manager import MobileOTPManager

        mgr = MobileOTPManager()
        assert len(mgr._active_rentals) == 0


@pytest.mark.unit
class TestOTPEventsDeep:
    def test_event_logger_no_events(self):
        from otp.otp_events import OTPEventLogger

        logger = OTPEventLogger(registration_id=1)
        assert len(logger.events) == 0

    def test_event_types_exist(self):
        from otp.otp_events import OTPEventType

        assert OTPEventType.INBOX_CREATED is not None
        assert OTPEventType.POLL_ATTEMPT is not None
        assert OTPEventType.OTP_EXTRACTED is not None

    def test_multiple_events(self):
        from otp.otp_events import OTPEventLogger, OTPEventType

        logger = OTPEventLogger(registration_id=42)
        logger.log(OTPEventType.INBOX_CREATED, inbox_id="inbox-1")
        logger.log(OTPEventType.POLL_ATTEMPT, attempt=1)
        logger.log(OTPEventType.OTP_EXTRACTED, otp_code="123456")
        assert len(logger.events) == 3

    def test_event_has_timestamp(self):
        from otp.otp_events import OTPEventLogger, OTPEventType

        logger = OTPEventLogger(registration_id=1)
        logger.log(OTPEventType.INBOX_CREATED, inbox_id="x")
        event = logger.events[0]
        assert hasattr(event, "timestamp") or hasattr(event, "created_at")


@pytest.mark.unit
class TestMailSlurpService:
    def test_init(self):
        from otp.mailslurp_service import MailSlurpService

        svc = MailSlurpService()
        assert svc is not None

    def test_has_email_service(self):
        from otp.mailslurp_service import MailSlurpService

        svc = MailSlurpService()
        assert hasattr(svc, "_service")


@pytest.mark.unit
class TestOTPBase:
    def test_base_import(self):
        from otp.base import BaseOTPService

        assert BaseOTPService is not None
