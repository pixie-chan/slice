"""CAPTCHA solver orchestrator — detects and solves CAPTCHAs automatically."""

import logging

from .slider import solve_slider, generate_slider_path
from .audio import AudioCaptchaSolver
from .api import TwoCaptchaSolver

logger = logging.getLogger(__name__)


class CaptchaSolver:
    """Orchestrates CAPTCHA detection and solving.

    Tries local solvers first, falls back to API service.
    """

    def __init__(self, api_key: str = None):
        self.audio_solver = AudioCaptchaSolver()
        self.api_solver = TwoCaptchaSolver(api_key) if api_key else None

    async def detect(self, connection, session_id: str = None) -> dict | None:
        """Detect if a CAPTCHA is present on the current page.

        Returns:
            Dict with 'type' and 'selector' keys, or None if no CAPTCHA found.
        """
        result = await connection.send(
            "Runtime.evaluate",
            {
                "expression": """
                (() => {
                    // reCAPTCHA
                    if (document.querySelector('.g-recaptcha') || document.querySelector('[data-sitekey]')) {
                        const el = document.querySelector('.g-recaptcha') || document.querySelector('[data-sitekey]');
                        return JSON.stringify({type: 'recaptcha_v2', selector: '.g-recaptcha', siteKey: el.getAttribute('data-sitekey')});
                    }
                    // hCaptcha
                    if (document.querySelector('.h-captcha') || document.querySelector('[data-hcaptcha-sitekey]')) {
                        const el = document.querySelector('.h-captcha') || document.querySelector('[data-hcaptcha-sitekey]');
                        return JSON.stringify({type: 'hcaptcha', selector: '.h-captcha', siteKey: el.getAttribute('data-sitekey') || el.getAttribute('data-hcaptcha-sitekey')});
                    }
                    // Cloudflare Turnstile
                    if (document.querySelector('.cf-turnstile') || document.querySelector('[data-action="turnstile"]))')) {
                        const el = document.querySelector('.cf-turnstile');
                        return JSON.stringify({type: 'turnstile', selector: '.cf-turnstile', siteKey: el ? el.getAttribute('data-sitekey') : ''});
                    }
                    // Slider CAPTCHA (common patterns)
                    if (document.querySelector('.slider-captcha, .captcha-slider, #slider, [class*="slider"]')) {
                        return JSON.stringify({type: 'slider', selector: '.slider-captcha, .captcha-slider, #slider, [class*="slider"]'});
                    }
                    // Image CAPTCHA
                    if (document.querySelector('#captcha, .captcha-image, img[alt*="captcha"], img[src*="captcha"]')) {
                        return JSON.stringify({type: 'image', selector: '#captcha, .captcha-image, img[alt*="captcha"], img[src*="captcha"]'});
                    }
                    // Audio challenge link (often inside reCAPTCHA iframe)
                    if (document.querySelector('#recaptcha-audiobutton, .rc-audiochallenge-tdownload-link')) {
                        return JSON.stringify({type: 'audio', selector: '#recaptcha-audiobutton'});
                    }
                    return null;
                })()
                """,
                "returnByValue": True,
            },
            session_id=session_id,
        )
        value = result.get("result", {}).get("value")
        if value:
            import json
            return json.loads(value)
        return None

    async def solve(
        self,
        connection,
        captcha_info: dict,
        page_url: str = "",
        session_id: str = None,
    ) -> str | None:
        """Solve a detected CAPTCHA.

        Args:
            connection: CDPConnection
            captcha_info: Dict from detect() with 'type', 'selector', etc.
            page_url: Current page URL (for API solver)
            session_id: Tab session ID

        Returns:
            Solution token/string if solved, None if unable.
        """
        captcha_type = captcha_info.get("type")

        if captcha_type == "slider":
            logger.info("Attempting slider CAPTCHA solve...")
            # For sliders, we need to determine the offset
            # This varies per implementation — typically the puzzle piece position
            offset = captcha_info.get("offset", 200)  # default guess
            await solve_slider(
                connection, captcha_info["selector"], offset, session_id
            )
            return "solved"

        elif captcha_type == "audio":
            logger.info("Attempting audio CAPTCHA solve...")
            try:
                return await self.audio_solver.solve_from_element(
                    connection, captcha_info["selector"], session_id
                )
            except ImportError:
                logger.warning("Whisper not available, falling back to API")

        elif captcha_type in ("recaptcha_v2", "hcaptcha", "turnstile"):
            site_key = captcha_info.get("siteKey", "")
            if self.api_solver and site_key:
                logger.info(f"Solving {captcha_type} via 2Captcha API...")
                if captcha_type == "recaptcha_v2":
                    return await self.api_solver.solve_recaptcha_v2(
                        site_key, page_url
                    )
                elif captcha_type == "hcaptcha":
                    return await self.api_solver.solve_hcaptcha(
                        site_key, page_url
                    )
                elif captcha_type == "turnstile":
                    return await self.api_solver.solve_turnstile(
                        site_key, page_url
                    )
            else:
                logger.warning(
                    f"No API key configured, cannot solve {captcha_type} remotely"
                )

        return None
