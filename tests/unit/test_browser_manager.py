"""Tests for playwright_bot/browser_manager.py — concurrency limits, stealth config."""

import pytest

from playwright_bot.browser_manager import BrowserManager


@pytest.mark.unit
class TestBrowserManagerInit:
    def test_default_max_contexts(self):
        manager = BrowserManager()
        assert manager._max_contexts == 5

    def test_custom_max_contexts(self):
        manager = BrowserManager(max_contexts=10)
        assert manager._max_contexts == 10

    def test_semaphore_matches_max(self):
        manager = BrowserManager(max_contexts=3)
        assert manager._semaphore._value == 3

    def test_headless_default(self):
        manager = BrowserManager()
        assert manager._headless is True

    def test_no_active_sessions_on_init(self):
        manager = BrowserManager()
        assert manager.active_count == 0


@pytest.mark.unit
class TestStealthConfig:
    def test_random_user_agent_uniqueness(self):
        from playwright_bot.stealth import random_user_agent

        agents = {random_user_agent() for _ in range(20)}
        assert len(agents) > 1

    def test_random_viewport(self):
        from playwright_bot.stealth import random_viewport

        vp = random_viewport()
        assert "width" in vp
        assert "height" in vp
        assert vp["width"] > 0
        assert vp["height"] > 0

    def test_random_locale(self):
        from playwright_bot.stealth import random_locale

        locale = random_locale()
        assert isinstance(locale, str)
        assert len(locale) > 0

    def test_random_timezone(self):
        from playwright_bot.stealth import random_timezone

        tz = random_timezone()
        assert isinstance(tz, str)
        assert "/" in tz

    def test_stealth_scripts(self):
        from playwright_bot.stealth import get_stealth_scripts

        scripts = get_stealth_scripts()
        assert isinstance(scripts, list)
        assert len(scripts) > 0


@pytest.mark.unit
class TestBrowserSessionContext:
    def test_browser_not_started_initially(self):
        manager = BrowserManager()
        assert manager._browser is None

    def test_playwright_not_started_initially(self):
        manager = BrowserManager()
        assert manager._pw is None
