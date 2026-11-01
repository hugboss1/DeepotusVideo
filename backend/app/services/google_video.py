"""Google GenAI native video client — W-a (v1.19), Interactions t406.

Two Generative Language API paths, both on the AI Studio key (the same
GEMINI_API_KEY the summarizer/planner already use, read from the vault into
settings — never logged, never put in a URL). Contract mirrors
FalSeedanceClient (generate_video / extract_video_url / extract_seed /
download_video) so the pipeline only branches on where the image goes:
fal uploads it to fal storage, Google takes inline base64 bytes — the
user's image never transits a third party for Google renders.

Veo 3.1 previews, proven live on 22/07/2026 with Olivier's key:
  POST /v1beta/models/{model}:predictLongRunning  -> {"name": op}
  GET  /v1beta/{op}                                -> {done, response|error}
  GET  {response...video.uri}  (x-goog-api-key)    -> mp4 bytes
SHUT DOWN by Google on 22/10/2026 (veo-3.1-generate-preview, -fast-, -lite-:
the video doc says so, and /api/generate got « no longer available » 404s on
01/11/2026). The registry keeps them flagged `retire` so old recipes get a
clean refusal before any spend.

t406 (01/11/2026) — Gemini Omni Flash (`gemini-omni-1.1-flash`) through the
Interactions API (docs/omni, api/interactions, docs/background-execution,
read 01/11/2026):
  POST /v1beta/interactions {model, input:[image, image?, text],
       response_format:{type:"video", aspect_ratio, resolution, duration,
       delivery:"uri"}, generation_config.video_config.task, background:true}
                                                   -> {id, status}
  GET  /v1beta/interactions/{id}                   -> {status, steps[...]}
  The video is steps[type=model_output].content[type=video]: `data` (base64)
  or `uri` (files/{id}:download, ready once GET files/{id} says ACTIVE). The
  doc warns that GET interactions/{id} answers inline base64 even when the
  job asked for a uri: both are handled.
No seed, no negative prompt (the doc: put negatives in the prompt), no fps
parameter. Billed on output tokens: 5,792 tokens per second of 720p video at
$17.50 / 1M (≈ $0.10/s, pricing page read 01/11/2026).
(This module is also the shared REST base for the W-c/W-e Google chantiers.)
"""
import asyncio
import base64
import mimetypes
import re
from pathlib import Path
from typing import Optional

import httpx
from loguru import logger

from app.config import settings, SSL_VERIFY

GOOGLE_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
INTERACTIONS_URL = f"{GOOGLE_API_BASE}/interactions"

# Veo renders usually land in well under 2 minutes (the 22/07 probe took 8s)
# but previews can queue; poll gently and give up cleanly after 10 min.
_POLL_INTERVAL_S = 5.0
_POLL_TIMEOUT_S = 600.0

# t406 : vidéos rendues INLINE par l'Interactions API, gardées en mémoire le
# temps que download_video les écrive. L'URL rendue au pipeline reste courte
# (« google-inline:<id> ») : jamais des mégaoctets de base64 dans le job.
_INLINE: dict = {}
_PREFIXE_INLINE = "google-inline:"
_RESOLUTIONS_OMNI = ("360p", "720p", "1080p", "4k")


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


def est_interactions(model: str) -> bool:
    """t406 : le modèle passe par l'Interactions API (Gemini Omni), pas par
    predictLongRunning (Veo)."""
    return str(model or "").startswith("gemini-omni")


def _part_interactions(image_path: Path) -> dict:
    mime = mimetypes.guess_type(image_path.name)[0] or "image/png"
    return {"type": "image", "data": base64.b64encode(image_path.read_bytes()).decode("ascii"),
            "mime_type": mime}


