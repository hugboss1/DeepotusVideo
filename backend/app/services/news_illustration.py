"""News illustration engine (v1.7).

The "Seedance-equivalent" for the news pipeline: turns selected headlines into
a branded 1080x1920 animated reel using the same ffmpeg primitives proven by
the v1.6 template renderer (work-dir fonts, drawtext, drawbox, scrolling
ticker, timed fades). Silent by design — the HeyGen avatar carries the audio
when composed via a v1.6 template / Composition.

Default engine is "ffmpeg" (no heavy deps). "remotion" is an optional richer
engine: it is wired as a clear, actionable error until a Remotion project is
provided (see render()), honouring the v1.7 scope decision.
"""
import shutil
import textwrap
from pathlib import Path

from loguru import logger

from app.config import settings
from app.services.template_service import TemplateEngine, _run_ffmpeg_in, _hex

CANVAS_W, CANVAS_H = 1080, 1920
FPS = 30
MAX_CARDS = 12
MIN_PER_CARD = 2.0
MAX_TOTAL_S = 90.0


def _wrap(text: str, width: int = 22, max_lines: int = 4) -> str:
    text = " ".join((text or "").split())
    lines = textwrap.wrap(text, width=width) or [""]
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(".") + "…"
    return "\n".join(lines)


class NewsIllustrationEngine:
    def __init__(self):
        self.tpl = TemplateEngine()  # reuse font/mark resolution

    def render(
        self,
        items: list[dict],
        output_path: Path,
        *,
        per_card_s: float = 3.5,
        bg: str = "#02060d",
        accent: str = "#00e5ff",
        engine: str = "ffmpeg",
    ) -> Path:
        if engine == "remotion":
            # Optional richer engine — intentionally not silently stubbed.
            raise RuntimeError(
                "Remotion engine is optional and not configured. Ship a "
                "Remotion project under remotion/ and set it up, or use "
                "engine='ffmpeg' (default).")
        if not items:
            raise ValueError("No news items provided for illustration")

        items = items[:MAX_CARDS]
        per = max(MIN_PER_CARD, float(per_card_s))
        total = min(round(per * len(items), 2), MAX_TOTAL_S)
        per = round(total / len(items), 3)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        work = Path(settings.outputs_path) / "_tmp_render" / output_path.stem
        if work.exists():
            shutil.rmtree(work, ignore_errors=True)
        work.mkdir(parents=True, exist_ok=True)

        try:
            cmd = self._build_cmd(items, output_path, work, per, total,
                                  _hex(bg, "02060d"), _hex(accent, "00e5ff"))
            logger.info(
                f"Rendering news illustration ({len(items)} cards, "
                f"{total}s) -> {output_path}")
            _run_ffmpeg_in(cmd, output_path, cwd=work)
        finally:
            shutil.rmtree(work, ignore_errors=True)
        return output_path

    def _build_cmd(self, items, output_path, work, per, total, bg, accent):
        font_disp = self.tpl.font_path("Space Grotesk")
        font_mono = self.tpl.font_path("JetBrains Mono")
        shutil.copyfile(font_disp, work / font_disp.name)
        shutil.copyfile(font_mono, work / font_mono.name)
        fd, fm = font_disp.name, font_mono.name

        txt_n = [0]

        def tf(content: str) -> str:
            txt_n[0] += 1
            fn = f"t{txt_n[0]}.txt"
            (work / fn).write_text(content, encoding="utf-8")
            return fn

        inputs = ["-f", "lavfi", "-i",
                  f"color=c=0x{bg}:s={CANVAS_W}x{CANVAS_H}:d={total}:r={FPS}"]
        parts = [f"[0:v]format=yuv420p[v0]"]
        cur = "v0"
        n = 0

        def w(filt: str, label: str):
            nonlocal cur
            parts.append(filt)
            cur = label

        # Brand wordmark (top), graceful if asset missing
        mark = self.tpl.mark_path("marks/wordmark_cyan.png")
        if mark is not None:
            inputs.extend(["-loop", "1", "-t", str(total), "-i", str(mark)])
            n += 1
            parts.append(f"[1:v]scale=360:-1,format=rgba[mk]")
            w(f"[{cur}][mk]overlay=x=(W-w)/2:y=70[v{n}]", f"v{n}")

        # Bottom ticker bar + scrolling concatenated headlines
        n += 1
        w(f"[{cur}]drawbox=x=0:y=1740:w={CANVAS_W}:h=120:"
          f"color=0x050a17@1:t=fill[v{n}]", f"v{n}")
        ticker = "    •    ".join(
            (it.get("title") or "").strip() for it in items if it.get("title"))
        n += 1
        w(f"[{cur}]drawtext=fontfile={fm}:textfile={tf(ticker)}:"
          f"fontsize=34:fontcolor=0x{accent}:"
          f"x='{CANVAS_W}-mod(t*150,{CANVAS_W}+tw)':"
          f"y='1740+(120-th)/2'[v{n}]", f"v{n}")

        # Per-card scenes (timed fades + subtle upward drift)
        for i, it in enumerate(items):
            a = round(i * per, 3)
            b = round(a + per, 3)
            fade = min(0.35, per / 4)
            alpha = (f"if(lt(t,{a}+{fade}),(t-{a})/{fade},"
                     f"if(gt(t,{b}-{fade}),({b}-t)/{fade},1))")
            enable = f"between(t,{a},{b})"
            title = _wrap(it.get("title") or "", 22, 4)
            src = (it.get("source_name") or "").strip()
            meta = f"{i + 1}/{len(items)}" + (f"  ·  {src}" if src else "")

            # accent rule
            n += 1
            w(f"[{cur}]drawbox=x=140:y=560:w={CANVAS_W - 280}:h=6:"
              f"color=0x{accent}@1:t=fill:enable='{enable}'[v{n}]", f"v{n}")
            # headline
            n += 1
            w(f"[{cur}]drawtext=fontfile={fd}:textfile={tf(title)}:"
              f"fontsize=68:fontcolor=0xffffff:line_spacing=14:"
              f"x='(w-tw)/2':y='640-(t-{a})*14':"
              f"borderw=4:bordercolor=0x02060d@0.7:"
              f"alpha='{alpha}':enable='{enable}'[v{n}]", f"v{n}")
            # meta (index · source)
            n += 1
            w(f"[{cur}]drawtext=fontfile={fm}:textfile={tf(meta)}:"
              f"fontsize=34:fontcolor=0x{accent}:"
              f"x='(w-tw)/2':y=470:"
              f"alpha='{alpha}':enable='{enable}'[v{n}]", f"v{n}")

        parts.append(f"[{cur}]format=yuv420p[outv]")
        cmd = [
            "ffmpeg", "-y", *inputs,
            "-filter_complex", ";".join(parts),
            "-map", "[outv]", "-an",
            "-t", str(total),
            "-c:v", "libx264", "-profile:v", "high", "-level", "4.0",
            "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
            "-r", str(FPS), "-movflags", "+faststart",
            str(output_path),
        ]
        return cmd


news_illustration_engine = NewsIllustrationEngine()
