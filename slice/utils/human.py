"""Human timing utilities — random delays, jitter."""

import asyncio
import random


async def random_delay(min_s: float = 1.0, max_s: float = 4.0) -> None:
    """Sleep for a random human-like duration."""
    await asyncio.sleep(random.uniform(min_s, max_s))


async def think_delay() -> None:
    """Simulate human 'thinking' pause (2-8 seconds)."""
    await asyncio.sleep(random.uniform(2, 8))


async def short_delay() -> None:
    """Quick pause (0.5-1.5 seconds)."""
    await asyncio.sleep(random.uniform(0.5, 1.5))


async def jittered_retry(attempt: int, base: float = 1.0, max_delay: float = 60.0) -> None:
    """Exponential backoff with jitter for retries."""
    delay = min(base * (2 ** attempt) + random.uniform(0, 1), max_delay)
    await asyncio.sleep(delay)