def build_interactions_body(*, prompt: str, image_path: Path, end_image_path: Optional[Path],
                            duration: int, aspect_ratio: str, resolution: str, model: str) -> dict:
    """t406 — le corps de POST /v1beta/interactions pour un image → vidéo.

    Image de départ, puis l'image de FIN facultative, puis le texte : la tâche
    `image_to_video` dit « la 1re image est la première trame, la 2de
    (facultative) la dernière » (référence de l'API). 9:16 / 16:9 seulement
    (autre chose -> vertical, l'orientation de l'app, comme Veo) ; une
    résolution hors des valeurs de l'API retombe sur 720p (le défaut de
    Google). `duration` est une CHAÎNE dans l'API, sans format documenté :
    on envoie la forme Duration de Google (« 4s »). `delivery: uri` pour les
    rendus de plus de 4 Mo ; `background: true` car un rendu dépasse le
    délai d'une requête HTTP ordinaire (60 s, docs/background-execution)."""
    parts = [_part_interactions(image_path)]
    if end_image_path is not None:
        parts.append(_part_interactions(end_image_path))
    parts.append({"type": "text", "text": prompt})
    return {
        "model": model,
        "input": parts,
        "response_format": {
            "type": "video",
            "aspect_ratio": aspect_ratio if aspect_ratio in ("9:16", "16:9") else "9:16",
            "resolution": resolution if resolution in _RESOLUTIONS_OMNI else "720p",
            "duration": f"{int(duration)}s",
            "delivery": "uri",
        },
        "generation_config": {"video_config": {"task": "image_to_video"}},
        "background": True,
    }


def _video_de(interaction: dict) -> dict:
    """Le contenu vidéo d'une interaction terminée ({data|uri, mime_type}),
    ou {} : le DERNIER steps[type=model_output] qui porte une vidéo, sinon
    `output_video` (forme vue dans un exemple REST de la doc)."""
    for step in reversed(interaction.get("steps") or []):
        if not isinstance(step, dict) or step.get("type") != "model_output":
            continue
        for c in step.get("content") or []:
            if isinstance(c, dict) and c.get("type") == "video" and (c.get("data") or c.get("uri")):
                return c
    ov = interaction.get("output_video")
    return ov if isinstance(ov, dict) and (ov.get("data") or ov.get("uri")) else {}


