"""Unit tests for OTP provider adapters — coverage boost for otp/ modules."""

from unittest.mock import MagicMock

import pytest

from otp.sms_provider import RentalResult, SMSProviderAdapter, SMSResult


@pytest.mark.unit
class TestSMSResult:
    def test_sms_result_with_otp(self):
        r = SMSResult(otp="123456", raw_message="Your code is 123456")
        assert r.otp == "123456"
        assert r.raw_message == "Your code is 123456"

    def test_sms_result_no_otp(self):
        r = SMSResult(otp=None)
        assert r.otp is None
        assert r.raw_message is None


@pytest.mark.unit
class TestRentalResultDataclass:
    def test_all_fields(self):
        r = RentalResult(
            order_id="ord-1",
            phone_number="+12025551234",
            provider="fivesim",
            country="US",
            service="any",
        )
        assert r.order_id == "ord-1"
        assert r.phone_number == "+12025551234"
        assert r.provider == "fivesim"
        assert r.country == "US"
        assert r.service == "any"


@pytest.mark.unit
class TestSMSProviderAdapterInterface:
    def test_abstract_methods_exist(self):
        methods = ["rent_number", "poll_for_otp", "release_number", "check_balance", "get_status"]
        for m in methods:
            assert hasattr(SMSProviderAdapter, m)


@pytest.mark.unit
class TestFiveSimServiceInit:
    def test_init(self):
        from otp.fivesim_service import FiveSimService

        svc = FiveSimService(api_key="test-key")
        assert svc._api_key == "test-key"

    def test_provider_name(self):
        from otp.fivesim_service import FiveSimService

        svc = FiveSimService(api_key="test-key")
        assert svc.provider_name == "5sim"


@pytest.mark.unit
class TestPVAPinsServiceInit:
    def test_init(self):
        from otp.pvapins_service import PVAPinsService

        svc = PVAPinsService(api_key="test-key")
        assert svc._api_key == "test-key"

    def test_provider_name(self):
        from otp.pvapins_service import PVAPinsService

        svc = PVAPinsService(api_key="test-key")
        assert svc.provider_name == "pvapins"


@pytest.mark.unit
class TestSMSActivateServiceInit:
    def test_init(self):
        from otp.smsactivate_service import SMSActivateService

        svc = SMSActivateService(api_key="test-key")
        assert svc._api_key == "test-key"

    def test_provider_name(self):
        from otp.smsactivate_service import SMSActivateService

        svc = SMSActivateService(api_key="test-key")
        assert svc.provider_name == "sms-activate"


@pytest.mark.unit
class TestEmailOTPServiceInit:
    def test_init(self):
        from otp.email_otp_service import EmailOTPService

        svc = EmailOTPService(api_key="test-key")
        assert svc._api_key == "test-key"


@pytest.mark.unit
class TestMobileOTPManagerInit:
    def test_init_default_providers(self):
        from otp.mobile_otp_manager import MobileOTPManager

        mgr = MobileOTPManager()
        assert len(mgr._providers) > 0

    def test_init_custom_providers(self):
        from otp.mobile_otp_manager import MobileOTPManager

        provider = MagicMock(spec=SMSProviderAdapter)
        provider.provider_name = "mock"
        provider.priority = 1
        mgr = MobileOTPManager(providers=[provider])
        assert len(mgr._providers) == 1

    def test_active_rentals_empty(self):
        from otp.mobile_otp_manager import MobileOTPManager

        mgr = MobileOTPManager()
        assert len(mgr._active_rentals) == 0


@pytest.mark.unit
class TestMailSlurpServiceInit:
    def test_import(self):
        from otp.mailslurp_service import MailSlurpService

        assert MailSlurpService is not None

    def test_init(self):
        from otp.mailslurp_service import MailSlurpService

        svc = MailSlurpService(api_key="test-key")
        assert svc._service is not None
        assert svc._service._api_key == "test-key"
