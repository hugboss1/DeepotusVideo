"""HeyGen API client — API v3 only (migration du 28/09/2026).

HeyGen retire ses endpoints v1/v2 le 1er novembre 2026 (developers.heygen.com,
« Endpoint Version Comparison »). Tout passe désormais par la v3 :
- génération   POST /v3/videos (type avatar | image | cinematic_avatar)
- statut       GET  /v3/videos/{id}
- avatars      GET  /v3/avatars/looks (+ GET /v3/avatars/looks/{id})
- voix         GET  /v3/voices
- compte       GET  /v3/users/me
- avatar photo POST /v3/avatars (type photo)
Réponses v3 : {"data": ...}, listes paginées par curseur (has_more, next_token).

Auth: X-Api-Key header. Pricing reminder: HeyGen is pay-as-you-go in credits.
The HEYGEN_API_KEY must be set in .env for this service to activate.
"""
import asyncio
import base64
import json
import re
import time
from pathlib import Path
from typing import Optional

import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings, SSL_VERIFY, DATA_ROOT

HEYGEN_BASE = "https://api.heygen.com"

# Les listes v3 sont paginées (50 looks / 100 voix par page). MESURÉ le
# 28/09/2026 sur le compte réel : 9 951 looks en 259 s (~200 pages), 2 944
# voix en 33 s — contre ~60 s pour l'ancien /v2/avatars. D'où trois étages :
#   mémoire (TTL 6 h) -> disque (DATA_ROOT/cache, servi jusqu'à 30 j) -> API ;
# une copie plus vieille que le TTL est servie TOUT DE SUITE et rafraîchie en
# arrière-plan ; deux demandes simultanées (réchauffage du lancement, main.py,
# et l'ouverture du sélecteur) partagent UN seul parcours des pages.
_LIST_TIMEOUT = 120.0
_LIST_MAX_PAGES = 400
_LIST_CACHE_TTL = 21600.0
_DISK_MAX_AGE = 30 * 86400.0
_LIST_CACHE: dict[str, tuple[float, list]] = {}
_INFLIGHT: dict[str, "asyncio.Future"] = {}


def _disk_path(kind: str) -> Path:
    return DATA_ROOT / "cache" / f"heygen_{kind}.json"


def _disk_read(kind: str) -> Optional[tuple[float, list]]:
    try:
        d = json.loads(_disk_path(kind).read_text(encoding="utf-8"))
        return float(d["t"]), list(d["items"])
    except Exception:
        return None


def _disk_write(kind: str, items: list) -> None:
    try:
        p = _disk_path(kind)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps({"t": time.time(), "items": items}, ensure_ascii=False),
                       encoding="utf-8")
        tmp.replace(p)
    except Exception as e:
        logger.warning(f"Cache HeyGen {kind} non écrit sur disque : {e}")

# Moteur quand l'appelant n'en choisit pas : Avatar III, le plus proche du
# rendu et du coût de l'ancienne génération v2 (décision du 28/09/2026). Un
# look qui ne le supporte pas prend le premier moteur qu'il déclare.
DEFAULT_ENGINE = "avatar_iii"
_ENGINES = ("avatar_iii", "avatar_iv", "avatar_v")


def _photo_png_or_jpeg(path: Path) -> tuple[str, bytes]:
    """(media_type, octets) d'une photo pour POST /v3/avatars. Le type est lu
    dans les OCTETS, pas dans l'extension : MESURÉ le 28/09/2026, un WebP
    nommé .jpg est refusé (« Content type not match image/jpeg !=
    image/webp »). La v3 ne documente que PNG et JPEG : tout autre format
    (WebP…) est converti en PNG par Pillow."""
    raw = path.read_bytes()
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png", raw
    if raw[:3] == b"\xff\xd8\xff":
        return "image/jpeg", raw
    import io
    from PIL import Image
    with Image.open(io.BytesIO(raw)) as im:
        buf = io.BytesIO()
        im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB").save(buf, "PNG")
    return "image/png", buf.getvalue()


def invalidate_list_cache() -> None:
    """Drop cached avatar/voice lists, memory AND disk (call after creating a
    new avatar so it shows up immediately instead of waiting for the TTL)."""
    _LIST_CACHE.clear()
    for kind in ("avatars", "voices"):
        try:
            _disk_path(kind).unlink(missing_ok=True)
        except Exception:
            pass


