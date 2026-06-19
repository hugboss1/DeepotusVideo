"""Composition service — combines Seedance and HeyGen clips into one final video.

Supports two composition modes:
1. SEQUENTIAL: Avatar speaks then Seedance animation plays (or vice versa).
   Optional brief transition (cyan flash) between the two segments.
2. SPLIT_SCREEN: Two clips stacked vertically (or side-by-side).
   - vstack: 50% top (Seedance) / 50% bottom (avatar)
   - hstack: 50% left / 50% right

All composition done via ffmpeg filter graph — single process, no intermediate
files beyond inputs.
"""
import subprocess
from pathlib import Path
from typing import Literal, Optional

from loguru import logger


class CompositionService:
    """Compose multiple clips into one final video via ffmpeg."""

    @staticmethod
    def sequential(
        clip_a: Path,
        clip_b: Path,
        output: Path,
        *,
        aspect_ratio: str = "9:16",
        transition_duration_s: float = 0.4,
        target_duration_s: Optional[int] = None,
    ) -> Path:
        """Concatenate clip_a -> clip_b with a brief cyan flash transition.

        Both clips are normalized to the same dimensions before concat.
        Result is encoded to a single MP4 in `output`.

        NOTE: sequential output is VIDEO-ONLY (silent). For a spoken-avatar
        composition use split_screen(), which routes the avatar's audio track.
        (Per-segment audio in the sequential concat is a planned refinement;
        concat with a=1 requires every segment to carry an audio stream, so it
        needs per-clip probing to insert silence where a clip has none.)
        """
        if not clip_a.exists():
            raise FileNotFoundError(f"Clip A not found: {clip_a}")
        if not clip_b.exists():
            raise FileNotFoundError(f"Clip B not found: {clip_b}")

        # Target dimensions
        dims = {
            "9:16": (1080, 1920),
            "1:1": (1080, 1080),
            "16:9": (1920, 1080),
        }
        w, h = dims.get(aspect_ratio, dims["9:16"])

        output.parent.mkdir(parents=True, exist_ok=True)

        # Build filter graph: scale+letterbox each input, a brief cyan flash,
        # then concat a -> flash -> b. Video-only (a=0) so it never breaks on a
        # clip that lacks audio — see the docstring note re: spoken compositions.
        filter_complex_simple = (
            f"[0:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps=30,"
            f"format=yuv420p[a];"
            f"[1:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps=30,"
            f"format=yuv420p[b];"
            f"color=c=0x00e5ff:s={w}x{h}:d={transition_duration_s}:r=30,"
            f"format=yuv420p[flash];"
            f"[a][flash][b]concat=n=3:v=1:a=0[outv]"
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", str(clip_a),
            "-i", str(clip_b),
            "-filter_complex", filter_complex_simple,
            "-map", "[outv]",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
        ]
        if target_duration_s:
            cmd.extend(["-t", str(target_duration_s)])
        cmd.append(str(output))

        logger.info(f"Composition sequential: {clip_a.name} + {clip_b.name} -> {output.name}")
        return _run_ffmpeg(cmd, output)

    @staticmethod
    def split_screen(
        clip_top: Path,
        clip_bottom: Path,
        output: Path,
        *,
        layout: Literal["vstack", "hstack"] = "vstack",
        aspect_ratio: str = "9:16",
        target_duration_s: Optional[int] = None,
        audio_source: Literal["top", "bottom"] = "bottom",
    ) -> Path:
        """Stack two clips side-by-side (hstack) or vertically (vstack).

        For deepotus reaction-style: vstack with Seedance animation on top,
        HeyGen avatar on bottom. Audio defaults to bottom (the avatar speaking).
        """
        if not clip_top.exists():
            raise FileNotFoundError(f"Top clip not found: {clip_top}")
        if not clip_bottom.exists():
            raise FileNotFoundError(f"Bottom clip not found: {clip_bottom}")

        dims = {
            "9:16": (1080, 1920),
            "1:1": (1080, 1080),
            "16:9": (1920, 1080),
        }
        full_w, full_h = dims.get(aspect_ratio, dims["9:16"])

        if layout == "vstack":
            half_w, half_h = full_w, full_h // 2
        else:  # hstack
            half_w, half_h = full_w // 2, full_h

        output.parent.mkdir(parents=True, exist_ok=True)

        # Audio routing
        audio_idx = 1 if audio_source == "bottom" else 0
        audio_map = f"-map {audio_idx}:a?"

        filter_complex = (
            f"[0:v]scale={half_w}:{half_h}:force_original_aspect_ratio=decrease,"
            f"pad={half_w}:{half_h}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps=30,"
            f"format=yuv420p[top];"
            f"[1:v]scale={half_w}:{half_h}:force_original_aspect_ratio=decrease,"
            f"pad={half_w}:{half_h}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps=30,"
            f"format=yuv420p[bot];"
            f"[top][bot]{layout}=inputs=2[outv]"
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", str(clip_top),
            "-i", str(clip_bottom),
            "-filter_complex", filter_complex,
            "-map", "[outv]",
        ]
        # Add audio mapping
        cmd.extend(audio_map.split())
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
        ])
        if target_duration_s:
            cmd.extend(["-t", str(target_duration_s)])
        cmd.append(str(output))

        logger.info(
            f"Composition {layout}: {clip_top.name} | {clip_bottom.name} -> {output.name} "
            f"(audio from {audio_source})"
        )
        return _run_ffmpeg(cmd, output)


def _run_ffmpeg(cmd: list[str], output: Path) -> Path:
    """Execute ffmpeg, raise informative error on failure."""
    try:
        proc = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        if not output.exists():
            raise RuntimeError(f"ffmpeg succeeded but output missing: {output}")
        logger.info(f"ffmpeg OK: {output} ({output.stat().st_size // 1024} KB)")
        return output
    except subprocess.CalledProcessError as e:
        stderr_tail = (e.stderr or "")[-1500:]
        raise RuntimeError(f"ffmpeg failed (exit {e.returncode}):\n{stderr_tail}") from e
    except FileNotFoundError:
        raise RuntimeError("ffmpeg not found in PATH. Install ffmpeg first.")
