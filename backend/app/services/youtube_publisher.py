"""YouTube Shorts — Data API v3 en HTTP direct (httpx), sans client Google (plan scheduler T3 — tâche #25, 29/09/2026).

OAuth 2.0 « application de bureau » : redirection loopback sur le backend
(http://127.0.0.1:<PORT>/api/oauth/youtube/callback — la route vient à T6), avec PKCE S256 ; le refresh token est
écrit dans .env par la route. Envoi résumable : POST init (taille et type annoncés) → URI de session dans `Location`
→ PUT du fichier, 201 Created. Quota : 100 envois/jour (quota.py).

Doc relue le 29/09/2026 (WebFetch) :
- developers.google.com/youtube/v3/guides/using_resumable_upload_protocol — init 200 + `Location`, PUT → 201 ;
- developers.google.com/identity/protocols/oauth2/native-app — loopback `http://127.0.0.1:port` recommandé pour
  un client Desktop, PKCE recommandé ;
- developers.google.com/youtube/v3/docs/videos/insert — 1 unité (seau des envois, 100/jour) et : « All videos
  uploaded via the videos.insert endpoint from unverified API projects created after 28 July 2020 will be restricted
  to private viewing mode ». D'où la lecture de la visibilité RÉELLEMENT appliquée : un Short demandé public et rendu
  privé est un succès, mais l'adaptateur le DIT.

Le fichier part par un générateur ASYNCHRONE de morceaux : le vrai httpx.AsyncClient refuse un fichier synchrone en
`content=` (le plan du 03/09 le lui passait)."""
import base64
import hashlib
import secrets
from pathlib import Path
from urllib.parse import urlencode

import httpx
from loguru import logger

from app.config import settings, SSL_VERIFY
from app.services import metrics_service, publishers
from app.services.publishers import PublishResult

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = ("https://www.googleapis.com/upload/youtube/v3/videos"
              "?uploadType=resumable&part=snippet,status")
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
SCOPES = ("https://www.googleapis.com/auth/youtube.upload "
          "https://www.googleapis.com/auth/youtube.readonly")
_MORCEAU = 1 << 20
# état OAuth -> vérificateur PKCE, consommé une fois ; borné (une autorisation abandonnée ne s'accumule pas)
_VERIFS: dict[str, str] = {}
_VERIFS_MAX = 16


def redirect_uri() -> str:
    return f"http://127.0.0.1:{settings.PORT}/api/oauth/youtube/callback"


