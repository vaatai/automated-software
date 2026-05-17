"""Unit tests for playwright_bot/registration_bot.py — coverage boost."""

from unittest.mock import MagicMock

import pytest

from playwright_bot.registration_bot import RegistrationBot


@pytest.mark.unit
class TestRegistrationBotInit:
    def test_import(self):
        assert RegistrationBot is not None

    def test_init(self):
        manager = MagicMock()
        bot = RegistrationBot(browser_manager=manager)
        assert bot.manager is manager

    def test_has_mailslurp(self):
        bot = RegistrationBot(browser_manager=MagicMock())
        assert bot.mailslurp is not None

    def test_has_fivesim(self):
        bot = RegistrationBot(browser_manager=MagicMock())
        assert bot.fivesim is not None

    def test_has_pvapins(self):
        bot = RegistrationBot(browser_manager=MagicMock())
        assert bot.pvapins is not None

    def test_has_failure_detectors(self):
        bot = RegistrationBot(browser_manager=MagicMock())
        assert bot._captcha_detector is not None
        assert bot._selector_detector is not None
        assert bot._proxy_ban_detector is not None


@pytest.mark.unit
class TestRegistrationBotMethods:
    def test_has_register_method(self):
        assert hasattr(RegistrationBot, "register")
        assert callable(getattr(RegistrationBot, "register"))
