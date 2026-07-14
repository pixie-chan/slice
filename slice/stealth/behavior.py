"""Human-like mouse movement, scroll, and interaction patterns via CDP."""

import asyncio
import math
import random


async def human_click(connection, x: int, y: int, session_id: str = None) -> None:
    """Click at position with human-like mouse path and timing."""
    # Start from a random nearby position
    start_x = random.randint(100, 500)
    start_y = random.randint(100, 300)

    await _move_mouse_bezier(connection, start_x, start_y, x, y, session_id)

    # Small random delay before click
    await asyncio.sleep(random.uniform(0.05, 0.15))

    # Mouse down
    await connection.send(
        "Input.dispatchMouseEvent",
        {"type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1},
        session_id=session_id,
    )

    # Human finger press duration
    await asyncio.sleep(random.uniform(0.05, 0.12))

    # Mouse up
    await connection.send(
        "Input.dispatchMouseEvent",
        {"type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1},
        session_id=session_id,
    )


async def human_type(connection, text: str, session_id: str = None) -> None:
    """Type text with human-like variable delays between keystrokes."""
    for char in text:
        await connection.send(
            "Input.dispatchKeyEvent",
            {"type": "keyDown", "text": char, "key": char, "code": ""},
            session_id=session_id,
        )
        await connection.send(
            "Input.dispatchKeyEvent",
            {"type": "keyUp", "text": char, "key": char, "code": ""},
            session_id=session_id,
        )
        # Variable delay: fast typists ~50ms, slower ~200ms
        await asyncio.sleep(random.uniform(0.05, 0.20))


async def human_scroll(connection, delta_y: int, x: int = 960, y: int = 540, session_id: str = None) -> None:
    """Scroll with human-like behavior — multiple small scrolls with pauses."""
    remaining = abs(delta_y)
    direction = 1 if delta_y > 0 else -1

    while remaining > 0:
        step = min(remaining, random.randint(80, 200))
        await connection.send(
            "Input.dispatchMouseEvent",
            {
                "type": "mouseWheel",
                "x": x,
                "y": y,
                "deltaX": 0,
                "deltaY": step * direction,
            },
            session_id=session_id,
        )
        remaining -= step
        await asyncio.sleep(random.uniform(0.05, 0.25))


async def human_move_to(connection, x: int, y: int, session_id: str = None) -> None:
    """Move mouse to position with bezier curve."""
    start_x = random.randint(100, 500)
    start_y = random.randint(100, 300)
    await _move_mouse_bezier(connection, start_x, start_y, x, y, session_id)


async def _move_mouse_bezier(
    connection, x1: int, y1: int, x2: int, y2: int, session_id: str = None
) -> None:
    """Move mouse along a cubic bezier curve with micro-jitter."""
    distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    steps = max(10, int(distance / 5))

    # Random control points for natural curve
    cp1x = x1 + (x2 - x1) * random.uniform(0.2, 0.4)
    cp1y = y1 + random.randint(-20, 20)
    cp2x = x1 + (x2 - x1) * random.uniform(0.6, 0.8)
    cp2y = y2 + random.randint(-20, 20)

    for i in range(steps + 1):
        t = i / steps
        # Cubic bezier interpolation
        x = (
            (1 - t) ** 3 * x1
            + 3 * (1 - t) ** 2 * t * cp1x
            + 3 * (1 - t) * t**2 * cp2x
            + t**3 * x2
        )
        y = (
            (1 - t) ** 3 * y1
            + 3 * (1 - t) ** 2 * t * cp1y
            + 3 * (1 - t) * t**2 * cp2y
            + t**3 * y2
        )

        # Micro-jitter
        x += random.gauss(0, 0.5)
        y += random.gauss(0, 0.5)

        await connection.send(
            "Input.dispatchMouseEvent",
            {"type": "mouseMoved", "x": round(x), "y": round(y)},
            session_id=session_id,
        )

        # Speed curve: slower at start/end, faster in middle
        speed_factor = math.sin(t * math.pi)
        delay = random.uniform(5, 15) * (1 - speed_factor * 0.7)
        await asyncio.sleep(delay / 1000)