def _client(timeout: float = 60.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(verify=SSL_VERIFY, timeout=timeout)


def auth_url(state: str) -> str:
    verif = secrets.token_urlsafe(48)
    while len(_VERIFS) >= _VERIFS_MAX:
        _VERIFS.pop(next(iter(_VERIFS)))
    _VERIFS[state] = verif
    defi = base64.urlsafe_b64encode(hashlib.sha256(verif.encode()).digest()).rstrip(b"=").decode()
    return AUTH_URL + "?" + urlencode({
        "client_id": settings.YOUTUBE_CLIENT_ID, "redirect_uri": redirect_uri(),
        "response_type": "code", "scope": SCOPES, "access_type": "offline",
        "prompt": "consent", "state": state,
        "code_challenge": defi, "code_challenge_method": "S256"})


async def exchange_code(code: str, state: str) -> str:
    """code → refresh_token ('' si l'état est inconnu — aucun appel alors — ou si Google refuse)."""
    verif = _VERIFS.pop(state, None)
    if not verif:
        logger.warning("youtube oauth : état inconnu ou déjà consommé")
        return ""
    async with _client() as c:
        r = await c.post(TOKEN_URL, data={
            "code": code, "client_id": settings.YOUTUBE_CLIENT_ID,
            "client_secret": settings.YOUTUBE_CLIENT_SECRET, "code_verifier": verif,
            "redirect_uri": redirect_uri(), "grant_type": "authorization_code"})
    if r.status_code != 200:
        logger.warning(f"youtube oauth {r.status_code}: {r.text[:200]}")
        return ""
    return str(r.json().get("refresh_token") or "")


async def access_token() -> str:
    async with _client() as c:
        r = await c.post(TOKEN_URL, data={
            "refresh_token": settings.YOUTUBE_REFRESH_TOKEN,
            "client_id": settings.YOUTUBE_CLIENT_ID,
            "client_secret": settings.YOUTUBE_CLIENT_SECRET,
            "grant_type": "refresh_token"})
    if r.status_code != 200:
        raise RuntimeError(f"youtube token {r.status_code}: {r.text[:160]}")
    return r.json()["access_token"]


async def _morceaux(path: str):
    with open(path, "rb") as f:
        while True:
            b = f.read(_MORCEAU)
            if not b:
                return
            yield b


async def publish(caption: str, video_path, image_path, meta: dict) -> PublishResult:
    if not video_path or not Path(video_path).is_file():
        return PublishResult(False, "youtube: un Short exige une vidéo (aucun rendu attaché)")
    size = Path(video_path).stat().st_size
    first = caption.splitlines()[0] if caption else "Short"
    # YouTube refuse « < » et « > » dans un titre (100 caractères au plus)
    title = ((meta.get("title") or first).replace("<", "").replace(">", "").strip() or "Short")[:100]
    voulu = meta.get("privacy", "public")
    body = {"snippet": {"title": title, "description": caption[:5000], "categoryId": "22"},
            "status": {"privacyStatus": voulu, "selfDeclaredMadeForKids": False}}
    try:
        tok = await access_token()
        async with _client(timeout=900.0) as c:
            r = await c.post(UPLOAD_URL, json=body, headers={
                "Authorization": f"Bearer {tok}", "X-Upload-Content-Type": "video/mp4",
                "X-Upload-Content-Length": str(size)})
            if r.status_code != 200:
                return PublishResult(False, f"youtube init {r.status_code}: {r.text[:200]}")
            loc = r.headers.get("location", "")
            if not loc:
                return PublishResult(False, "youtube init : aucune URI de session (en-tête Location absent)")
            r2 = await c.put(loc, content=_morceaux(video_path), headers={
                "Authorization": f"Bearer {tok}", "Content-Type": "video/mp4",
                "Content-Length": str(size)})
        if r2.status_code not in (200, 201):
            return PublishResult(False, f"youtube upload {r2.status_code}: {r2.text[:200]}")
        j = r2.json()
        vid = str(j.get("id") or "")
        rendu = (j.get("status") or {}).get("privacyStatus") or voulu
        detail = f"youtube: short {vid}"
        if rendu != voulu:
            detail += (f" — rendu {'privé' if rendu == 'private' else rendu} au lieu de "
                       f"{'public' if voulu == 'public' else voulu} : projet Google non vérifié "
                       "(YouTube restreint les envois de l'API tant que le projet n'a pas passé l'audit)")
        return PublishResult(True, detail, vid or None)
    except Exception as e:
        return PublishResult(False, f"youtube error: {e}")


async def fetch_stats(video_ids: list[str]) -> dict[str, dict]:
    """statistics de ≤ 50 vidéos — 1 unité de quota par appel. YouTube ne publie ni partages ni enregistrements."""
    if not video_ids:
        return {}
    tok = await access_token()
    async with _client() as c:
        r = await c.get(VIDEOS_URL, params={"part": "statistics", "id": ",".join(video_ids[:50])},
                        headers={"Authorization": f"Bearer {tok}"})
    if r.status_code != 200:
        return {}
    out = {}
    for it in r.json().get("items", []):
        s = it.get("statistics", {})
        out[it["id"]] = {"views": int(s.get("viewCount", 0)), "likes": int(s.get("likeCount", 0)),
                         "comments": int(s.get("commentCount", 0)), "shares": 0, "saves": 0}
    return out


publishers.register("youtube", lambda: settings.has_youtube, publish)
metrics_service.FETCHERS["youtube"] = fetch_stats   # tâche #29 : la passe de métriques
