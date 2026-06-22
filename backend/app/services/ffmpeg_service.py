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
    def _has_audio(path: Path) -> bool:
        """True if the media file carries at least one audio stream."""
        try:
            r = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "a",
                 "-show_entries", "stream=index", "-of", "csv=p=0", str(path)],
                capture_output=True, text=True, timeout=30)
            return bool(r.stdout.strip())
        except Exception:
            return False

    @staticmethod
    def merge(
        video_path: Path,
        audio_path: Optional[Path],
        output_path: Path,
        loop_audio: bool = False,
        music_path: Optional[Path] = None,
        music_volume_db: float = -14.0,
        keep_video_audio: bool = False,
    ) -> Path:
        """Merge a video with an optional voiceover and/or looped background music.

        - audio_path: a voiceover track streamed over the video.
        - music_path: a BGM track, looped (`-stream_loop -1`) to fill and mixed
          in at `music_volume_db`. `-shortest` cuts the output to the video
          length, so the music always matches the clip duration.
        - keep_video_audio: mix in the video's own audio too (e.g. a HeyGen
          avatar speaking) instead of dropping it.
        - Output is H.264/AAC mp4, web-friendly for X.
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        has_vo = audio_path is not None and Path(audio_path).exists()
        has_bgm = music_path is not None and Path(music_path).exists()

        if not has_vo and not has_bgm:
            logger.info(f"No audio — copying video to {output_path}")
            shutil.copy2(video_path, output_path)
            return output_path

        if not FFmpegMerger.check_ffmpeg():
            raise RuntimeError(
                "ffmpeg not found on PATH. Run scripts/install.ps1 to install it."
            )

        # Fast path: a single voiceover, nothing else → stream-copy video.
        if has_vo and not has_bgm and not keep_video_audio:
            cmd = [
                "ffmpeg", "-y",
                "-i", str(video_path),
                "-i", str(audio_path),
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-map", "0:v:0", "-map", "1:a:0",
                "-shortest", "-movflags", "+faststart",
                str(output_path),
            ]
        else:
            inputs = ["-i", str(video_path)]
            fc: list[str] = []
            alabels: list[str] = []
            idx = 1
            if keep_video_audio and FFmpegMerger._has_audio(video_path):
                fc.append("[0:a]aresample=async=1[avid]")
                alabels.append("[avid]")
            if has_vo:
                inputs += ["-i", str(audio_path)]
                fc.append(f"[{idx}:a]aresample=async=1[avo]")
                alabels.append("[avo]")
                idx += 1
            if has_bgm:
                inputs += ["-stream_loop", "-1", "-i", str(music_path)]
                fc.append(f"[{idx}:a]volume={music_volume_db}dB,"
                          f"aresample=async=1[abg]")
                alabels.append("[abg]")
                idx += 1
            if not alabels:
                logger.info(f"No usable audio — copying video to {output_path}")
                shutil.copy2(video_path, output_path)
                return output_path
            if len(alabels) > 1:
                fc.append(f"{''.join(alabels)}amix=inputs={len(alabels)}:"
                          f"duration=longest:normalize=0[outa]")
                amap = "[outa]"
            else:
                amap = alabels[0]
            cmd = [
                "ffmpeg", "-y", *inputs,
                "-filter_complex", ";".join(fc),
                "-map", "0:v:0", "-map", amap,
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-shortest", "-movflags", "+faststart",
                str(output_path),
            ]

        logger.info(f"Merging → {output_path}")
        try:
            result = subprocess.run(
                cmd, check=True, capture_output=True, text=True, timeout=180
            )
            logger.debug(f"ffmpeg stderr: {result.stderr[-400:] if result.stderr else ''}")
        except subprocess.CalledProcessError as e:
            logger.error(f"ffmpeg failed: {e.stderr}")
            raise RuntimeError(f"ffmpeg merge failed: {(e.stderr or '')[-300:]}") from e

        logger.info(f"Merge complete: {output_path} ({output_path.stat().st_size // 1024} KB)")
        return output_path

    # ── Episodes: narrated illustrated scenes ──────────────────────────────
    @staticmethod
    def probe_dur(path: Path) -> float:
        """Media duration in seconds (0.0 on any error)."""
        try:
            r = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=nw=1:nk=1", str(path)],
                capture_output=True, text=True, timeout=30)
            return float((r.stdout or "0").strip() or 0)
        except Exception:
            return 0.0

    @staticmethod
    def scene_clip(image, audio, out: Path, *, motion: str = "kenburns",
                   dur: float = 4.0, w: int = 1080, h: int = 1920,
                   fps: int = 30, bg: str = "0a0a0a") -> Path:
        """Render one episode scene: a still image with a slow Ken Burns zoom
        (or static) over its narration audio, cut to `dur`. If `image` is
        missing, a solid background is used so the narration still plays."""
        out.parent.mkdir(parents=True, exist_ok=True)
        dur = max(0.5, round(float(dur), 3))
        frames = max(1, int(round(dur * fps)))
        has_audio = audio is not None and Path(audio).exists()
        if image and Path(image).exists():
            if motion == "still":
                vf = (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
                      f"crop={w}:{h},format=yuv420p")
            else:  # kenburns (also the v1 fallback for seedance scenes)
                vf = (f"scale={w*2}:{h*2}:force_original_aspect_ratio=increase,"
                      f"crop={w*2}:{h*2},zoompan=z='min(zoom+0.0010,1.12)':"
                      f"d={frames}:s={w}x{h}:fps={fps},format=yuv420p")
            ins = ["-loop", "1", "-i", str(image)]
            vfilter = ["-vf", vf]
        else:
            ins = ["-f", "lavfi", "-i", f"color=c=0x{bg}:s={w}x{h}:r={fps}"]
            vfilter = []
        cmd = ["ffmpeg", "-y", *ins]
        if has_audio:
            cmd += ["-i", str(audio)]
        cmd += vfilter + ["-map", "0:v"]
        if has_audio:
            cmd += ["-map", "1:a", "-c:a", "aac", "-b:a", "192k"]
        else:
            cmd += ["-an"]
        cmd += ["-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                "-t", str(dur), "-r", str(fps), "-movflags", "+faststart", str(out)]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"scene_clip failed: {(e.stderr or '')[-300:]}") from e
        return out

    @staticmethod
    def concat_clips(clips: list, out: Path) -> Path:
        """Concatenate scene clips (same codec params) into the final video."""
        out.parent.mkdir(parents=True, exist_ok=True)
        lst = out.with_suffix(".concat.txt")
        lst.write_text("".join(f"file '{Path(c).as_posix()}'\n" for c in clips),
                       encoding="utf-8")
        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
               "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=600)
        finally:
            try:
                lst.unlink()
            except Exception:
                pass
        return out
