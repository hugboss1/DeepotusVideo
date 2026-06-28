"""Animation node render engine: per-frame Pillow compositor over an ffmpeg
base. See docs/superpowers/specs/2026-06-24-animation-node-phase1-design.md."""
from __future__ import annotations

_KEYS = ("x", "y", "scale", "rotation", "opacity")


def ease(name: str, t: float) -> float:
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    if name == "easeIn":
        return t * t
    if name == "easeOut":
        return 1 - (1 - t) * (1 - t)
    if name == "easeInOut":
        return 2 * t * t if t < 0.5 else 1 - ((-2 * t + 2) ** 2) / 2
    if name == "easeOutBack":
        c1 = 1.70158
        c3 = c1 + 1
        return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2
    if name == "easeOutBounce":
        n1, d1 = 7.5625, 2.75
        if t < 1 / d1:
            return n1 * t * t
        if t < 2 / d1:
            t -= 1.5 / d1
            return n1 * t * t + 0.75
        if t < 2.5 / d1:
            t -= 2.25 / d1
            return n1 * t * t + 0.9375
        t -= 2.625 / d1
        return n1 * t * t + 0.984375
    return t  # linear / unknown


def lerp(a: float, b: float, e: float) -> float:
    return a + (b - a) * e


def transform_at(el: dict, t: float):
    start = float(el.get("start", 0))
    dur = max(1e-3, float(el.get("dur", 1)))
    hold = float(el.get("hold", 0))
    if t < start or t > start + dur + hold:
        return None
    u = (t - start) / dur
    e = 1.0 if u >= 1 else ease(el.get("easing", "linear"), u)
    f, to = el["from"], el["to"]
    return {k: lerp(float(f[k]), float(to[k]), e) for k in _KEYS}
