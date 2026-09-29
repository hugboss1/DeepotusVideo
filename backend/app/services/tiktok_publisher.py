"""TikTok Direct Post — Content Posting API v2, FILE_UPLOAD par morceaux (plan scheduler T5 — tâche #27, 29/09/2026).

Doc relue le 29/09/2026 (WebFetch developers.tiktok.com : content-posting-api-reference-direct-post, -media-transfer-guide,
-get-started, -reference-query-creator-info, -reference-get-video-status, oauth-user-access-token-management,
login-kit-desktop). Ce qu'elle impose, et que le plan du 03/09 n'avait pas :
- `creator_info/query` AVANT l'init : la visibilité « must match one of the privacy_level_options returned » ; les
  commentaires / duos / collages que le créateur a coupés restent coupés ;
- morceaux : « at least 5 MB but no greater than 64 MB, except for the final chunk, which can be greater than
  chunk_size (up to 128 MB) », 1000 au plus, et `total_chunk_count` = video_size / chunk_size ARRONDI À L'INFÉRIEUR
  (le reste va au dernier morceau — le plan arrondissait au supérieur) ; PUT séquentiels, 206 puis 201 ;
- « All content posted by unaudited clients will be restricted to private viewing mode » : SELF_ONLY forcé et DIT
  tant que TIKTOK_AUDITED est faux ; `unaudited_client_can_only_post_to_private_accounts` = le COMPTE doit être privé ;
- le renouvellement « may be different than the one passed in the payload. You must use the newly-returned token » :
  le refresh token rendu est appliqué ET enregistré (coffre ouvert, sinon .env) — sinon TikTok se déconnecte ;
- jeton d'accès valable 24 h : mis en cache (l'init est limitée à 6 requêtes/min par jeton, le statut à 30/min) ;
- appli de bureau : redirection loopback « Only localhost or loopback IP 127.0.0.1 », PKCE obligatoire avec un défi
  SHA256 en HEXADÉCIMAL (pas en base64url comme Google) — la voie « coller le code » du plan est inutile, la route de
  rappel vient à T6 comme pour YouTube.
Quota local : ~15 posts/jour (quota.py)."""
import asyncio
import hashlib
import secrets
import time
from pathlib import Path
from urllib.parse import urlencode

import httpx
from loguru import logger

from app.config import settings, SSL_VERIFY
from app.services import publishers
from app.services.publishers import PublishResult

AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
CREATOR_URL = "https://open.tiktokapis.com/v2/post/publish/creator_info/query/"
INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"
QUERY_URL = "https://open.tiktokapis.com/v2/video/query/"
SCOPES = "user.info.basic,video.publish,video.list"
CHUNK = 32 * 1024 * 1024           # 5 Mo ≤ morceau ≤ 64 Mo ; le dernier (≤ 2 × CHUNK) reste sous 128 Mo
SINGLE_MAX = 64 * 1024 * 1024
POLL_EVERY_S_DEFAUT = 5.0          # statut : 30 requêtes/min par jeton — 12/min ici
POLL_EVERY_S, POLL_MAX = POLL_EVERY_S_DEFAUT, 60   # 5 minutes
_VERIFS: dict[str, str] = {}
_VERIFS_MAX = 16
_jeton: dict = {"valeur": "", "expire": 0.0}


def redirect_uri() -> str:
    return f"http://127.0.0.1:{settings.PORT}/api/oauth/tiktok/callback/"


