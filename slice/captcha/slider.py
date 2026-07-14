"""Slider CAPTCHA solver — Bezier curve trajectory generation."""

import asyncio
import json
import math
import random


def generate_slider_path(start_x: int, end_x: int, duration_ms: int = 400) -> list:
    """Generate a human-like slider drag trajectory.

    Returns list of (x, y, timestamp_ms) tuples.
    """
    distance = end_x - start_x
    steps = int(duration_ms / 16)  # ~60fps

    # Control points with randomness
    cp1x = start_x + distance * random.uniform(0.25, 0.45)
    cp1y = random.randint(-12, 12)
    cp2x = start_x + distance * random.uniform(0.6, 0.8)
    cp2y = random.randint(-12, 12)

    trajectory = []
    accumulated_pause = 0
    for i in range(steps + 1):
        t = i / steps

        # Cubic bezier
        x = (
            (1 - t) ** 3 * start_x
            + 3 * (1 - t) ** 2 * t * cp1x
            + 3 * (1 - t) * t**2 * cp2x
            + t**3 * end_x
        )
        y = (
            (1 - t) ** 3 * 0
            + 3 * (1 - t) ** 2 * t * cp1y
            + 3 * (1 - t) * t**2 * cp2y
            + t**3 * 0
        )

        # Micro-jitter
        x += random.gauss(0, 0.8)
        y += random.gauss(0, 1.2)

        ts = int(t * duration_ms) + accumulated_pause

        # Occasional micro-pauses (human hesitation)
        if random.random() < 0.05:
            trajectory.append((round(x), round(y), ts))
            pause = random.randint(50, 150)
            accumulated_pause += pause
            trajectory.append((round(x), round(y), ts + pause))
        else:
            trajectory.append((round(x), round(y), ts))

    # Small overshoot at end (humans overshoot then correct)
    overshoot = random.randint(3, 8)
    last_ts = trajectory[-1][2]
    trajectory.append((end_x + overshoot, trajectory[-1][1], last_ts + 20))
    trajectory.append((end_x, trajectory[-1][1], last_ts + 40))

    return trajectory


async def solve_slider(
    connection,
    slider_selector: str,
    target_offset: int,
    session_id: str = None,
) -> None:
    """Solve a slider CAPTCHA by dragging to target offset.

    Args:
        connection: CDPConnection instance
        slider_selector: CSS selector for the slider handle
        target_offset: Pixels to drag (from slider start position)
        session_id: Tab session ID
    """
    # Get slider position
    result = await connection.send(
        "Runtime.evaluate",
        {
            "expression": f"JSON.stringify(document.querySelector('{slider_selector}').getBoundingClientRect())",
            "returnByValue": True,
        },
        session_id=session_id,
    )
    rect = json.loads(result["result"]["value"])

    start_x = rect["x"] + rect["width"] / 2
    start_y = rect["y"] + rect["height"] / 2
    end_x = start_x + target_offset

    # Generate trajectory
    path = generate_slider_path(int(start_x), int(end_x))

    # Mouse down on slider
    await connection.send(
        "Input.dispatchMouseEvent",
        {
            "type": "mousePressed",
            "x": int(start_x),
            "y": int(start_y),
            "button": "left",
            "clickCount": 1,
        },
        session_id=session_id,
    )

    # Execute trajectory
    prev_time = 0
    for x, y, ts in path:
        delay = (ts - prev_time) / 1000
        if delay > 0:
            await asyncio.sleep(delay)
        await connection.send(
            "Input.dispatchMouseEvent",
            {"type": "mouseMoved", "x": x, "y": y, "button": "left"},
            session_id=session_id,
        )
        prev_time = ts

    # Mouse up
    await asyncio.sleep(random.uniform(0.03, 0.08))
    await connection.send(
        "Input.dispatchMouseEvent",
        {
            "type": "mouseReleased",
            "x": int(end_x),
            "y": int(start_y),
            "button": "left",
            "clickCount": 1,
        },
        session_id=session_id,
    )
