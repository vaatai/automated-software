"""Anti-Captcha CAPTCHA solving service — fallback solver.

Supports:
  - reCAPTCHA v2 (checkbox / invisible)
  - reCAPTCHA v3 (score-based)
  - hCaptcha
  - Cloudflare Turnstile
"""

import logging
import time

import httpx

logger = logging.getLogger(__name__)

ANTICAPTCHA_API = "https://api.anti-captcha.com"
POLL_INTERVAL = 3
MAX_POLL_TIME = 120


class AntiCaptchaService:
    """Solve CAPTCHAs via the Anti-Captcha API."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def get_balance(self) -> float:
        resp = self._post("/getBalance", {})
        return resp.get("balance", 0.0)

    def solve_recaptcha_v2(
        self,
        website_url: str,
        website_key: str,
        is_invisible: bool = False,
    ) -> str | None:
        task_type = "RecaptchaV2TaskProxyless"
        if is_invisible:
            task_type = "RecaptchaV2TaskProxyless"
        return self._solve(
            task_type=task_type,
            extra={
                "websiteURL": website_url,
                "websiteKey": website_key,
                "isInvisible": is_invisible,
            },
            token_key="gRecaptchaResponse",
        )

    def solve_recaptcha_v3(
        self,
        website_url: str,
        website_key: str,
        page_action: str = "register",
        min_score: float = 0.7,
    ) -> str | None:
        return self._solve(
            task_type="RecaptchaV3TaskProxyless",
            extra={
                "websiteURL": website_url,
                "websiteKey": website_key,
                "pageAction": page_action,
                "minScore": min_score,
            },
            token_key="gRecaptchaResponse",
        )

    def solve_hcaptcha(
        self,
        website_url: str,
        website_key: str,
    ) -> str | None:
        return self._solve(
            task_type="HCaptchaTaskProxyless",
            extra={
                "websiteURL": website_url,
                "websiteKey": website_key,
            },
            token_key="gRecaptchaResponse",
        )

    def solve_turnstile(
        self,
        website_url: str,
        website_key: str,
    ) -> str | None:
        return self._solve(
            task_type="TurnstileTaskProxyless",
            extra={
                "websiteURL": website_url,
                "websiteKey": website_key,
            },
            token_key="token",
        )

    # ── internal ───────────────────────────────────────────

    def _solve(self, task_type: str, extra: dict, token_key: str) -> str | None:
        task_payload = {"type": task_type, **extra}
        logger.info("AntiCaptcha: creating task type=%s url=%s", task_type, extra.get("websiteURL"))

        create_resp = self._post("/createTask", {"task": task_payload})
        task_id = create_resp.get("taskId")
        if not task_id:
            logger.error("AntiCaptcha: no taskId in response: %s", create_resp)
            return None

        logger.info("AntiCaptcha: task created id=%s, polling...", task_id)
        start = time.monotonic()
        while time.monotonic() - start < MAX_POLL_TIME:
            time.sleep(POLL_INTERVAL)
            result = self._post("/getTaskResult", {"taskId": task_id})
            status = result.get("status")
            if status == "ready":
                solution = result.get("solution", {})
                token = solution.get(token_key) or solution.get("token") or solution.get("gRecaptchaResponse")
                logger.info(
                    "AntiCaptcha: solved in %.1fs (type=%s)",
                    time.monotonic() - start,
                    task_type,
                )
                return token
            if result.get("errorId", 0) != 0:
                logger.error("AntiCaptcha: task failed: %s", result)
                return None

        logger.error("AntiCaptcha: timeout after %ds", MAX_POLL_TIME)
        return None

    def _post(self, path: str, payload: dict) -> dict:
        body = {"clientKey": self._api_key, **payload}
        try:
            resp = httpx.post(f"{ANTICAPTCHA_API}{path}", json=body, timeout=30)
            data = resp.json()
            if data.get("errorId", 0) != 0:
                logger.warning(
                    "AntiCaptcha API error: %s — %s",
                    data.get("errorCode"),
                    data.get("errorDescription"),
                )
            return data
        except Exception as exc:
            logger.error("AntiCaptcha request failed: %s", exc)
            return {"errorId": 1, "errorDescription": str(exc)}
