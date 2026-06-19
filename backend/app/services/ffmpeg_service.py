"""ffmpeg-based merger: combines video + voiceover into final deliverable.

Requires ffmpeg installed and on PATH. The install script handles this on Windows.
"""
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from loguru import logger


class FFmpegMerger:
    @staticmethod
    def check_ffmpeg() -> bool:
        return shutil.which("ffmpeg") is not None

    @staticmethod
    def extend(src: Path, dst: Path, target_s: int,
               mode: str = "loop") -> Path:
        """Extend a (silent) clip to target_s seconds.

        Seedance caps native generation around 10s, so to fit a longer
        HeyGen avatar we generate <=10s once then stretch the runtime here:
          - loop  : seamless repeat until target_s (default)
          - hold  : freeze the last frame until target_s
        Re-encodes (precise cut), drops audio (voiceover is added later).
        """
        if not src.exists():
            raise FileNotFoundError(f"Clip not found: {src}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        if mode == "hold":
            cmd = [
                "ffmpeg", "-y", "-i", str(src),
                "-vf", f"tpad=stop_mode=clone:stop_duration={target_s}",
                "-t", str(target_s),
            ]
        else:  # loop
            cmd = [
                "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(src),
                "-t", str(target_s),
            ]
        cmd += [
            "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(dst),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True,
                           text=True, timeout=300)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"ffmpeg extend failed: {(e.stderr or '')[-300:]}") from e
        if not dst.exists():
            raise RuntimeError("ffmpeg extend produced no output")
        logger.info(f"Extended {src.name} -> {target_s}s ({mode}) {dst.name}")
        return dst

    @staticmethod
    def merge(
        video_path: Path,
        audio_path: Optional[Path],
        output_path: Path,
        loop_audio: bool = False,
    ) -> Path:
        """Merge a video file with an optional audio track.

        - If audio_path is None: just copies the video as the final output.
        - Audio is mixed at full volume; original video audio is replaced.
        - Output is H.264/AAC mp4, web-friendly for X.
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if audio_path is None or not audio_path.exists():
            logger.info(f"No audio — copying video to {output_path}")
            shutil.copy2(video_path, output_path)
            return output_path

        if not FFmpegMerger.check_ffmpeg():
            raise RuntimeError(
                "ffmpeg not found on PATH. Run scripts/install.ps1 to install it."
            )

        logger.info(f"Merging video + audio → {output_path}")

        # Get video duration first to know when to cut audio
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-c:v", "copy",                  # don't re-encode video
            "-c:a", "aac",
            "-b:a", "192k",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",                      # cut to shortest stream
            "-movflags", "+faststart",
            str(output_path),
        ]

        try:
            result = subprocess.run(
                cmd, check=True, capture_output=True, text=True, timeout=120
            )
            logger.debug(f"ffmpeg stderr: {result.stderr[-500:] if result.stderr else ''}")
        except subprocess.CalledProcessError as e:
            logger.error(f"ffmpeg failed: {e.stderr}")
            raise RuntimeError(f"ffmpeg merge failed: {e.stderr[-300:]}") from e

        logger.info(f"Merge complete: {output_path} ({output_path.stat().st_size // 1024} KB)")
        return output_path
