"""fal.ai client wrapper for Seedance 2.0 — v1.3.1+ patched.

PATCH (May 2026): handle non-ASCII filenames during upload.

Why: fal_client uses multipart HTTP form upload internally, which encodes the
filename in ASCII headers. Files like "accréditation.png", "café.jpg",
"été-2026.webp" etc. crash the upload with:
  'ascii' codec can't encode character '\\xe9' in position N

Fix: detect non-ASCII filename, copy to a temp file with an ASCII-safe name,
upload that, then clean up. The original file in assets/images is untouched.

New in v1.2:
- Smart routing: 1 image -> Pro single-image; 2 images -> Lite first-last-frame
- Returns seed used by the model (for reproducibility / regeneration)
"""
import os
import re
import shutil
import tempfile
import unicodedata
import uuid
from pathlib import Path
from typing import Optional

import fal_client
import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings, SSL_VERIFY


if settings.FAL_KEY:
    os.environ["FAL_KEY"] = settings.FAL_KEY


# Endpoints
SEEDANCE_PRO_I2V = "fal-ai/bytedance/seedance/v1/pro/image-to-video"
SEEDANCE_LITE_I2V = "fal-ai/bytedance/seedance/v1/lite/image-to-video"


def _ascii_safe_filename(filename: str) -> str:
    """Convert a filename to an ASCII-only safe equivalent.

    'accréditation.png' -> 'accreditation.png'
    'été 2026.jpg'      -> 'ete_2026.jpg'
    'café.png'          -> 'cafe.png'
    """
    # Normalize unicode (decompose accents into base+accent), then drop accents
    normalized = unicodedata.normalize("NFKD", filename)
    ascii_only = normalized.encode("ASCII", "ignore").decode("ASCII")
    # Replace any leftover non-safe chars with underscore
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", ascii_only)
    # Collapse double underscores
    safe = re.sub(r"_+", "_", safe).strip("_")
    return safe or "image.png"


def _filename_is_ascii_safe(name: str) -> bool:
    try:
        name.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


class FalSeedanceClient:
    @staticmethod
    async def upload_image(image_path: Path) -> str:
        """Upload to fal storage. Handles non-ASCII filenames transparently."""
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        # If filename has non-ASCII chars, copy to a safe-named temp file first.
        # The original file in assets/images is never modified.
        cleanup_temp_path: Optional[Path] = None
        if _filename_is_ascii_safe(image_path.name):
            upload_path = image_path
        else:
            safe_name = _ascii_safe_filename(image_path.name)
            unique = uuid.uuid4().hex[:8]
            temp_dir = Path(tempfile.gettempdir())
            upload_path = temp_dir / f"deepotus_{unique}_{safe_name}"
            shutil.copy2(image_path, upload_path)
            cleanup_temp_path = upload_path
            logger.info(
                f"Filename has non-ASCII chars; renamed for upload: "
                f"'{image_path.name}' -> '{upload_path.name}'"
            )

        try:
            logger.info(f"Uploading image to fal storage: {upload_path.name}")
            url = await fal_client.upload_file_async(str(upload_path))
            logger.info(f"Image uploaded: {url}")
            return url
        finally:
            # Always clean up the temp file, even on failure
            if cleanup_temp_path is not None and cleanup_temp_path.exists():
                try:
                    cleanup_temp_path.unlink()
                except Exception as e:
                    logger.warning(f"Could not clean up temp file {cleanup_temp_path}: {e}")

    @staticmethod
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=30),
        reraise=True,
    )
    async def generate_video(
        image_url: str,
        prompt: str,
        negative_prompt: str = "",
        end_image_url: Optional[str] = None,
        duration: int = 5,
        aspect_ratio: str = "9:16",
        resolution: str = "1080p",
        seed: Optional[int] = None,
    ) -> dict:
        """Submit a job to Seedance 2.0 and wait for completion.

        Routing:
        - end_image_url provided -> Lite endpoint (supports first-last frame)
        - else -> Pro endpoint (best quality on single image)

        Returns dict with at least 'video' field (URL) and possibly 'seed'.
        """
        if not settings.FAL_KEY:
            raise RuntimeError("FAL_KEY is not configured. Set it in .env")

        endpoint = SEEDANCE_LITE_I2V if end_image_url else SEEDANCE_PRO_I2V
        logger.info(
            f"Submitting Seedance job to {endpoint} -- duration={duration}s, "
            f"ratio={aspect_ratio}, res={resolution}, end_image={'yes' if end_image_url else 'no'}"
        )

        arguments = {
            "image_url": image_url,
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
        }
        if negative_prompt:
            arguments["negative_prompt"] = negative_prompt
        if seed is not None:
            arguments["seed"] = seed
        if end_image_url:
            arguments["end_image_url"] = end_image_url

        try:
            result = await fal_client.subscribe_async(
                endpoint,
                arguments=arguments,
                with_logs=True,
                on_queue_update=lambda update: logger.debug(f"fal.ai update: {update}"),
            )
        except Exception as e:
            # Provider-prefix so the UI surfaces a clear, linkable error
            # (credit / quota / billing failures on fal.ai).
            raise RuntimeError(f"fal.ai: {e}") from e
        logger.info(f"Seedance job complete; result keys: {list(result.keys()) if isinstance(result, dict) else type(result)}")
        return result

    @staticmethod
    def extract_video_url(result: dict) -> Optional[str]:
        """fal.ai may return either {video: {url}} or {video_url} or {url}."""
        if not isinstance(result, dict):
            return None
        v = result.get("video")
        if isinstance(v, dict) and "url" in v:
            return v["url"]
        if isinstance(v, str):
            return v
        return result.get("video_url") or result.get("url")

    @staticmethod
    def extract_seed(result: dict) -> Optional[int]:
        """fal.ai sometimes returns the seed used so we can reproduce."""
        if not isinstance(result, dict):
            return None
        seed = result.get("seed")
        if isinstance(seed, (int, float)):
            return int(seed)
        return None

    @staticmethod
    async def download_video(video_url: str, dest_path: Path) -> Path:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Downloading video -> {dest_path}")
        async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=120.0) as client:
            async with client.stream("GET", video_url) as response:
                response.raise_for_status()
                with dest_path.open("wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
        logger.info(f"Download complete: {dest_path} ({dest_path.stat().st_size // 1024} KB)")
        return dest_path