_SPEAK = re.compile(r"</?speak[^>]*>", re.I)
_BREAK = re.compile(r"\s*<break\b[^>]*?/?>\s*", re.I)
_TAG = re.compile(r"<[^>]+>")


def ssml_to_plain(text: str) -> str:
    """Le script v3 est du texte : la v3 ne documente pas le SSML (décision du
    28/09/2026 : convertir plutôt que risquer des balises lues à voix haute).
    <speak> est retiré, chaque <break …/> devient « … » (pause de
    ponctuation), toute autre balise disparaît ; les espaces sont resserrés."""
    t = _SPEAK.sub("", text or "")
    t = _BREAK.sub(" … ", t)
    t = _TAG.sub("", t)
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"(…\s*){2,}", "… ", t)
    return t


class HeyGenError(RuntimeError):
    """Raised when HeyGen API returns a non-success response."""


class HeyGenClient:
    """Thin async wrapper around the HeyGen REST API (v3)."""

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

    async def _get_raw(self, path: str, params: Optional[dict] = None,
                       timeout: float = 60.0) -> dict:
        """GET qui rend l'enveloppe ENTIÈRE (data + has_more + next_token) :
        _parse ne garde que `data` et perdrait le curseur de pagination."""
        async with httpx.AsyncClient(timeout=timeout, verify=SSL_VERIFY) as client:
            r = await client.get(f"{HEYGEN_BASE}{path}",
                                 headers=self.headers, params=params)
            data = self._json(r)
            self._raise_for(r, data)
            return data

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
    def _json(response: httpx.Response):
        try:
            return response.json()
        except ValueError:
            raise HeyGenError(f"Non-JSON response ({response.status_code}): {response.text[:200]}")

    @staticmethod
    def _raise_for(response: httpx.Response, data) -> None:
        if response.status_code >= 400:
            err = data.get("error") if isinstance(data, dict) else None
            if isinstance(err, dict):
                err_msg = err.get("message") or err.get("code") or str(err)
            else:
                err_msg = err or (data.get("message") if isinstance(data, dict) else None) or str(data)
            raise HeyGenError(f"HeyGen {response.status_code}: {err_msg}")

    @staticmethod
    def _parse(response: httpx.Response) -> dict:
        data = HeyGenClient._json(response)
        HeyGenClient._raise_for(response, data)
        # v3 : l'objet utile est sous `data`.
        if isinstance(data, dict) and "data" in data and "code" not in data:
            return data["data"]
        return data

    async def _paginate(self, path: str, params: dict, *, limit: int,
                        max_pages: int = _LIST_MAX_PAGES) -> list[dict]:
        """Suit le curseur v3 (has_more / next_token) jusqu'au bout."""
        out: list[dict] = []
        token = None
        for _ in range(max_pages):
            q = dict(params, limit=limit)
            if token:
                q["token"] = token
            page = await self._get_raw(path, params=q, timeout=_LIST_TIMEOUT)
            items = page.get("data") if isinstance(page, dict) else None
            out.extend(x for x in (items or []) if isinstance(x, dict))
            token = page.get("next_token") if isinstance(page, dict) else None
            if not (isinstance(page, dict) and page.get("has_more") and token):
                break
        else:
            logger.warning(f"HeyGen {path}: arrêt après {max_pages} pages ({len(out)} éléments).")
        return out

    # ---------- AVATARS & VOICES ----------

    @staticmethod
    def _look_to_avatar(lk: dict) -> dict:
        """Look v3 -> forme historique attendue par l'UI (DzAvatarPick, casting,
        Quick). Tous les looks v3 s'utilisent comme `avatar_id` de
        POST /v3/videos, photo avatars compris : avatar_type='avatar' partout."""
        name = lk.get("name") or lk.get("id")
        return {
            "avatar_id": lk.get("id"),
            "avatar_name": name,
            "name": name,
            "gender": lk.get("gender"),
            "preview_image_url": lk.get("preview_image_url"),
            "preview_video_url": lk.get("preview_video_url"),
            "avatar_type": "avatar",
            "look_type": lk.get("avatar_type"),
            "group_id": lk.get("group_id"),
            "default_voice_id": lk.get("default_voice_id"),
            "supported_engines": list(lk.get("supported_api_engines") or []),
            "status": lk.get("status"),
        }

    # -- cache à trois étages (voir _LIST_CACHE_TTL) --

    async def _cached_list(self, kind: str, fetch, use_cache: bool) -> list[dict]:
        if use_cache:
            now = time.time()
            hit = _LIST_CACHE.get(kind)
            if hit is None:
                disk = _disk_read(kind)
                if disk and now - disk[0] < _DISK_MAX_AGE:
                    _LIST_CACHE[kind] = hit = disk
            if hit is not None:
                if now - hit[0] >= _LIST_CACHE_TTL:
                    self._refresh_in_background(kind, fetch)
                logger.debug(f"HeyGen {kind} list served from cache.")
                return hit[1]
        return await self._fetch_once(kind, fetch)

    async def _fetch_store(self, kind: str, fetch) -> list[dict]:
        items = await fetch()
        _LIST_CACHE[kind] = (time.time(), items)
        _disk_write(kind, items)
        return items

    def _start_fetch(self, kind: str, fetch) -> "asyncio.Future":
        task = _INFLIGHT.get(kind)
        if task is None or task.done():
            task = asyncio.ensure_future(self._fetch_store(kind, fetch))
            _INFLIGHT[kind] = task
            task.add_done_callback(
                lambda t, k=kind: _INFLIGHT.pop(k, None) if _INFLIGHT.get(k) is t else None)
        return task

    async def _fetch_once(self, kind: str, fetch) -> list[dict]:
        """Un seul parcours des pages à la fois par liste : les appels
        simultanés attendent le même."""
        return await asyncio.shield(self._start_fetch(kind, fetch))

    def _refresh_in_background(self, kind: str, fetch) -> None:
        def _log(t):
            if not t.cancelled() and t.exception() is not None:
                logger.warning(f"Rafraîchissement HeyGen {kind} échoué : {t.exception()}")
        self._start_fetch(kind, fetch).add_done_callback(_log)

    async def list_avatars(self, *, use_cache: bool = True) -> list[dict]:
        """Tous les looks utilisables : ceux du compte d'abord (ownership
        private : photo avatars, digital twins), puis la bibliothèque publique.
        Liste longue (pagination v3) : cache mémoire + disque, TTL 6 h."""
        return await self._cached_list("avatars", self._fetch_avatars, use_cache)

    async def _fetch_avatars(self) -> list[dict]:
        logger.info("Fetching HeyGen avatar looks (v3)...")
        mine = await self._paginate("/v3/avatars/looks", {"ownership": "private"}, limit=50)
        public = await self._paginate("/v3/avatars/looks", {"ownership": "public"}, limit=50)
        seen, out = set(), []
        for lk in mine + public:
            lid = lk.get("id")
            if not lid or lid in seen:
                continue
            seen.add(lid)
            out.append(self._look_to_avatar(lk))
        logger.info(f"Got {len(mine)} private + {len(public)} public HeyGen looks.")
        return out

    async def list_voices(self, *, use_cache: bool = True) -> list[dict]:
        """Voix du compte (clones) puis voix publiques, à la forme historique
        (voice_id, name, language, gender, preview_audio, support_pause)."""
        return await self._cached_list("voices", self._fetch_voices, use_cache)

    async def _fetch_voices(self) -> list[dict]:
        logger.info("Fetching HeyGen voices (v3)...")
        raw = (await self._paginate("/v3/voices", {"type": "private"}, limit=100)
               + await self._paginate("/v3/voices", {"type": "public"}, limit=100))
        seen, voices = set(), []
        for v in raw:
            vid = v.get("voice_id")
            if not vid or vid in seen:
                continue
            seen.add(vid)
            voices.append({
                "voice_id": vid,
                "name": v.get("name"),
                "language": v.get("language"),
                "gender": v.get("gender"),
                "preview_audio": v.get("preview_audio_url"),
                "support_pause": bool(v.get("support_pause")),
                "support_locale": bool(v.get("support_locale")),
                "type": v.get("type"),
            })
        logger.info(f"Got {len(voices)} voices from HeyGen.")
        return voices

    async def remaining_quota(self) -> dict:
        """Sonde légère (GET /v3/users/me) : valide la clé sans le listage
        lourd. La v3 rend le solde selon la facturation :
          subscription -> crédits premium + add-on  -> remaining_quota
          usage_based  -> remaining_credits          -> remaining_quota
          wallet       -> solde en dollars           -> remaining_usd
        Rend {"remaining_quota", "remaining_usd", "billing_type"}."""
        d = await self._get("/v3/users/me", timeout=20.0)
        d = d if isinstance(d, dict) else {}
        bt = d.get("billing_type")
        credits = usd = None
        sub = (d.get("subscription") or {}).get("credits") if isinstance(d.get("subscription"), dict) else None
        if isinstance(sub, dict):
            parts = [((sub.get(k) or {}).get("remaining")) for k in ("premium_credits", "add_on_credits")]
            parts = [p for p in parts if isinstance(p, (int, float))]
            credits = sum(parts) if parts else None
        ub = d.get("usage_based")
        if credits is None and isinstance(ub, dict) and isinstance(ub.get("remaining_credits"), (int, float)):
            credits = ub["remaining_credits"]
        wal = d.get("wallet")
        if isinstance(wal, dict) and isinstance(wal.get("remaining_balance"), (int, float)):
            usd = wal["remaining_balance"]
        return {"remaining_quota": credits, "remaining_usd": usd, "billing_type": bt}

    async def get_look(self, look_id: str) -> dict:
        """GET /v3/avatars/looks/{id} : moteurs supportés, statut d'entraînement."""
        d = await self._get(f"/v3/avatars/looks/{look_id}", timeout=30.0)
        return d if isinstance(d, dict) else {}

    async def resolve_engine(self, avatar_id: str, engine: Optional[str]) -> str:
        """Moteur explicite : gardé tel quel. Sinon DEFAULT_ENGINE (Avatar III)
        si le look le supporte, à défaut le premier moteur qu'il déclare. Un
        look illisible garde DEFAULT_ENGINE : HeyGen dira s'il le refuse."""
        if engine:
            return engine
        try:
            sup = [e for e in (await self.get_look(avatar_id)).get("supported_api_engines") or []
                   if e in _ENGINES]
        except Exception as e:
            logger.warning(f"HeyGen look {avatar_id} illisible ({e}) — moteur {DEFAULT_ENGINE}.")
            return DEFAULT_ENGINE
        if not sup or DEFAULT_ENGINE in sup:
            return DEFAULT_ENGINE
        return sup[0]

    # ---------- VIDEO GENERATION (API v3) ----------

    @staticmethod
    def build_v3_avatar_body(
        text: str,
        avatar_id: str,
        voice_id: str,
        *,
        engine: str,
        aspect_ratio: str = "9:16",
        speed: float = 1.0,
        background_color: str = "#02060d",
        motion_prompt: Optional[str] = None,
        expressiveness: Optional[str] = None,
        title: Optional[str] = None,
    ) -> dict:
        """Build the /v3/videos request body (type=avatar). Pure + testable.

        v3 clamps voice speed to 0.5–1.5; the script is plain text (SSML
        converted by ssml_to_plain); motion_prompt / expressiveness only
        apply to photo avatars on IV/V, so they are sent only when provided.
        """
        body: dict = {
            "type": "avatar",
            "avatar_id": avatar_id,
            "script": ssml_to_plain(text)[:4900],
            "voice_id": voice_id,
            "engine": {"type": engine},
            "aspect_ratio": aspect_ratio,
            "resolution": "1080p",
            "background": {"type": "color", "value": background_color},
            "voice_settings": {"speed": max(0.5, min(1.5, speed))},
        }
        if motion_prompt and engine in ("avatar_iv", "avatar_v"):
            body["motion_prompt"] = motion_prompt
        if expressiveness and engine == "avatar_iv":
            body["expressiveness"] = expressiveness
        if title:
            body["title"] = title
        return body

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=4, max=30), reraise=True)
    async def generate_video_v3(
        self,
        text: str,
        avatar_id: str,
        voice_id: str,
        *,
        engine: Optional[str] = None,
        aspect_ratio: str = "9:16",
        speed: float = 1.0,
        background_color: str = "#02060d",
        motion_prompt: Optional[str] = None,
        expressiveness: Optional[str] = None,
        title: Optional[str] = None,
    ) -> str:
        """Submit a v3 avatar video. `engine` None = résolu par look
        (resolve_engine). Returns video_id."""
        engine = await self.resolve_engine(avatar_id, engine)
        body = self.build_v3_avatar_body(
            text, avatar_id, voice_id, engine=engine,
            aspect_ratio=aspect_ratio, speed=speed,
            background_color=background_color,
            motion_prompt=motion_prompt, expressiveness=expressiveness,
            title=title,
        )
        logger.info(f"Submitting HeyGen v3 video: engine={engine}, "
                    f"avatar={avatar_id}, voice={voice_id}, aspect={aspect_ratio}")
        result = await self._post("/v3/videos", body)
        payload = result.get("data") if isinstance(result.get("data"), dict) else result
        video_id = payload.get("video_id") or payload.get("id")
        if not video_id:
            raise HeyGenError(f"No video_id in HeyGen v3 response: {result}")
        logger.info(f"HeyGen v3 video submitted: {video_id}")
        return video_id

    async def poll_video_status_v3(
        self,
        video_id: str,
        *,
        poll_every_s: float = 4.0,
        timeout_s: float = 900.0,
    ) -> dict:
        """Poll GET /v3/videos/{id} until completed/failed. Returns the final
        payload (contains a presigned video_url — download promptly)."""
        elapsed = 0.0
        last_status = None
        while elapsed < timeout_s:
            result = await self._get(f"/v3/videos/{video_id}")
            payload = (result.get("data")
                       if isinstance(result.get("data"), dict) else result)
            status = payload.get("status")
            last_status = status
            if status == "completed":
                logger.info(f"HeyGen v3 video {video_id} complete.")
                return payload
            if status == "failed":
                # v3 : failure_code / failure_message (doc « Get Video »).
                err = payload.get("error")
                msg = (payload.get("failure_message")
                       or (err.get("message") if isinstance(err, dict) else err)
                       or payload.get("failure_code"))
                raise HeyGenError(f"HeyGen v3 video {video_id} failed: "
                                  f"{msg or 'unknown error'}")
            logger.debug(f"HeyGen v3 status {video_id}: {status} ({elapsed:.0f}s)")
            await asyncio.sleep(poll_every_s)
            elapsed += poll_every_s
        raise HeyGenError(
            f"HeyGen v3 video {video_id} timed out after {timeout_s}s "
            f"(last status: {last_status})")

    # ---------- v3: ANIMATE AN IMAGE / CINEMATIC (feature D) ----------

    @staticmethod
    def _b64_image(path: Path) -> dict:
        """v3 inline-image payload (base64) from a local Library file."""
        import base64
        mt = {".png": "image/png", ".jpg": "image/jpeg",
              ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(
                  path.suffix.lower(), "image/png")
        return {"type": "base64", "media_type": mt,
                "data": base64.b64encode(path.read_bytes()).decode()}

    @staticmethod
    def build_v3_image_body(
        image_path: Path,
        text: str,
        voice_id: str,
        *,
        engine: str = "avatar_iv",
        aspect_ratio: str = "9:16",
        speed: float = 1.0,
        motion_prompt: Optional[str] = None,
        expressiveness: Optional[str] = None,
        title: Optional[str] = None,
    ) -> dict:
        """/v3/videos body, type=image: animate ANY still (photo→talking video).
        No background field — the image itself is the frame."""
        body: dict = {
            "type": "image",
            "image": HeyGenClient._b64_image(image_path),
            "script": text[:4900],
            "voice_id": voice_id,
            "engine": {"type": engine},
            "aspect_ratio": aspect_ratio,
            "resolution": "1080p",
            "voice_settings": {"speed": max(0.5, min(1.5, speed))},
        }
        if motion_prompt:
            body["motion_prompt"] = motion_prompt
        if expressiveness and engine == "avatar_iv":
            body["expressiveness"] = expressiveness
        if title:
            body["title"] = title
        return body

    async def generate_image_video_v3(self, image_path: Path, text: str,
                                      voice_id: str, **kw) -> str:
        """Animate a local image via v3. Returns video_id (poll with
        poll_video_status_v3)."""
        body = self.build_v3_image_body(image_path, text, voice_id, **kw)
        logger.info(f"Submitting HeyGen v3 IMAGE video: {image_path.name}, "
                    f"engine={body['engine']['type']}")
        result = await self._post("/v3/videos", body)
        payload = result.get("data") if isinstance(result.get("data"), dict) else result
        video_id = payload.get("video_id") or payload.get("id")
        if not video_id:
            raise HeyGenError(f"No video_id in HeyGen v3 image response: {result}")
        return video_id

    @staticmethod
    def build_v3_cinematic_body(
        prompt: str,
        look_ids: list[str],
        *,
        reference_paths: Optional[list[Path]] = None,
        duration_s: Optional[int] = None,
        auto_duration: bool = False,
        aspect_ratio: str = "9:16",
        resolution: str = "720p",
        enhance_prompt: bool = True,
        title: Optional[str] = None,
    ) -> dict:
        """/v3/videos body, type=cinematic_avatar: prompt-driven motion with
        1–3 avatar looks and optional reference images. No script/voice —
        motion comes from the prompt."""
        body: dict = {
            "type": "cinematic_avatar",
            "prompt": prompt[:10000],
            "avatar_id": list(look_ids)[:3],
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
        }
        if auto_duration or not duration_s:
            body["auto_duration"] = True
        else:
            body["duration"] = max(4, min(15, int(duration_s)))
        refs = [HeyGenClient._b64_image(p) for p in (reference_paths or [])[:9]]
        if refs:
            body["references"] = refs
        if enhance_prompt:
            body["enhance_prompt"] = True
        if title:
            body["title"] = title
        return body

    async def generate_cinematic_v3(self, prompt: str, look_ids: list[str],
                                    **kw) -> str:
        """Cinematic avatar video via v3. Returns video_id."""
        body = self.build_v3_cinematic_body(prompt, look_ids, **kw)
        logger.info(f"Submitting HeyGen v3 CINEMATIC video: "
                    f"{len(body['avatar_id'])} look(s), "
                    f"{'auto' if body.get('auto_duration') else body.get('duration')}s")
        result = await self._post("/v3/videos", body)
        payload = result.get("data") if isinstance(result.get("data"), dict) else result
        video_id = payload.get("video_id") or payload.get("id")
        if not video_id:
            raise HeyGenError(f"No video_id in HeyGen v3 cinematic response: {result}")
        return video_id

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

    # ---------- PHOTO AVATAR (v3) ----------

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
        """Crée un photo avatar v3 (POST /v3/avatars, type photo, image en
        base64) puis attend que son look soit entraîné (GET
        /v3/avatars/looks/{id} -> completed). L'id du look s'utilise comme
        avatar_id de POST /v3/videos. `group_name` / `do_train` restent
        acceptés pour la route historique (la v3 entraîne d'elle-même).
        Clés rendues stables pour la route et l'UI :
        {photo_avatar_id, group_id, status, asset_url, avatar_name}.
        Un look en `pending_consent` est rendu tel quel (le consentement se
        donne dans HeyGen) ; `failed` lève HeyGenError."""
        if not file_path.exists():
            raise FileNotFoundError(f"Photo not found: {file_path}")
        mt, data = _photo_png_or_jpeg(file_path)
        body = {
            "type": "photo",
            "name": avatar_name,
            "file": {"type": "base64", "media_type": mt,
                     "data": base64.b64encode(data).decode()},
        }
        logger.info(f"Creating HeyGen v3 photo avatar: {file_path.name} ({mt})")
        res = await self._post("/v3/avatars", body)
        item = (res.get("avatar_item") if isinstance(res, dict) else None) or {}
        group = (res.get("avatar_group") if isinstance(res, dict) else None) or {}
        look_id = item.get("id")
        if not look_id:
            raise HeyGenError(f"No avatar look id in HeyGen v3 response: {res}")
        status = item.get("status") or "processing"
        look = item
        elapsed = 0.0
        while status == "processing" and elapsed < timeout_s:
            await asyncio.sleep(poll_every_s)
            elapsed += poll_every_s
            look = await self.get_look(look_id)
            status = look.get("status") or status
        if status == "failed":
            err = look.get("error") or {}
            raise HeyGenError("HeyGen photo avatar failed: "
                              f"{err.get('message') if isinstance(err, dict) else err}")
        return {
            "photo_avatar_id": look_id,
            "group_id": item.get("group_id") or group.get("id") or "",
            "status": status,
            "asset_url": look.get("preview_image_url"),
            "avatar_name": avatar_name,
        }
