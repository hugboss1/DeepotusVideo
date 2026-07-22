"""Google GenAI native video client — W-a (v1.19).

Veo 3.1 through the Generative Language API (AI Studio key, the same
GEMINI_API_KEY the summarizer/planner already use). Contract mirrors
FalSeedanceClient (generate_video / extract_video_url / extract_seed /
download_video) so the pipeline only branches on where the image goes:
fal uploads it to fal storage, Google takes inline base64 bytes — the
user's image never transits a third party for Google renders.

API surface proven live on 22/07/2026 with Olivier's key:
  POST /v1beta/models/{model}:predictLongRunning  -> {"name": op}
  GET  /v1beta/{op}                                -> {done, response|error}
  GET  {response...video.uri}  (x-goog-api-key)    -> mp4 bytes
("gemini-omni-flash-preview" only supports the Interactions API and cannot
generate video via generateContent — probed the same day; Veo 3.1 is the
Google-native video path. This module is also the shared REST base for the
W-c/W-e Google chantiers.)
"""
import asyncio
import base64
import mimetypes
from pathlib import Path
from typing import Optional

import httpx
from loguru import logger

from app.config import settings, SSL_VERIFY

GOOGLE_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

# Veo renders usually land in well under 2 minutes (the 22/07 probe took 8s)
# but previews can queue; poll gently and give up cleanly after 10 min.
_POLL_INTERVAL_S = 5.0
_POLL_TIMEOUT_S = 600.0


def google_headers() -> dict:
    """Auth headers for every Generative Language API call (key never in URL)."""
    return {"x-goog-api-key": settings.GEMINI_API_KEY}


def build_google_params(duration: int, aspect_ratio: str, resolution: str) -> dict:
    """predictLongRunning `parameters` for Veo 3.1 previews.

    Veo only knows 9:16 / 16:9 — anything else (1:1) renders vertical, the
    app's default orientation. negativePrompt is NOT sent: the 3.1 previews
    reject it with HTTP 400 ("isn't supported by this model", probed live
    22/07/2026 — recette W-a)."""
    return {
        "aspectRatio": aspect_ratio if aspect_ratio in ("9:16", "16:9") else "9:16",
        "durationSeconds": int(duration),
        "resolution": resolution if resolution in ("720p", "1080p") else "720p",
    }


class GoogleVeoClient:
    @staticmethod
    def _require_key():
        if not settings.GEMINI_API_KEY.strip():
            raise RuntimeError(
                "google: GEMINI_API_KEY is not configured "
                "(Settings -> Keys -> Google Gemini)")

    @staticmethod
    def _image_part(image_path: Path) -> dict:
        mime = mimetypes.guess_type(image_path.name)[0] or "image/png"
        data = base64.b64encode(image_path.read_bytes()).decode("ascii")
        return {"bytesBase64Encoded": data, "mimeType": mime}

    @staticmethod
    async def generate_video(
        *,
        image_path: Path,
        prompt: str,
        negative_prompt: str = "",
        duration: int = 8,
        aspect_ratio: str = "9:16",
        resolution: str = "720p",
        model: str = "veo-3.1-fast-generate-preview",
    ) -> dict:
        """Submit an image-to-video job to Veo and wait for the operation.

        Returns {"video": {"url": ...}} like the fal client. All failures
        raise RuntimeError prefixed "google:" so job.error is self-explaining
        (quota / billing / safety block included).
        """
        GoogleVeoClient._require_key()
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        # negative_prompt is accepted for contract parity with the fal client
        # but deliberately dropped — see build_google_params.
        if negative_prompt:
            logger.debug("Veo preview: negative_prompt dropped (unsupported)")
        params = build_google_params(duration, aspect_ratio, resolution)
        body = {
            "instances": [{
                "prompt": prompt,
                "image": GoogleVeoClient._image_part(image_path),
            }],
            "parameters": params,
        }

        url = f"{GOOGLE_API_BASE}/models/{model}:predictLongRunning"
        logger.info(
            f"Submitting Google Veo job to {model} -- duration={duration}s, "
            f"ratio={params['aspectRatio']}, res={params['resolution']}")
        async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=90.0) as client:
            try:
                r = await client.post(url, json=body, headers=google_headers())
            except httpx.HTTPError as e:
                raise RuntimeError(f"google: {e}") from e
            if r.status_code != 200:
                raise RuntimeError(
                    f"google: HTTP {r.status_code} — {_short_error(r)}")
            op_name = (r.json() or {}).get("name")
            if not op_name:
                raise RuntimeError(f"google: no operation name in {r.text[:200]}")

            # Poll the long-running operation until done / timeout.
            waited = 0.0
            while True:
                await asyncio.sleep(_POLL_INTERVAL_S)
                waited += _POLL_INTERVAL_S
                try:
                    pr = await client.get(f"{GOOGLE_API_BASE}/{op_name}",
                                          headers=google_headers())
                except httpx.HTTPError as e:
                    raise RuntimeError(f"google: poll failed — {e}") from e
                if pr.status_code != 200:
                    raise RuntimeError(
                        f"google: poll HTTP {pr.status_code} — {_short_error(pr)}")
                op = pr.json() or {}
                if op.get("done"):
                    break
                if waited >= _POLL_TIMEOUT_S:
                    raise RuntimeError(
                        f"google: video operation timed out after "
                        f"{int(_POLL_TIMEOUT_S)}s ({op_name})")

        if op.get("error"):
            err = op["error"]
            raise RuntimeError(
                f"google: {err.get('message') or err} "
                f"(code {err.get('code', '?')})")
        resp = op.get("response") or {}
        gvr = resp.get("generateVideoResponse") or {}
        samples = gvr.get("generatedSamples") or []
        uri = (samples[0].get("video") or {}).get("uri") if samples else None
        if not uri:
            # Safety-filtered renders come back done+empty; surface why.
            reason = gvr.get("raiMediaFilteredReasons") or resp
            raise RuntimeError(f"google: no video in response — {str(reason)[:300]}")
        logger.info(f"Google Veo job complete after ~{int(waited)}s -> {uri[:80]}...")
        return {"video": {"url": uri}}

    @staticmethod
    def extract_video_url(result: dict) -> Optional[str]:
        if not isinstance(result, dict):
            return None
        v = result.get("video")
        if isinstance(v, dict) and "url" in v:
            return v["url"]
        return None

    @staticmethod
    def extract_seed(result: dict) -> Optional[int]:
        return None  # the preview API does not echo a seed

    @staticmethod
    async def download_video(video_url: str, dest_path: Path) -> Path:
        """Download the generated file (the uri requires the API key header)."""
        GoogleVeoClient._require_key()
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Downloading Google video -> {dest_path}")
        async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=300.0,
                                     follow_redirects=True) as client:
            async with client.stream("GET", video_url,
                                     headers=google_headers()) as response:
                if response.status_code != 200:
                    await response.aread()
                    raise RuntimeError(
                        f"google: download HTTP {response.status_code}")
                with dest_path.open("wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
        logger.info(
            f"Download complete: {dest_path} ({dest_path.stat().st_size // 1024} KB)")
        return dest_path


def _short_error(r: httpx.Response) -> str:
    """First meaningful line of a Google error body (message field if JSON)."""
    try:
        msg = (r.json() or {}).get("error", {}).get("message")
        if msg:
            return str(msg)[:300]
    except Exception:
        pass
    return (r.text or "")[:300]
