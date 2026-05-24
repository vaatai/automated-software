"""Stealth and anti-detection utilities for Playwright browser contexts."""

import random

# Realistic Chrome user agents (desktop, last ~6 major versions)
USER_AGENTS: list[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# Viewport variations to avoid fingerprint consistency
VIEWPORTS: list[dict[str, int]] = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1280, "height": 800},
    {"width": 1440, "height": 900},
    {"width": 1600, "height": 900},
    {"width": 1280, "height": 720},
]

LANGUAGES: list[str] = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9",
    "en-US,en;q=0.9,fr;q=0.8",
    "en-US,en;q=0.9,de;q=0.8",
    "en-US,en;q=0.9,es;q=0.8",
]

TIMEZONES: list[str] = [
    "America/New_York",
    "America/Chicago",
    "America/Los_Angeles",
    "Europe/London",
    "Europe/Berlin",
]

# JS scripts injected to hide automation indicators
STEALTH_SCRIPTS: list[str] = [
    # Hide webdriver flag
    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});",
    # Override plugins to look realistic
    """
    Object.defineProperty(navigator, 'plugins', {
        get: () => [
            {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
            {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
            {name: 'Native Client', filename: 'internal-nacl-plugin'}
        ]
    });
    """,
    # Override languages
    """
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en']
    });
    """,
    # Override permissions query
    """
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) =>
        parameters.name === 'notifications'
            ? Promise.resolve({state: Notification.permission})
            : originalQuery(parameters);
    """,
    # Hide chrome automation properties
    """
    window.chrome = { runtime: {}, loadTimes: function(){}, csi: function(){} };
    """,
    # Override hardware concurrency
    """
    Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: () => Math.floor(Math.random() * 4) + 4
    });
    """,
    # Hide automation-related properties
    """
    delete navigator.__proto__.webdriver;
    """,
    # Fake screen dimensions to match viewport
    """
    Object.defineProperty(screen, 'availWidth', { get: () => window.innerWidth });
    Object.defineProperty(screen, 'availHeight', { get: () => window.innerHeight });
    """,
    # Override connection info
    """
    Object.defineProperty(navigator, 'connection', {
        get: () => ({
            effectiveType: '4g',
            rtt: 50,
            downlink: 10,
            saveData: false
        })
    });
    """,
]


def random_user_agent() -> str:
    return random.choice(USER_AGENTS)


def random_viewport() -> dict[str, int]:
    return random.choice(VIEWPORTS).copy()


def random_locale() -> str:
    return random.choice(LANGUAGES)


def random_timezone() -> str:
    return random.choice(TIMEZONES)


def get_stealth_scripts() -> list[str]:
    return STEALTH_SCRIPTS.copy()
