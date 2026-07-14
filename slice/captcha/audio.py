"""Audio CAPTCHA solver — downloads audio challenge and transcribes it.

Requires: pip install openai-whisper (optional dependency)
"""

import asyncio
import logging
import os
import re
import tempfile

import aiohttp

logger = logging.getLogger(__name__)


class AudioCaptchaSolver:
    """Solve audio CAPTCHAs using OpenAI Whisper for speech-to-text.

    Usage:
        solver = AudioCaptchaSolver(model_size="tiny.en")
        text = await solver.solve(audio_url)
    """

    def __init__(self, model_size: str = "tiny.en"):
        self.model_size = model_size
        self._model = None

    def _load_model(self):
        """Lazy-load Whisper model (heavy import)."""
        if self._model is None:
            try:
                import whisper

                self._model = whisper.load_model(self.model_size)
                logger.info(f"Loaded Whisper model: {self.model_size}")
            except ImportError:
                raise ImportError(
                    "openai-whisper not installed. Run: pip install openai-whisper"
                )

    async def solve(self, audio_url: str = None, audio_data: bytes = None) -> str:
        """Download audio and transcribe it.

        Args:
            audio_url: URL to download audio from
            audio_data: Raw audio bytes (if already downloaded)

        Returns:
            Transcribed text/numbers from the CAPTCHA audio.
        """
        if audio_data is None and audio_url:
            async with aiohttp.ClientSession() as session:
                async with session.get(audio_url) as resp:
                    audio_data = await resp.read()

        if audio_data is None:
            raise ValueError("Must provide audio_url or audio_data")

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_data)
            temp_path = f.name

        try:
            self._load_model()
            result = self._model.transcribe(temp_path, language="en")
            text = result["text"].strip()

            # Extract digits/words (CAPTCHAs are usually numbers or simple words)
            numbers = re.findall(r"\d+", text)
            return " ".join(numbers) if numbers else text
        finally:
            os.unlink(temp_path)

    async def solve_from_element(
        self, connection, audio_element_selector: str, session_id: str = None
    ) -> str:
        """Find audio URL from a CAPTCHA element and solve it.

        Args:
            connection: CDPConnection
            audio_element_selector: CSS selector for the audio element
            session_id: Tab session ID

        Returns:
            Transcribed CAPTCHA answer.
        """
        result = await connection.send(
            "Runtime.evaluate",
            {
                "expression": f"document.querySelector('{audio_element_selector}').src",
                "returnByValue": True,
            },
            session_id=session_id,
        )
        audio_url = result["result"]["value"]
        return await self.solve(audio_url=audio_url)
