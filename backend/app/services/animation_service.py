"""Animation node render engine: per-frame Pillow compositor over an ffmpeg
base. See docs/superpowers/specs/2026-06-24-animation-node-phase1-design.md."""
from __future__ import annotations

_KEYS = ("x", "y", "scale", "rotation", "opacity")


def _bezier_y_for_x(p1x, p1y, p2x, p2y, x):
    """Cubic bezier with P0=(0,0), P3=(1,1): solve Bx(s)=x for s, return By(s)."""
    def bx(s): return 3 * (1 - s) ** 2 * s * p1x + 3 * (1 - s) * s * s * p2x + s ** 3
    def by(s): return 3 * (1 - s) ** 2 * s * p1y + 3 * (1 - s) * s * s * p2y + s ** 3
    def dbx(s): return 3 * (1 - s) ** 2 * p1x + 6 * (1 - s) * s * (p2x - p1x) + 3 * s * s * (1 - p2x)
    s = x
    for _ in range(8):
        err = bx(s) - x
        if abs(err) < 1e-6:
            break
        d = dbx(s)
        if abs(d) < 1e-6:
            break
        s -= err / d
        s = 0.0 if s < 0 else 1.0 if s > 1 else s
    if abs(bx(s) - x) > 1e-4:  # bisection fallback
        lo, hi = 0.0, 1.0
        for _ in range(40):
            s = (lo + hi) / 2
            if bx(s) < x:
                lo = s
            else:
                hi = s
    return by(s)


_BEZIER = {
    "smooth": (0.4, 0.0, 0.2, 1.0),
    "easeInOutSine": (0.45, 0.05, 0.55, 0.95),
    "anticipate": (0.36, 0.0, 0.66, -0.56),
    "overshoot": (0.34, 1.56, 0.64, 1.0),
}


def ease(name: str, t: float) -> float:
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    if name in _BEZIER:
        return _bezier_y_for_x(*_BEZIER[name], t)
    if isinstance(name, str) and name.startswith("cubic-bezier(") and name.endswith(")"):
        try:
            a, b, c, d = (float(v) for v in name[len("cubic-bezier("):-1].split(","))
            return _bezier_y_for_x(a, b, c, d, t)
        except Exception:
            return t
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


def kfs_of(el: dict):
    """Normalize an element to a sorted keyframe list. Accepts the Phase-2
    `keyframes[]` shape or synthesizes one from the legacy `from`/`to`."""
    kfs = el.get("keyframes")
    if isinstance(kfs, list) and len(kfs) >= 2:
        return sorted(kfs, key=lambda k: float(k.get("t", 0)))
    f = el.get("from", {})
    to = el.get("to", {})
    base = {k: 0 for k in _KEYS}
    k0 = {**base, **f, "t": 0.0, "easing": el.get("easing", "linear")}
    k1 = {**base, **to, "t": 1.0}
    return [k0, k1]


def transform_at(el: dict, t: float):
    start = float(el.get("start", 0))
    dur = max(1e-3, float(el.get("dur", 1)))
    hold = float(el.get("hold", 0))
    if t < start or t > start + dur + hold:
        return None
    kfs = kfs_of(el)
    u = (t - start) / dur
    if u >= 1:
        last = kfs[-1]
        return {k: float(last[k]) for k in _KEYS}
    i = 0
    while i < len(kfs) - 2 and u > float(kfs[i + 1]["t"]):
        i += 1
    a, b = kfs[i], kfs[i + 1]
    ta, tb = float(a["t"]), float(b["t"])
    span = max(1e-9, tb - ta)
    e = ease(a.get("easing", "linear"), (u - ta) / span)
    return {k: lerp(float(a[k]), float(b[k]), e) for k in _KEYS}


def _hex(c: str):
    c = (c or "#ffffff").lstrip("#")
    if len(c) == 3:  # #fff shorthand
        c = "".join(ch * 2 for ch in c)
    if len(c) != 6:
        c = "ffffff"
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) + (255,)