def _client(timeout: float = 60.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(verify=SSL_VERIFY, timeout=timeout)


def _scrub(text: str) -> str:
    for v in (settings.TIKTOK_CLIENT_SECRET, settings.TIKTOK_REFRESH_TOKEN, _jeton["valeur"]):
        v = (v or "").strip()
        if v:
            text = text.replace(v, "***")
    return text


def _chunks(size: int) -> tuple[int, int]:
    """(chunk_size, total_chunk_count) selon la doc : un morceau jusqu'à SINGLE_MAX, sinon arrondi inférieur."""
    if size <= SINGLE_MAX:
        return size, 1
    return CHUNK, size // CHUNK


def _oublier_jeton() -> None:
    _jeton.update(valeur="", expire=0.0)


def auth_url(state: str) -> str:
    verif = secrets.token_urlsafe(48)
    while len(_VERIFS) >= _VERIFS_MAX:
        _VERIFS.pop(next(iter(_VERIFS)))
    _VERIFS[state] = verif
    return AUTH_URL + "?" + urlencode({
        "client_key": settings.TIKTOK_CLIENT_KEY, "scope": SCOPES, "redirect_uri": redirect_uri(),
        "state": state, "response_type": "code",
        "code_challenge": hashlib.sha256(verif.encode()).hexdigest(), "code_challenge_method": "S256"})


async def _token(grant: dict) -> dict:
    async with _client() as c:
        r = await c.post(TOKEN_URL, data={"client_key": settings.TIKTOK_CLIENT_KEY,
                                          "client_secret": settings.TIKTOK_CLIENT_SECRET, **grant},
                         headers={"Content-Type": "application/x-www-form-urlencoded"})
    j = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    if r.status_code != 200 or not j.get("access_token"):
        raise RuntimeError(f"tiktok token {r.status_code}: {_scrub(r.text)[:160]}")
    return j


async def exchange_code(code: str, state: str) -> str:
    """code → refresh_token ('' si l'état est inconnu — aucun appel alors — ou si TikTok refuse)."""
    verif = _VERIFS.pop(state, None)
    if not verif:
        logger.warning("tiktok oauth : état inconnu ou déjà consommé")
        return ""
    try:
        j = await _token({"grant_type": "authorization_code", "code": code,
                          "redirect_uri": redirect_uri(), "code_verifier": verif})
    except RuntimeError as e:
        logger.warning(str(e))
        return ""
    return str(j.get("refresh_token") or "")


async def access_token() -> str:
    if _jeton["valeur"] and time.time() < _jeton["expire"] - 60:
        return _jeton["valeur"]
    j = await _token({"grant_type": "refresh_token", "refresh_token": settings.TIKTOK_REFRESH_TOKEN})
    _jeton.update(valeur=j["access_token"], expire=time.time() + float(j.get("expires_in") or 0))
    neuf = str(j.get("refresh_token") or "")
    if neuf and neuf != settings.TIKTOK_REFRESH_TOKEN:
        from app.services import coffre
        ou = coffre.enregistrer_cle("TIKTOK_REFRESH_TOKEN", neuf)
        logger.info(f"tiktok : refresh token renouvelé, gardé ({ou})")
    return _jeton["valeur"]


def _erreur(r: httpx.Response) -> str:
    try:
        e = r.json().get("error") or {}
    except ValueError:
        return _scrub(r.text)[:200]
    return str(e.get("code") or "") + (f" ({e.get('message')})" if e.get("message") else "")


async def publish(caption: str, video_path, image_path, meta: dict) -> PublishResult:
    if not video_path or not Path(video_path).is_file():
        return PublishResult(False, "tiktok: une vidéo est requise (aucun rendu attaché)")
    size = Path(video_path).stat().st_size
    chunk, n = _chunks(size)
    voulu = meta.get("privacy", "PUBLIC_TO_EVERYONE") if settings.TIKTOK_AUDITED else "SELF_ONLY"
    try:
        tok = await access_token()
        hdr = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8"}
        async with _client(timeout=900.0) as c:
            ci = await c.post(CREATOR_URL, headers=hdr)
            cd = (ci.json().get("data") or {}) if ci.status_code == 200 else {}
            if ci.status_code != 200:
                return PublishResult(False, f"tiktok creator_info {ci.status_code}: {_erreur(ci)}")
            opts = list(cd.get("privacy_level_options") or [])
            if voulu not in opts:
                return PublishResult(False, f"tiktok : visibilité {voulu} refusée pour ce compte "
                                            f"(options de TikTok : {', '.join(opts) or 'aucune'})")
            body = {"post_info": {"title": caption[:2200], "privacy_level": voulu,
                                  "disable_duet": bool(cd.get("duet_disabled")),
                                  "disable_comment": bool(cd.get("comment_disabled")),
                                  "disable_stitch": bool(cd.get("stitch_disabled")),
                                  "video_cover_timestamp_ms": 1000},
                    "source_info": {"source": "FILE_UPLOAD", "video_size": size,
                                    "chunk_size": chunk, "total_chunk_count": n}}
            r = await c.post(INIT_URL, json=body, headers=hdr)
            d = (r.json().get("data") or {}) if r.status_code == 200 else {}
            if r.status_code != 200 or not d.get("upload_url"):
                code = _erreur(r)
                aide = (" — tant que l'app n'est pas auditée, le COMPTE TikTok doit être en privé"
                        if "unaudited_client_can_only_post_to_private_accounts" in code else "")
                return PublishResult(False, f"tiktok init {r.status_code}: {code}{aide}")
            pid, url = str(d.get("publish_id") or ""), d["upload_url"]
            with open(video_path, "rb") as f:
                for i in range(n):
                    part = f.read(chunk if i < n - 1 else size)   # le dernier morceau prend le reste
                    start = i * chunk
                    r2 = await c.put(url, content=part, headers={
                        "Content-Type": "video/mp4", "Content-Length": str(len(part)),
                        "Content-Range": f"bytes {start}-{start + len(part) - 1}/{size}"})
                    if r2.status_code not in (200, 201, 206):
                        return PublishResult(False, f"tiktok upload {r2.status_code} (morceau {i + 1}/{n})")
            post_id = ""
            for _ in range(POLL_MAX):
                s = await c.post(STATUS_URL, json={"publish_id": pid}, headers=hdr)
                sd = s.json().get("data") or {}
                if sd.get("status") == "PUBLISH_COMPLETE":
                    ids = sd.get("publicaly_available_post_id") or []
                    post_id = str(ids[0]) if ids else ""
                    break
                if sd.get("status") == "FAILED":
                    return PublishResult(False, f"tiktok FAILED: {sd.get('fail_reason', '')}")
                await asyncio.sleep(POLL_EVERY_S)
            else:
                return PublishResult(False, f"tiktok: statut jamais PUBLISH_COMPLETE après {POLL_MAX} sondages")
        ref = post_id or pid
        note = (" — publié en PRIVÉ (client TikTok non audité : SELF_ONLY tant que l'audit n'est pas passé)"
                if not settings.TIKTOK_AUDITED else "")
        return PublishResult(True, f"tiktok: {ref}{note}", ref or None)
    except Exception as e:
        return PublishResult(False, f"tiktok error: {_scrub(str(e))}")


async def fetch_stats(video_ids: list[str]) -> dict[str, dict]:
    """video/query (portée video.list) — seuls les ids publics NUMÉRIQUES existent pour l'API."""
    ids = [v for v in video_ids if str(v).isdigit()][:20]
    if not ids:
        return {}
    tok = await access_token()
    async with _client() as c:
        r = await c.post(QUERY_URL, params={"fields": "id,view_count,like_count,comment_count,share_count"},
                         json={"filters": {"video_ids": ids}},
                         headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    if r.status_code != 200:
        return {}
    out = {}
    for v in (r.json().get("data") or {}).get("videos", []):
        out[str(v.get("id"))] = {"views": int(v.get("view_count") or 0), "likes": int(v.get("like_count") or 0),
                                 "comments": int(v.get("comment_count") or 0),
                                 "shares": int(v.get("share_count") or 0), "saves": 0}
    return out


publishers.register("tiktok", lambda: settings.has_tiktok, publish)
