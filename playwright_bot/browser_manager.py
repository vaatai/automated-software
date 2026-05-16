"""Reusable browser manager service for concurrent Playwright workers.

Manages a shared browser instance and hands out isolated browser contexts
with stealth, fingerprint randomization, proxy rotation, and log capture.
Designed for use by multiple concurrent Celery workers.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from playwright_bot.stealth import (
    get_stealth_scripts,
    random_locale,
    random_timezone,
    random_user_agent,
    random_viewport,
)

logger = logging.getLogger(__name__)

SCREENSHOT_DIR = "screenshots"
LOG_DIR = "browser_logs"


class BrowserSession:
    """An isolated browser context + page with log capture and screenshot helpers."""

    def __init__(
        self,
        context: BrowserContext,
        page: Page,
        session_id: str,
    ) -> None:
        self.context = context
        self.page = page
        self.session_id = session_id
        self._console_logs: list[dict] = []
        self._request_logs: list[dict] = []

        # Wire up log capture
        self.page.on("console", self._on_console)
        self.page.on("requestfailed", self._on_request_failed)

    def _on_console(self, msg: object) -> None:
        self._console_logs.append({
            "type": getattr(msg, "type", "unknown"),
            "text": str(msg),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def _on_request_failed(self, request: object) -> None:
        self._request_logs.append({
            "url": getattr(request, "url", ""),
            "failure": str(getattr(request, "failure", "")),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    @property
    def console_logs(self) -> list[dict]:
        return self._console_logs

    @property
    def request_logs(self) -> list[dict]:
        return self._request_logs

    async def screenshot(self, label: str = "error") -> str:
        """Capture a full-page screenshot and return the file path."""
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = f"{SCREENSHOT_DIR}/{self.session_id}_{label}_{ts}.png"
        await self.page.screenshot(path=path, full_page=True)
        logger.info("Screenshot saved: %s", path)
        return path

    def save_logs(self) -> str | None:
        """Write captured browser logs to disk and return the file path."""
        if not self._console_logs and not self._request_logs:
            return None
        os.makedirs(LOG_DIR, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = f"{LOG_DIR}/{self.session_id}_{ts}.log"
        with open(path, "w") as f:
            f.write(f"=== Console Logs ({len(self._console_logs)}) ===\n")
            for entry in self._console_logs:
                f.write(f"[{entry['timestamp']}] [{entry['type']}] {entry['text']}\n")
            f.write(f"\n=== Failed Requests ({len(self._request_logs)}) ===\n")
            for entry in self._request_logs:
                f.write(f"[{entry['timestamp']}] {entry['url']} — {entry['failure']}\n")
        logger.info("Browser logs saved: %s", path)
        return path

    async def close(self) -> None:
        """Close the context (page is closed automatically with it)."""
        try:
            await self.context.close()
        except Exception:
            logger.debug("Context already closed for session %s", self.session_id)


class BrowserManager:
    """Manages a shared Playwright browser with a bounded concurrency pool.

    Usage::

        mgr = BrowserManager(max_contexts=5)
        await mgr.start()

        async with mgr.acquire_session("reg-42") as session:
            await session.page.goto("https://example.com")
            ...

        await mgr.stop()
    """

    def __init__(
        self,
        max_contexts: int = 5,
        headless: bool = True,
        default_timeout_ms: int = 30_000,
        navigation_timeout_ms: int = 30_000,
    ) -> None:
        self._max_contexts = max_contexts
        self._headless = headless
        self._default_timeout_ms = default_timeout_ms
        self._navigation_timeout_ms = navigation_timeout_ms
        self._semaphore = asyncio.Semaphore(max_contexts)
        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._active_sessions: dict[str, BrowserSession] = {}

    @property
    def active_count(self) -> int:
        return len(self._active_sessions)

    # ── lifecycle ──────────────────────────────────────────

    async def start(self) -> None:
        """Launch the shared Chromium browser instance."""
        if self._browser:
            return
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=self._headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-setuid-sandbox",
            ],
        )
        logger.info(
            "BrowserManager started (max_contexts=%d, headless=%s)",
            self._max_contexts,
            self._headless,
        )

    async def stop(self) -> None:
        """Close all sessions and the shared browser."""
        for session in list(self._active_sessions.values()):
            await session.close()
        self._active_sessions.clear()
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._pw:
            await self._pw.stop()
            self._pw = None
        logger.info("BrowserManager stopped")

    # ── context creation ───────────────────────────────────

    async def create_session(
        self,
        session_id: str,
        proxy: dict | None = None,
        user_agent: str | None = None,
        viewport: dict[str, int] | None = None,
        locale: str | None = None,
        timezone_id: str | None = None,
    ) -> BrowserSession:
        """Create an isolated browser context with stealth and fingerprint randomization."""
        if not self._browser:
            msg = "BrowserManager not started — call start() first"
            raise RuntimeError(msg)

        ua = user_agent or random_user_agent()
        vp = viewport or random_viewport()
        loc = locale or random_locale()
        tz = timezone_id or random_timezone()

        context = await self._browser.new_context(
            viewport=vp,
            user_agent=ua,
            locale=loc.split(",")[0].split(";")[0],
            timezone_id=tz,
            proxy=proxy,
            ignore_https_errors=True,
        )

        # Inject stealth scripts into every new page in this context
        for script in get_stealth_scripts():
            await context.add_init_script(script)

        # Set default timeouts
        context.set_default_timeout(self._default_timeout_ms)
        context.set_default_navigation_timeout(self._navigation_timeout_ms)

        page = await context.new_page()
        session = BrowserSession(context=context, page=page, session_id=session_id)
        self._active_sessions[session_id] = session

        logger.debug(
            "Session %s created (ua=%s..., viewport=%s, tz=%s)",
            session_id,
            ua[:40],
            vp,
            tz,
        )
        return session

    async def release_session(self, session_id: str) -> None:
        """Close and release a session back to the pool."""
        session = self._active_sessions.pop(session_id, None)
        if session:
            session.save_logs()
            await session.close()
            logger.debug("Session %s released", session_id)

    class _SessionContextManager:
        """Async context manager returned by acquire_session."""

        def __init__(
            self,
            manager: "BrowserManager",
            session_id: str,
            proxy: dict | None,
            user_agent: str | None,
            viewport: dict[str, int] | None,
            locale: str | None,
            timezone_id: str | None,
        ) -> None:
            self._mgr = manager
            self._session_id = session_id
            self._proxy = proxy
            self._user_agent = user_agent
            self._viewport = viewport
            self._locale = locale
            self._timezone_id = timezone_id
            self._session: BrowserSession | None = None

        async def __aenter__(self) -> BrowserSession:
            await self._mgr._semaphore.acquire()
            try:
                self._session = await self._mgr.create_session(
                    session_id=self._session_id,
                    proxy=self._proxy,
                    user_agent=self._user_agent,
                    viewport=self._viewport,
                    locale=self._locale,
                    timezone_id=self._timezone_id,
                )
            except Exception:
                self._mgr._semaphore.release()
                raise
            return self._session

        async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
            try:
                await self._mgr.release_session(self._session_id)
            finally:
                self._mgr._semaphore.release()

    def acquire_session(
        self,
        session_id: str,
        proxy: dict | None = None,
        user_agent: str | None = None,
        viewport: dict[str, int] | None = None,
        locale: str | None = None,
        timezone_id: str | None = None,
    ) -> _SessionContextManager:
        """Acquire a browser session from the bounded pool.

        Returns an async context manager that automatically releases the
        session (and semaphore slot) on exit::

            async with mgr.acquire_session("reg-42") as session:
                await session.page.goto(...)
        """
        return self._SessionContextManager(
            manager=self,
            session_id=session_id,
            proxy=proxy,
            user_agent=user_agent,
            viewport=viewport,
            locale=locale,
            timezone_id=timezone_id,
        )
