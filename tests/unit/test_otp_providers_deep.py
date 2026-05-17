"""Deep OTP provider tests with httpx mocking."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.unit
class TestFiveSimRentNumber:
    @pytest.mark.asyncio
    async def test_rent_number_success(self):
        from otp.fivesim_service import FiveSimService

        svc = FiveSimService()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "id": 12345,
            "phone": "+14155551234",
            "status": "PENDING",
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("otp.fivesim_service.httpx.AsyncClient", return_value=mock_client):
            result = await svc.rent_number(country="US", service="google")

        assert result.order_id == "12345"
        assert result.phone_number == "+14155551234"
        assert result.provider == "5sim"

    @pytest.mark.asyncio
    async def test_rent_number_no_phones(self):
        import httpx

        from otp.fivesim_service import FiveSimService
        from otp.sms_provider import NumberUnavailableError

        svc = FiveSimService()

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("Not Found", request=MagicMock(), response=mock_response)
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("otp.fivesim_service.httpx.AsyncClient", return_value=mock_client),
            pytest.raises(NumberUnavailableError),
        ):
            await svc.rent_number()


@pytest.mark.unit
class TestFiveSimCheckBalance:
    @pytest.mark.asyncio
    async def test_check_balance(self):
        from otp.fivesim_service import FiveSimService

        svc = FiveSimService()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"balance": 100.50}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("otp.fivesim_service.httpx.AsyncClient", return_value=mock_client):
            balance = await svc.check_balance()
        assert balance == 100.50


@pytest.mark.unit
class TestFiveSimReleaseNumber:
    @pytest.mark.asyncio
    async def test_release_number(self):
        from otp.fivesim_service import FiveSimService

        svc = FiveSimService()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("otp.fivesim_service.httpx.AsyncClient", return_value=mock_client):
            await svc.release_number("12345")


@pytest.mark.unit
class TestFiveSimGetStatus:
    @pytest.mark.asyncio
    async def test_get_status(self):
        from otp.fivesim_service import FiveSimService

        svc = FiveSimService()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"balance": 50.0}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("otp.fivesim_service.httpx.AsyncClient", return_value=mock_client):
            status = await svc.get_status()
        from otp.sms_provider import ProviderStatus
        assert status == ProviderStatus.AVAILABLE


@pytest.mark.unit
class TestPVAPinsRentNumber:
    @pytest.mark.asyncio
    async def test_rent_number_success(self):
        from otp.pvapins_service import PVAPinsService

        svc = PVAPinsService()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "id": "pvapins-99",
            "number": "+442071234567",
            "status": "success",
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("otp.pvapins_service.httpx.AsyncClient", return_value=mock_client):
            result = await svc.rent_number(country="US", service="google")
        assert result.provider == "pvapins"


@pytest.mark.unit
class TestSMSActivateRentNumber:
    @pytest.mark.asyncio
    async def test_rent_number_success(self):
        from otp.smsactivate_service import SMSActivateService

        svc = SMSActivateService()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.text = "ACCESS_NUMBER:12345:+14155550000"

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("otp.smsactivate_service.httpx.AsyncClient", return_value=mock_client):
            result = await svc.rent_number(country="0", service="go")
        assert result.order_id == "12345"
        assert result.phone_number == "+14155550000"

    @pytest.mark.asyncio
    async def test_check_balance(self):
        from otp.smsactivate_service import SMSActivateService

        svc = SMSActivateService()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.text = "ACCESS_BALANCE:25.50"

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("otp.smsactivate_service.httpx.AsyncClient", return_value=mock_client):
            balance = await svc.check_balance()
        assert balance == 25.50


@pytest.mark.unit
class TestPVAPinsCheckBalance:
    @pytest.mark.asyncio
    async def test_check_balance_success(self):
        from otp.pvapins_service import PVAPinsService

        svc = PVAPinsService()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"balance": 75.25}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("otp.pvapins_service.httpx.AsyncClient", return_value=mock_client):
            balance = await svc.check_balance()
        assert balance == 75.25

    @pytest.mark.asyncio
    async def test_check_balance_error(self):
        from otp.pvapins_service import PVAPinsService

        svc = PVAPinsService()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("connection failed"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("otp.pvapins_service.httpx.AsyncClient", return_value=mock_client):
            balance = await svc.check_balance()
        assert balance is None


@pytest.mark.unit
class TestPVAPinsGetStatus:
    @pytest.mark.asyncio
    async def test_get_status_available(self):
        from otp.pvapins_service import PVAPinsService
        from otp.sms_provider import ProviderStatus

        svc = PVAPinsService()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"balance": 50.0}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("otp.pvapins_service.httpx.AsyncClient", return_value=mock_client):
            status = await svc.get_status()
        assert status == ProviderStatus.AVAILABLE


@pytest.mark.unit
class TestPVAPinsReleaseNumber:
    @pytest.mark.asyncio
    async def test_release_number(self):
        from otp.pvapins_service import PVAPinsService

        svc = PVAPinsService()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("otp.pvapins_service.httpx.AsyncClient", return_value=mock_client):
            await svc.release_number("pvapins-99")


@pytest.mark.unit
class TestSMSActivateReleaseNumber:
    @pytest.mark.asyncio
    async def test_release_success(self):
        from otp.smsactivate_service import SMSActivateService

        svc = SMSActivateService()
        mock_resp = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("otp.smsactivate_service.httpx.AsyncClient", return_value=mock_client):
            await svc.release_number("12345", success=True)

    @pytest.mark.asyncio
    async def test_release_cancel(self):
        from otp.smsactivate_service import SMSActivateService

        svc = SMSActivateService()
        mock_resp = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("otp.smsactivate_service.httpx.AsyncClient", return_value=mock_client):
            await svc.release_number("12345", success=False)


@pytest.mark.unit
class TestSMSActivateGetStatus:
    @pytest.mark.asyncio
    async def test_get_status_available(self):
        from otp.sms_provider import ProviderStatus
        from otp.smsactivate_service import SMSActivateService

        svc = SMSActivateService()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.text = "ACCESS_BALANCE:10.00"

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("otp.smsactivate_service.httpx.AsyncClient", return_value=mock_client):
            status = await svc.get_status()
        assert status == ProviderStatus.AVAILABLE


@pytest.mark.unit
class TestEmailOTPServiceDeep:
    @pytest.mark.asyncio
    async def test_create_inbox(self):
        from otp.email_otp_service import EmailOTPService

        svc = EmailOTPService()
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "id": "inbox-abc123",
            "emailAddress": "test@mailslurp.com",
        }
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("otp.email_otp_service.httpx.AsyncClient", return_value=mock_client):
            inbox = await svc.create_inbox()
        assert inbox.inbox_id == "inbox-abc123"
        assert inbox.email_address == "test@mailslurp.com"