def _font_path(name: str | None) -> str:
    """Resolve a design-font name to its shipped TTF path, reusing
    template_service's font table + fonts dir (no hardcoded path)."""
    from pathlib import Path
    from app.services import template_service as T
    fn = T._FONT_FILES.get((name or "").strip().lower(), T._DEFAULT_FONT)
    fonts = Path(T.__file__).parent.parent / "templates" / "_fonts"
    p = fonts / fn
    if not p.exists():
        p = fonts / T._DEFAULT_FONT
    return str(p)


def render_element(el: dict, tr: dict, W: int, H: int):
    """Render a single element at transform `tr` onto a fresh W×H RGBA layer."""
    from PIL import Image, ImageDraw, ImageFont
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    typ = el.get("type", "text")
    if typ == "text":
        st = el.get("style", {})
        size = max(4, int(st.get("size", 48) * float(tr.get("scale", 1))))
        font = ImageFont.truetype(_font_path(st.get("font", "JetBrains Mono")), size)
        txt = el.get("text", "")
        tmp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(tmp)
        bb = d.textbbox((0, 0), txt, font=font)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        ix = int(tr["x"] / 100 * W - tw / 2)
        iy = int(tr["y"] / 100 * H - th / 2)
        sc = int(st.get("stroke", 0) or 0)
        d.text((ix, iy), txt, font=font, fill=_hex(st.get("color", "#ffffff")),
               stroke_width=sc, stroke_fill=_hex(st.get("strokeColor", "#000000")))
        el_img = tmp
    else:  # sticker | image
        from app.config import settings
        src = settings.images_path / el.get("filename", "")
        if not el.get("filename") or not src.exists():
            return layer
        im = Image.open(src).convert("RGBA")
        s = float(tr.get("scale", 1))
        im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))))
        el_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        el_img.alpha_composite(im, (int(tr["x"] / 100 * W - im.width / 2),
                                    int(tr["y"] / 100 * H - im.height / 2)))
    rot = float(tr.get("rotation", 0) or 0)
    if rot:
        el_img = el_img.rotate(-rot, resample=Image.BICUBIC,
                               center=(int(tr["x"] / 100 * W), int(tr["y"] / 100 * H)))
    op = max(0.0, min(1.0, float(tr.get("opacity", 1))))
    if op < 1:
        a = el_img.split()[3].point(lambda v: int(v * op))
        el_img.putalpha(a)
    layer.alpha_composite(el_img)
    return layer


def _wh(aspect: str):
    return {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080),
            "4:5": (1080, 1350)}.get(aspect, (1080, 1920))


def render_animation(payload: dict, job_id: str):
    """Composite animated elements over a (streamed) base into an mp4.

    Per-frame: read one base RGBA frame (or a solid canvas), draw each visible
    element, pipe the result into an ffmpeg H.264 encoder. Base audio is copied
    through when a base clip is present. Returns the output Path."""
    import subprocess
    from PIL import Image
    from app.config import settings
    W, H = _wh(payload.get("aspect", "9:16"))
    fps = int(payload.get("fps", 30))
    dur = float(payload.get("duration_s", 8))
    n = max(1, int(dur * fps))
    els = payload.get("elements", [])
    base = payload.get("base")  # absolute path to a clip, or None
    out = settings.outputs_path / f"anim_{job_id}.mp4"
    # base frame reader (rawvideo rgba) or None
    bproc = None
    if base:
        bproc = subprocess.Popen(
            ["ffmpeg", "-i", str(base), "-vf",
             f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={fps}",
             "-f", "rawvideo", "-pix_fmt", "rgba", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen(
        ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
         *(["-i", str(base), "-map", "0:v", "-map", "1:a?", "-shortest"] if base else []),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(out)], stdin=subprocess.PIPE)
    fb = W * H * 4
    for i in range(n):
        t = i / fps
        if bproc:
            raw = bproc.stdout.read(fb)
            frame = (Image.frombytes("RGBA", (W, H), raw) if len(raw) == fb
                     else Image.new("RGBA", (W, H), (2, 6, 13, 255)))
        else:
            frame = Image.new("RGBA", (W, H), (2, 6, 13, 255))
        for el in els:
            tr = transform_at(el, t)
            if tr is not None:
                frame.alpha_composite(render_element(el, tr, W, H))
        enc.stdin.write(frame.tobytes())
    enc.stdin.close()
    enc.wait()
    if bproc:
        bproc.terminate()
    return out
