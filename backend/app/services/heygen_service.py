"""HeyGen API client wrapper for v1.4 'Composition Edition'.

Implements:
- List avatars and voices
- Generate avatar videos (Avatar III / IV / Photo Avatar)
- Photo avatar creation flow (group + look + train)
- Video translation
- Status polling and video download

API docs: https://docs.heygen.com/reference
Auth: X-Api-Key header.

Pricing reminder for users: HeyGen is pay-as-you-go in credits; Avatar V ~6 credits/min
video. The HEYGEN_API_KEY must be set in .env for this service to activate.
"""
import asyncio
import time
from pathlib import Path
from typing import Optional, Literal

import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings, SSL_VERIFY


HEYGEN_BASE = "https://api.heygen.com"
HEYGEN_UPLOAD_BASE = "https://upload.heygen.com"

# v1.15.1: HeyGen's /v2/avatars is genuinely SLOW for accounts with a large
# avatar catalogue — 60s+ responses are normal (the payload is ~500 KB). The
# old 15s timeout always fired, so the UI showed "0 avatars / check key" even
# with a perfectly valid key. We now allow a long timeout AND cache the parsed
# lists in-process so the slow fetch happens once per session, not on every
# tab open. Health checks use remaining_quota() (fast) instead of listing.
_LIST_TIMEOUT = 120.0
# 6 h: the list is re-warmed on every app launch anyway, so a long TTL just
# means "instant for the whole session" — matching what the guide promises.
# Freshness is preserved by invalidate_list_cache() after creating an avatar;
# external catalogue changes are picked up on the next launch.
_LIST_CACHE_TTL = 21600.0
_LIST_CACHE: dict[str, tuple[float, list]] = {}


def invalidate_list_cache() -> None:
    """Drop cached avatar/voice lists (call after creating a new avatar so it
    shows up immediately instead of waiting for the TTL)."""
    _LIST_CACHE.clear()


class HeyGenError(RuntimeError):
    """Raised when HeyGen API returns a non-success response."""


