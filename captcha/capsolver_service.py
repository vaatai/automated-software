"""CapSolver CAPTCHA solving service.

Supports:
  - reCAPTCHA v2 (checkbox / invisible)
  - reCAPTCHA v3 (score-based)
  - hCaptcha
"""

import logging
import time

import httpx

logger = logging.getLogger(__name__)

CAPSOLVER_API = "https://api.capsolver.com"
POLL_INTERVAL = 3  # seconds between status checks
MAX_POLL_TIME = 120  # max seconds to wait for solution


class CapsolverService:
    """Solve CAPTCHAs via the CapSolver API."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    # ── public helpers ─────────────────────────────────────

    def get_balance(self) -> float:
        resp = self._post("/getBalance", {})
        return resp.get("balance", 0.0)

    def solve_recaptcha_v2(
        self,
        website_url: str,
        website_key: str,
        is_invisible: bool = False,
    ) -> str | None:
        """Solve reCAPTCHA v2 and return the token."""
        return self._solve(
            task_type="ReCaptchaV2TaskProxyLess",
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
        """Solve reCAPTCHA v3 and return the token."""
        return self._solve(
            task_type="ReCaptchaV3TaskProxyLess",
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
        """Solve hCaptcha and return the token."""
        return self._solve(
            task_type="HCaptchaTaskProxyLess",
            extra={
                "websiteURL": website_url,
                "websiteKey": website_key,
            },
            token_key="gRecaptchaResponse",
        )

    # ── internal ───────────────────────────────────────────

    def _solve(self, task_type: str, extra: dict, token_key: str) -> str | None:
        """Create task, poll for result, return token."""
        task_payload = {"type": task_type, **extra}
        logger.info("CapSolver: creating task type=%s url=%s", task_type, extra.get("websiteURL"))

        create_resp = self._post("/createTask", {"task": task_payload})
        task_id = create_resp.get("taskId")
        if not task_id:
            logger.error("CapSolver: no taskId in response: %s", create_resp)
            return None

        logger.info("CapSolver: task created id=%s, polling...", task_id)
        start = time.monotonic()
        while time.monotonic() - start < MAX_POLL_TIME:
            time.sleep(POLL_INTERVAL)
            result = self._post("/getTaskResult", {"taskId": task_id})
            status = result.get("status")
            if status == "ready":
                solution = result.get("solution", {})
                token = solution.get(token_key) or solution.get("token")
                logger.info(
                    "CapSolver: solved in %.1fs (type=%s)",
                    time.monotonic() - start,
                    task_type,
                )
                return token
            if status == "failed":
                logger.error("CapSolver: task failed: %s", result)
                return None

        logger.error("CapSolver: timeout after %ds", MAX_POLL_TIME)
        return None

    def _post(self, path: str, payload: dict) -> dict:
        body = {"clientKey": self._api_key, **payload}
        try:
            resp = httpx.post(f"{CAPSOLVER_API}{path}", json=body, timeout=30)
            data = resp.json()
            if data.get("errorId", 0) != 0:
                logger.warning(
                    "CapSolver API error: %s — %s",
                    data.get("errorCode"),
                    data.get("errorDescription"),
                )
            return data
        except Exception as exc:
            logger.error("CapSolver request failed: %s", exc)
            return {"errorId": 1, "errorDescription": str(exc)}
