"""CAPTCHA API wrapper — 2Captcha / CapSolver integration as fallback."""

import asyncio
import logging

import aiohttp

logger = logging.getLogger(__name__)


class TwoCaptchaSolver:
    """2Captcha API wrapper for solving CAPTCHAs when local solving fails.

    Supports: reCAPTCHA v2/v3, hCaptcha, Cloudflare Turnstile, image CAPTCHAs.
    """

    def __init__(self, api_key: str, base_url: str = "https://2captcha.com"):
        self.api_key = api_key
        self.base_url = base_url

    async def solve_recaptcha_v2(
        self, site_key: str, page_url: str, timeout: float = 120.0
    ) -> str:
        """Solve reCAPTCHA v2 via 2Captcha API.

        Args:
            site_key: The reCAPTCHA site key
            page_url: URL of the page with the CAPTCHA
            timeout: Max seconds to wait for solution

        Returns:
            The reCAPTCHA response token.
        """
        return await self._solve_captcha(
            method="userrecaptcha",
            params={"googlekey": site_key, "pageurl": page_url},
            timeout=timeout,
        )

    async def solve_recaptcha_v3(
        self,
        site_key: str,
        page_url: str,
        action: str = "verify",
        min_score: float = 0.7,
        timeout: float = 120.0,
    ) -> str:
        """Solve reCAPTCHA v3."""
        return await self._solve_captcha(
            method="userrecaptcha",
            params={
                "googlekey": site_key,
                "pageurl": page_url,
                "version": "v3",
                "action": action,
                "min_score": min_score,
            },
            timeout=timeout,
        )

    async def solve_hcaptcha(
        self, site_key: str, page_url: str, timeout: float = 120.0
    ) -> str:
        """Solve hCaptcha."""
        return await self._solve_captcha(
            method="hcaptcha",
            params={"sitekey": site_key, "pageurl": page_url},
            timeout=timeout,
        )

    async def solve_turnstile(
        self, site_key: str, page_url: str, timeout: float = 120.0
    ) -> str:
        """Solve Cloudflare Turnstile."""
        return await self._solve_captcha(
            method="turnstile",
            params={"sitekey": site_key, "pageurl": page_url},
            timeout=timeout,
        )

    async def solve_image(
        self, image_base64: str, timeout: float = 60.0
    ) -> str:
        """Solve an image CAPTCHA from base64 data."""
        return await self._solve_captcha(
            method="base64",
            params={"body": image_base64},
            timeout=timeout,
        )

    async def _solve_captcha(
        self, method: str, params: dict, timeout: float = 120.0
    ) -> str:
        """Submit CAPTCHA and poll for result."""
        async with aiohttp.ClientSession() as session:
            # Submit task
            data = {
                "key": self.api_key,
                "method": method,
                "json": 1,
                **params,
            }
            async with session.post(
                f"{self.base_url}/in.php", data=data
            ) as resp:
                result = await resp.json()
                if result.get("status") != 1:
                    raise RuntimeError(
                        f"2Captcha submit failed: {result.get('request', 'unknown')}"
                    )
                task_id = result["request"]

            logger.info(f"CAPTCHA task submitted: {task_id}")

            # Poll for result
            elapsed = 0.0
            while elapsed < timeout:
                await asyncio.sleep(5)
                elapsed += 5

                async with session.get(
                    f"{self.base_url}/res.php",
                    params={
                        "key": self.api_key,
                        "action": "get",
                        "id": task_id,
                        "json": 1,
                    },
                ) as resp:
                    result = await resp.json()
                    if result.get("status") == 1:
                        logger.info("CAPTCHA solved")
                        return result["request"]
                    if result.get("request") == "CAPCHA_NOT_READY":
                        continue
                    raise RuntimeError(
                        f"2Captcha error: {result.get('request', 'unknown')}"
                    )

            raise TimeoutError(f"CAPTCHA not solved within {timeout}s")