class HeyGenClient:
    """Thin async wrapper around the HeyGen REST API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.HEYGEN_API_KEY
        if not self.api_key:
            raise RuntimeError(
                "HEYGEN_API_KEY is not configured. Set it in backend/.env"
            )
        self.headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @staticmethod
    def is_enabled() -> bool:
        return bool(settings.HEYGEN_API_KEY)

    # ---------- helpers ----------

    async def _get(self, path: str, params: Optional[dict] = None,
                   timeout: float = 60.0) -> dict:
        async with httpx.AsyncClient(timeout=timeout, verify=SSL_VERIFY) as client:
            r = await client.get(f"{HEYGEN_BASE}{path}",
                                 headers=self.headers, params=params)
            return self._parse(r)

    async def _post(self, path: str, body: Optional[dict] = None) -> dict:
        async with httpx.AsyncClient(timeout=120.0, verify=SSL_VERIFY) as client:
            r = await client.post(f"{HEYGEN_BASE}{path}",
                                  headers=self.headers, json=body or {})
            return self._parse(r)

    @staticmethod
    def _parse(response: httpx.Response) -> dict:
        try:
            data = response.json()
        except ValueError:
            raise HeyGenError(f"Non-JSON response ({response.status_code}): {response.text[:200]}")
        if response.status_code >= 400:
            err_msg = data.get("error") or data.get("message") or str(data)
            raise HeyGenError(f"HeyGen {response.status_code}: {err_msg}")
        # HeyGen responses may have a top-level 'data' key
        if "data" in data and "code" not in data:
            return data["data"]
        return data

    # ---------- AVATARS & VOICES ----------

    async def list_avatars(self, *, use_cache: bool = True) -> list[dict]:
        """List all available avatars (including instant avatars).

        Each item typically: avatar_id, avatar_name, gender, preview_image_url, preview_video_url.

        HeyGen's /v2/avatars can take 60s+ for accounts with many avatars, so
        this uses a long timeout (_LIST_TIMEOUT) and caches the result in
        process (_LIST_CACHE_TTL). The first load after start is slow; later
        loads are instant. Pass use_cache=False to force a fresh fetch.
        """
        if use_cache:
            hit = _LIST_CACHE.get("avatars")
            if hit and (time.monotonic() - hit[0]) < _LIST_CACHE_TTL:
                logger.debug("HeyGen avatar list served from cache.")
                return hit[1]
        logger.info("Fetching HeyGen avatar list...")
        result = await self._get("/v2/avatars", timeout=_LIST_TIMEOUT)
        avatars = result.get("avatars", []) if isinstance(result, dict) else []
        # /v2/avatars also returns a `talking_photos` array (uploaded photo
        # avatars). It was being dropped, so created talking photos never
        # showed up in any selector. Normalize them into the avatar list.
        tps = result.get("talking_photos", []) if isinstance(result, dict) else []
        norm_tps = []
        for tp in tps:
            tid = tp.get("talking_photo_id") or tp.get("id")
            if not tid:
                continue
            tname = tp.get("talking_photo_name") or tp.get("name") or "Talking Photo"
            norm_tps.append({
                "avatar_id": tid,
                "avatar_name": tname,
                "name": tname,
                "gender": tp.get("gender"),
                "preview_image_url": tp.get("preview_image_url"),
                "preview_video_url": None,
                "avatar_type": "talking_photo",
            })
        logger.info(
            f"Got {len(avatars)} avatars + {len(norm_tps)} talking photos from HeyGen.")
        out = avatars + norm_tps
        # Also surface the account's Photo-Avatar GROUPS (the user's *generated*
        # avatars), which live outside /v2/avatars. Best-effort — a groups
        # failure must never break the main avatar list.
        try:
            group_looks = await self._list_group_looks()
            if group_looks:
                logger.info(f"Merged {len(group_looks)} photo-avatar group looks.")
                out = group_looks + out  # the user's own avatars first
        except Exception as e:
            logger.warning(f"Photo-avatar groups not merged: {e}")
        _LIST_CACHE["avatars"] = (time.monotonic(), out)
        return out

    async def list_voices(self, *, use_cache: bool = True) -> list[dict]:
        """List all available voices.
        Each item: voice_id, name, language, gender, preview_audio.
        Long timeout + in-process cache, same rationale as list_avatars."""
        if use_cache:
            hit = _LIST_CACHE.get("voices")
            if hit and (time.monotonic() - hit[0]) < _LIST_CACHE_TTL:
                logger.debug("HeyGen voice list served from cache.")
                return hit[1]
        logger.info("Fetching HeyGen voice list...")
        result = await self._get("/v2/voices", timeout=_LIST_TIMEOUT)
        voices = result.get("voices", []) if isinstance(result, dict) else []
        logger.info(f"Got {len(voices)} voices from HeyGen.")
        _LIST_CACHE["voices"] = (time.monotonic(), voices)
        return voices

    async def remaining_quota(self) -> dict:
        """Lightweight authenticated probe: verifies the key is valid and the
        API is reachable WITHOUT the heavy /v2/avatars listing (which can take
        60s+). Returns e.g. {"remaining_quota": 766, "details": {...}}.
        Used by the health check so the HeyGen status badge stays responsive.
        """
        result = await self._get("/v2/user/remaining_quota", timeout=20.0)
        return result if isinstance(result, dict) else {}

    async def list_photo_avatar_groups(self) -> list[dict]:
        """List photo avatar groups (collections of looks for one subject)."""
        result = await self._get("/v2/avatar_group.list")
        groups = result.get("avatar_group_list", []) if isinstance(result, dict) else []
        return groups

    async def _list_group_looks(self, *, max_groups: int = 30) -> list[dict]:
        """Fetch the looks inside the account's photo-avatar groups (the user's
        generated avatars) and normalise them into the avatar-list shape so they
        show up in the picker alongside stock/instant avatars."""
        groups = await self.list_photo_avatar_groups()
        out: list[dict] = []
        for grp in groups[:max_groups]:
            gid = grp.get("id") or grp.get("group_id")
            if not gid:
                continue
            looks = []
            for path in (f"/v2/avatar_group/{gid}/avatars",
                         f"/v2/photo_avatar/avatar_group/avatars?group_id={gid}"):
                try:
                    res = await self._get(path, timeout=30.0)
                except Exception:
                    continue
                looks = (res.get("avatar_list") or res.get("avatars") or []) \
                    if isinstance(res, dict) else []
                if looks:
                    break
            gname = grp.get("name") or "Photo avatar"
            for lk in looks:
                lid = lk.get("id") or lk.get("avatar_id")
                if not lid:
                    continue
                lname = lk.get("name")
                # names inside a group are often all identical ("Photo Avatar");
                # identical avatar_names break find-by-name selection, so fall
                # back to a short id suffix to keep every entry distinct.
                disp = (f"{gname} · {lname}" if lname and lname != gname
                        else f"{gname} ({str(lid)[-5:]})")
                out.append({
                    "avatar_id": lid,
                    "avatar_name": disp,
                    "name": gname,
                    "gender": lk.get("gender"),
                    "preview_image_url": (lk.get("image_url")
                                          or lk.get("preview_image_url")),
                    "preview_video_url": lk.get("motion_preview_url"),
                    "avatar_type": "avatar",
                    "from_group": True,
                })
        return out

    # ---------- VIDEO GENERATION ----------

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=4, max=30), reraise=True)
    async def generate_video(
        self,
        text: str,
        avatar_id: str,
        voice_id: str,
        *,
        avatar_type: Literal["avatar", "talking_photo"] = "avatar",
        aspect_ratio: str = "9:16",
        speed: float = 1.0,
        background_color: str = "#02060d",
        use_avatar_iv: bool = False,
    ) -> str:
        """Submit a video generation request. Returns the video_id immediately.

        Use poll_video_status() to wait for completion and get the video URL.
        """
        # Map aspect ratio to dimensions
        dimensions = {
            "9:16": {"width": 1080, "height": 1920},
            "1:1":  {"width": 1080, "height": 1080},
            "16:9": {"width": 1920, "height": 1080},
        }
        dim = dimensions.get(aspect_ratio, dimensions["9:16"])

        character = {
            "type": avatar_type,
        }
        if avatar_type == "talking_photo":
            character["talking_photo_id"] = avatar_id
        else:
            character["avatar_id"] = avatar_id
            character["avatar_style"] = "normal"

        voice_obj = {
            "type": "text",
            "input_text": text[:4900],  # API limit ~5000 chars
            "voice_id": voice_id,
            "speed": speed,
        }
        # SSML pauses: when the script carries <break>/<speak> tags ("Precise"
        # pacing in the News-script node), flag the voice as SSML so HeyGen
        # honours the pauses instead of reading the tags aloud. Requires a
        # voice with support_pause=true (otherwise HeyGen ignores the breaks).
        _ssml = (text or "").strip()
        if "<break" in _ssml or _ssml.startswith("<speak"):
            if not _ssml.startswith("<speak"):
                _ssml = "<speak>" + _ssml + "</speak>"
            voice_obj["input_text"] = _ssml[:4900]
            voice_obj["input_type"] = "ssml"

        body = {
            "video_inputs": [{
                "character": character,
                "voice": voice_obj,
                "background": {
                    "type": "color",
                    "value": background_color,
                },
            }],
            "dimension": dim,
            "aspect_ratio": aspect_ratio,
            "test": False,
        }
        if use_avatar_iv and avatar_type == "talking_photo":
            body["video_inputs"][0]["use_avatar_iv_model"] = True

        logger.info(f"Submitting HeyGen video: avatar={avatar_id}, voice={voice_id}, "
                    f"aspect={aspect_ratio}, len={len(text)} chars")
        result = await self._post("/v2/video/generate", body)
        video_id = result.get("video_id")
        if not video_id:
            raise HeyGenError(f"No video_id in HeyGen response: {result}")
        logger.info(f"HeyGen video submitted: {video_id}")
        return video_id

    async def poll_video_status(
        self,
        video_id: str,
        *,
        poll_every_s: float = 4.0,
        timeout_s: float = 600.0,
    ) -> dict:
        """Poll HeyGen until the video is complete or fails.

        Returns the final status dict containing video_url, thumbnail_url, etc.
        """
        elapsed = 0.0
        last_status = None
        while elapsed < timeout_s:
            params = {"video_id": video_id}
            result = await self._get("/v1/video_status.get", params=params)
            # /v1/video_status.get returns {"code":100,"data":{"status":...,
            # "video_url":...}}. _parse leaves that envelope intact because it
            # has a `code`, so the status lives one level in. Without this the
            # status is always None and the poll always times out even though
            # HeyGen finished (the completion email still arrives).
            payload = (result.get("data")
                       if isinstance(result.get("data"), dict) else result)
            status = payload.get("status")
            last_status = status
            if status in ("completed", "success", "done"):
                logger.info(f"HeyGen video {video_id} complete.")
                return payload
            if status in ("failed", "error"):
                err = (payload.get("error") or payload.get("message")
                       or "unknown error")
                raise HeyGenError(f"HeyGen video {video_id} failed: {err}")
            logger.debug(f"HeyGen status {video_id}: {status} ({elapsed:.0f}s)")
            await asyncio.sleep(poll_every_s)
            elapsed += poll_every_s
        raise HeyGenError(
            f"HeyGen video {video_id} timed out after {timeout_s}s "
            f"(last status: {last_status})")

    async def download_video(self, video_url: str, dest_path: Path) -> Path:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Downloading HeyGen video -> {dest_path}")
        async with httpx.AsyncClient(timeout=180.0, verify=SSL_VERIFY) as client:
            async with client.stream("GET", video_url) as response:
                response.raise_for_status()
                with dest_path.open("wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
        logger.info(f"HeyGen download complete: {dest_path} ({dest_path.stat().st_size // 1024} KB)")
        return dest_path

    # ---------- PHOTO AVATAR ----------

    async def upload_asset(self, file_path: Path, content_type: str = "image/png") -> dict:
        """Upload a local file to HeyGen asset storage.

        Returns {"url": <asset url>, "image_key": <storage key or None>}.
        The photo-avatar generate endpoint requires the `image_key`, not the
        URL, so both are surfaced. HeyGen uses a separate upload endpoint that
        accepts the raw bytes with a Content-Type header (no multipart form).
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Asset file not found: {file_path}")
        # Infer content type from extension if generic was passed
        ext = file_path.suffix.lower()
        if content_type == "image/png":
            content_type = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".webp": "image/webp",
            }.get(ext, "image/png")

        url = f"{HEYGEN_UPLOAD_BASE}/v1/asset"
        headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": content_type,
        }
        logger.info(f"Uploading asset to HeyGen: {file_path.name} ({content_type})")
        async with httpx.AsyncClient(timeout=180.0, verify=SSL_VERIFY) as client:
            with file_path.open("rb") as f:
                r = await client.post(url, headers=headers, content=f.read())
            data = self._parse(r)
        # The v1 /v1/asset endpoint wraps the payload as
        # {"code":100,"data":{...,"url":...}}. _parse leaves that envelope
        # intact (it only unwraps `data` when there is no `code` key), so
        # look one level deeper when the URL isn't at the top.
        payload = data.get("data") if isinstance(data.get("data"), dict) else data
        asset_url = (payload.get("url") or payload.get("asset_url")
                     or payload.get("image_url"))
        image_key = payload.get("image_key") or payload.get("key")
        if not asset_url:
            raise HeyGenError(f"No URL in upload response: {data}")
        logger.info(f"Asset uploaded: {asset_url} (image_key={image_key})")
        return {"url": asset_url, "image_key": image_key}

    async def create_photo_avatar_group(
        self, name: str, image_key: Optional[str] = None
    ) -> str:
        """Create a new photo avatar group from an uploaded image.

        HeyGen's /v2/photo_avatar/avatar_group/create requires `image_key`
        (the storage key from the asset upload) as the group's base look.
        Returns the group_id.
        """
        body = {"name": name}
        if image_key:
            body["image_key"] = image_key
        result = await self._post("/v2/photo_avatar/avatar_group/create", body)
        gid = result.get("group_id") or result.get("id")
        if not gid:
            raise HeyGenError(f"No group_id in response: {result}")
        return gid

    async def upload_photo_to_group(
        self,
        group_id: str,
        name: str,
        *,
        image_key: Optional[str] = None,
        image_url: Optional[str] = None,
    ) -> str:
        """Add a photo (look) to an existing avatar group. Returns the photo_avatar_id.

        HeyGen's /v2/photo_avatar/photo/generate requires `image_key` (the
        storage key returned by the asset upload), not the URL. `image_url`
        is sent as a fallback only when no key is available.
        """
        if not image_key and not image_url:
            raise HeyGenError("upload_photo_to_group needs image_key or image_url")
        body = {"group_id": group_id, "name": name}
        if image_key:
            body["image_key"] = image_key
        else:
            body["image_url"] = image_url
        result = await self._post("/v2/photo_avatar/photo/generate", body)
        avatar_id = result.get("id") or result.get("photo_avatar_id")
        if not avatar_id:
            raise HeyGenError(f"No photo avatar id in response: {result}")
        return avatar_id

    async def train_photo_avatar_group(self, group_id: str) -> None:
        """Initiate training of a photo avatar group. Async — poll separately if needed."""
        body = {"group_id": group_id}
        await self._post("/v2/photo_avatar/train", body)

    async def get_photo_avatar_status(self, photo_avatar_id: str) -> dict:
        """Check the status of a specific photo/look generation."""
        return await self._get(f"/v2/photo_avatar/{photo_avatar_id}")

    async def upload_talking_photo(
        self, file_path: Path, content_type: str = "image/png"
    ) -> dict:
        """Upload a user photo as a HeyGen Talking Photo (instant avatar).

        Returns {"talking_photo_id", "talking_photo_url"}. This is the correct
        path for a user-supplied photo: the id is usable immediately in video
        generation with avatar_type='talking_photo' -- no group, no looks, no
        training, no polling. (The /v2/photo_avatar/* group+looks endpoints
        are for AI-*generated* looks from a prompt and do not accept uploaded
        images, which is why that flow 400s on image_key.)
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Photo not found: {file_path}")
        ext = file_path.suffix.lower()
        ctype = {".png": "image/png", ".jpg": "image/jpeg",
                 ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(ext, content_type)
        url = f"{HEYGEN_UPLOAD_BASE}/v1/talking_photo"
        headers = {"X-Api-Key": self.api_key, "Content-Type": ctype}
        logger.info(f"Uploading talking photo to HeyGen: {file_path.name} ({ctype})")
        async with httpx.AsyncClient(timeout=180.0, verify=SSL_VERIFY) as client:
            with file_path.open("rb") as f:
                r = await client.post(url, headers=headers, content=f.read())
            data = self._parse(r)
        payload = data.get("data") if isinstance(data.get("data"), dict) else data
        tp_id = payload.get("talking_photo_id") or payload.get("id")
        tp_url = payload.get("talking_photo_url") or payload.get("url")
        if not tp_id:
            raise HeyGenError(f"No talking_photo_id in response: {data}")
        logger.info(f"Talking photo created: {tp_id}")
        return {"talking_photo_id": tp_id, "talking_photo_url": tp_url}

    async def create_photo_avatar(
        self,
        file_path: Path,
        avatar_name: str,
        *,
        group_name: Optional[str] = None,
        poll_every_s: float = 3.0,
        timeout_s: float = 180.0,
        do_train: bool = True,
    ) -> dict:
        """Upload a user photo and return an instantly-usable talking photo.

        Uses HeyGen's Talking Photo upload: the returned id works immediately
        with avatar_type='talking_photo'. group_name / poll_every_s /
        timeout_s / do_train are accepted for backward compatibility with the
        existing route but are not needed for talking photos. Returned keys
        are kept stable for the route/UI:
        {photo_avatar_id, group_id, status, asset_url, avatar_name}.
        """
        tp = await self.upload_talking_photo(file_path)
        return {
            "photo_avatar_id": tp["talking_photo_id"],
            "group_id": "",            # talking photos have no avatar group
            "status": "ready",         # usable immediately, no training/poll
            "asset_url": tp.get("talking_photo_url"),
            "avatar_name": avatar_name,
        }

    # ---------- VIDEO TRANSLATION ----------

    async def translate_video(
        self,
        video_url: str,
        target_language: str,
        *,
        title: Optional[str] = None,
        mode: Literal["quality", "speed"] = "quality",
    ) -> str:
        """Translate an existing video to another language using HeyGen's video_translate.

        Returns the translation job id (poll separately to get final URL).
        Supported languages: 'English', 'French', 'Spanish', 'German', etc.
        Mode 'quality' for premium lip-sync, 'speed' for fast standard.
        """
        body = {
            "video_url": video_url,
            "output_language": target_language,
            "mode": mode,
        }
        if title:
            body["title"] = title
        result = await self._post("/v2/video_translate", body)
        translate_id = result.get("video_translate_id") or result.get("id")
        if not translate_id:
            raise HeyGenError(f"No translate_id in response: {result}")
        return translate_id

    async def get_translation_status(self, translate_id: str) -> dict:
        return await self._get(f"/v2/video_translate/{translate_id}")