def _erreur_interaction(interaction: dict) -> str:
    err = interaction.get("error")
    if isinstance(err, dict):
        return str(err.get("message") or err)[:300]
    return str(err or "")[:300]


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
        end_image_path: Optional[Path] = None,
        duration: int = 8,
        aspect_ratio: str = "9:16",
        resolution: str = "720p",
        model: str = "veo-3.1-fast-generate-preview",
    ) -> dict:
        """Submit an image-to-video job to Google and wait for it — Gemini
        Omni through the Interactions API (t406), else Veo through
        predictLongRunning.

        Returns {"video": {"url": ...}} like the fal client. All failures
        raise RuntimeError prefixed "google:" so job.error is self-explaining
        (quota / billing / safety block included).
        """
        GoogleVeoClient._require_key()
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        if est_interactions(model):
            return await GoogleVeoClient._generate_interactions(
                image_path=image_path, end_image_path=end_image_path, prompt=prompt,
                negative_prompt=negative_prompt, duration=duration,
                aspect_ratio=aspect_ratio, resolution=resolution, model=model)
        if end_image_path is not None:
            raise RuntimeError(f"google: {model} has no last-frame input")

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
    async def _generate_interactions(*, image_path: Path, end_image_path: Optional[Path], prompt: str,
                                     negative_prompt: str, duration: int, aspect_ratio: str,
                                     resolution: str, model: str) -> dict:
        """t406 — image → vidéo par l'Interactions API (Gemini Omni Flash) :
        création en arrière-plan, sondage de l'interaction jusqu'à un statut
        terminal, puis la vidéo inline (gardée pour download_video) ou son
        fichier, attendu jusqu'à ACTIVE. Toute erreur lève RuntimeError
        préfixée « google: » (statut et message de Google)."""
        if end_image_path is not None and not end_image_path.exists():
            raise FileNotFoundError(f"End image not found: {end_image_path}")
        if negative_prompt:
            logger.debug("Gemini Omni: negative_prompt dropped (unsupported)")
        body = build_interactions_body(prompt=prompt, image_path=image_path, end_image_path=end_image_path,
                                       duration=duration, aspect_ratio=aspect_ratio,
                                       resolution=resolution, model=model)
        rf = body["response_format"]
        logger.info(
            f"Submitting Google Interactions video job to {model} -- duration={rf['duration']}, "
            f"ratio={rf['aspect_ratio']}, res={rf['resolution']}, "
            f"first-last={end_image_path is not None}")
        async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=90.0) as client:
            try:
                r = await client.post(INTERACTIONS_URL, json=body, headers=google_headers())
            except httpx.HTTPError as e:
                raise RuntimeError(f"google: {e}") from e
            if r.status_code != 200:
                raise RuntimeError(f"google: HTTP {r.status_code} — {_short_error(r)}")
            inter = r.json() or {}
            iid = inter.get("id")
            waited = 0.0
            while (inter.get("status") or "in_progress") == "in_progress":
                if not iid:
                    raise RuntimeError(f"google: no interaction id in {r.text[:200]}")
                if waited >= _POLL_TIMEOUT_S:
                    raise RuntimeError(
                        f"google: video interaction timed out after {int(_POLL_TIMEOUT_S)}s ({iid})")
                await asyncio.sleep(_POLL_INTERVAL_S)
                waited += _POLL_INTERVAL_S
                try:
                    pr = await client.get(f"{INTERACTIONS_URL}/{iid}", headers=google_headers())
                except httpx.HTTPError as e:
                    raise RuntimeError(f"google: poll failed — {e}") from e
                if pr.status_code != 200:
                    raise RuntimeError(f"google: poll HTTP {pr.status_code} — {_short_error(pr)}")
                inter = pr.json() or {}
            statut = inter.get("status")
            if statut != "completed":
                raise RuntimeError(f"google: interaction {statut} — {_erreur_interaction(inter)} ({iid})")
            video = _video_de(inter)
            if not video:
                raise RuntimeError(f"google: no video in interaction {iid} — {str(inter)[:300]}")
            usage = inter.get("usage")
            if video.get("uri"):
                await GoogleVeoClient._attendre_fichier(client, video["uri"])
                url = video["uri"]
            else:
                url = f"{_PREFIXE_INLINE}{iid}"
                _INLINE[url] = base64.b64decode(video["data"])
        logger.info(f"Google Interactions job {iid} complete after ~{int(waited)}s "
                    f"({'uri' if video.get('uri') else 'inline'}) usage={str(usage)[:200]}")
        return {"video": {"url": url}, "usage": usage}

    @staticmethod
    async def _attendre_fichier(client: httpx.AsyncClient, uri: str) -> None:
        """Le fichier d'une livraison par URI ne se télécharge qu'une fois
        GET files/{id} à state ACTIVE (doc omni) ; FAILED lève."""
        m = re.search(r"/files/([^/:?]+)", uri)
        if not m:
            return
        waited = 0.0
        while True:
            try:
                fr = await client.get(f"{GOOGLE_API_BASE}/files/{m.group(1)}", headers=google_headers())
            except httpx.HTTPError as e:
                raise RuntimeError(f"google: file poll failed — {e}") from e
            if fr.status_code != 200:
                raise RuntimeError(f"google: file poll HTTP {fr.status_code} — {_short_error(fr)}")
            etat = (fr.json() or {}).get("state")
            if etat == "ACTIVE":
                return
            if etat == "FAILED":
                raise RuntimeError(f"google: video file {m.group(1)} FAILED")
            if waited >= _POLL_TIMEOUT_S:
                raise RuntimeError(f"google: video file not ready after {int(_POLL_TIMEOUT_S)}s")
            await asyncio.sleep(_POLL_INTERVAL_S)
            waited += _POLL_INTERVAL_S

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
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        if video_url.startswith(_PREFIXE_INLINE):
            # t406 : vidéo rendue inline par l'Interactions API, écrite une fois
            data = _INLINE.pop(video_url, None)
            if data is None:
                raise RuntimeError(f"google: inline video {video_url} unknown or already written")
            dest_path.write_bytes(data)
            logger.info(f"Inline Google video written: {dest_path} ({len(data) // 1024} KB)")
            return dest_path
        GoogleVeoClient._require_key()
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
