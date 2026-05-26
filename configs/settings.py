from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    # --- Database (PostgreSQL) ---
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/automated_software"
    DATABASE_URL_SYNC: str = "postgresql://user:password@localhost:5432/automated_software"

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- MailSlurp (Email OTP) ---
    MAILSLURP_API_KEY: str = ""

    # --- 5SIM (Primary SMS OTP) ---
    FIVESIM_API_KEY: str = ""
    FIVESIM_BASE_URL: str = "https://5sim.net/v1"

    # --- PVAPins (Secondary SMS OTP) ---
    PVAPINS_API_KEY: str = ""
    PVAPINS_BASE_URL: str = "https://pvapins.com/api"

    # --- SMS-Activate (Backup SMS OTP) ---
    SMSACTIVATE_API_KEY: str = ""
    SMSACTIVATE_BASE_URL: str = "https://api.sms-activate.org/stubs/handler_api.php"

    # --- Application ---
    APP_NAME: str = "Automated Registration Software"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-to-a-random-secret"
    MAX_CONCURRENT_WORKERS: int = 3
    DEFAULT_DAILY_LIMIT: int = 100
    OTP_POLL_TIMEOUT_SECONDS: int = 120
    OTP_POLL_INTERVAL_SECONDS: int = 5

    # --- MailSlurp Webhook ---
    MAILSLURP_WEBHOOK_URL: str = ""
    MAILSLURP_INBOX_EXPIRY_MS: int = 600_000

    # --- CAPTCHA Solving ---
    CAPSOLVER_API_KEY: str = ""
    ANTICAPTCHA_API_KEY: str = ""

    # --- Bright Data Scraping Browser ---
    BRIGHT_DATA_BROWSER_WSS: str = ""

    # --- Proxy Management ---
    PROXY_URL: str = ""
    PROXY_BAN_THRESHOLD: int = 5
    PROXY_COOLDOWN_SECONDS: int = 60
    PROXY_RATE_LIMIT_COOLDOWN: int = 300
    PROXY_MAX_FAIL_RATE_PCT: int = 50

    # --- Error Handling & Resilience ---
    ERROR_SCREENSHOT_ON_FAILURE: bool = True
    ERROR_HTML_SNAPSHOT_ON_FAILURE: bool = True
    ERROR_BROWSER_LOG_ON_FAILURE: bool = True
    ERROR_NETWORK_LOG_ON_FAILURE: bool = True
    ERROR_MAX_CONSOLE_LOGS: int = 50
    ERROR_MAX_NETWORK_LOGS: int = 200
    ERROR_MAX_DEBUG_REPORTS_DAYS: int = 7

    # --- Security ---
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT_MAX: int = 60
    RATE_LIMIT_DEFAULT_WINDOW: int = 60
    SECURITY_HEADERS_ENABLED: bool = True
    ENABLE_HSTS: bool = True
    ENABLE_CSP: bool = True
    AUDIT_LOG_ENABLED: bool = True
    CELERY_REDIS_SSL: bool = False
    CORS_ALLOWED_ORIGINS: str = "*"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
