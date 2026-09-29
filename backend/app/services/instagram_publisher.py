"""Instagram Reels — Graph API en HTTP direct (plan scheduler T4 — tâche #26, 29/09/2026).

Compte professionnel, jeton + id du compte IG (IG_ACCESS_TOKEN / IG_BUSINESS_ID). Envoi RÉSUMABLE : le fichier part du
PC vers rupload.facebook.com, aucun hôte public.

Doc relue le 29/09/2026 (WebFetch developers.facebook.com/docs/instagram-platform/content-publishing et
…/reference/instagram-media/insights) :
- l'envoi résumable accepte « A file located on your computer » → RESUMABLE_SUPPORTED = True ;
- conteneur `POST /<IG_ID>/media` (media_type=REELS, upload_type=resumable) → `uri` ; envoi `POST` sur cette uri avec
  `Authorization: OAuth <jeton>`, `offset: 0`, `file_size` → {"success": true} ; statut FINISHED / IN_PROGRESS / ERROR /
  EXPIRED ; « We recommend querying a container's status once per minute, for no more than 5 minutes » ;
  `POST /<IG_ID>/media_publish` (creation_id) ;
- « Instagram accounts are limited to 100 API-published posts within a 24-hour moving period » — le plan disait 50 ;
  la fenêtre est GLISSANTE, qu'aucun seau par jour ne borne vraiment : le compteur d'Instagram
  (`GET /<IG_ID>/content_publishing_limit`) est demandé AVANT chaque envoi et fait foi ;
- deux connexions : « Business Login for Instagram » (jeton utilisateur Instagram, préfixe « IG », graph.instagram.com)
  ou « Facebook Login for Business » (jeton de Page, graph.facebook.com) — l'hôte suit le jeton ; version v25.0 ;
- métriques des Reels : `views` (« Total number of times IG Media has been played on Instagram »), likes, comments,
  shares, saved ; `impressions` est déprécié pour les médias d'après le 2 juillet 2024.

Le jeton n'apparaît dans aucun détail (`_scrub`) ; le fichier part par un générateur asynchrone (le vrai
httpx.AsyncClient refuse un fichier synchrone)."""
import asyncio
from pathlib import Path

import httpx

from app.config import settings, SSL_VERIFY
from app.services import publishers
from app.services.publishers import PublishResult

VERSION = "v25.0"
RESUMABLE_SUPPORTED = True          # mesuré le 29/09/2026 (voir le docstring)
METRICS = "views,likes,comments,shares,saved"
# un premier coup d'œil à 15 s (un Reel court est souvent prêt), puis au rythme recommandé ; 4 min 45 au total
POLL_DELAIS = (15, 30, 60, 60, 60, 60)
_MORCEAU = 1 << 20


def _client(timeout: float = 60.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(verify=SSL_VERIFY, timeout=timeout)


def _graph() -> str:
    tok = settings.IG_ACCESS_TOKEN.strip()
    hote = "graph.instagram.com" if tok.startswith("IG") else "graph.facebook.com"
    return f"https://{hote}/{VERSION}"


def _scrub(text: str) -> str:
    tok = settings.IG_ACCESS_TOKEN.strip()
    return text.replace(tok, "***") if tok else text


def available() -> bool:
    return settings.has_instagram and RESUMABLE_SUPPORTED


async def _morceaux(path: str):
    with open(path, "rb") as f:
        while True:
            b = f.read(_MORCEAU)
            if not b:
                return
            yield b


async def publish(caption: str, video_path, image_path, meta: dict) -> PublishResult:
    if not video_path or not Path(video_path).is_file():
        return PublishResult(False, "instagram: un Reel exige une vidéo (aucun rendu attaché)")
    tok, ig, g = settings.IG_ACCESS_TOKEN.strip(), settings.IG_BUSINESS_ID.strip(), _graph()
    size = Path(video_path).stat().st_size
    try:
        async with _client(timeout=900.0) as c:
            lim = await c.get(f"{g}/{ig}/content_publishing_limit",
                              params={"fields": "quota_usage,config", "access_token": tok})
            if lim.status_code != 200:
                return PublishResult(False, f"instagram content_publishing_limit {lim.status_code}: "
                                            f"{_scrub(lim.text)[:160]} — envoi suspendu faute de compteur")
            d = (lim.json().get("data") or [{}])[0]
            used, total = int(d.get("quota_usage") or 0), int((d.get("config") or {}).get("quota_total") or 100)
            if used >= total:
                return PublishResult(False, f"quota instagram : {used}/{total} sur 24 h glissantes (compteur d'Instagram)")
            r = await c.post(f"{g}/{ig}/media", data={
                "media_type": "REELS", "upload_type": "resumable",
                "caption": caption[:2200], "share_to_feed": "true", "access_token": tok})
            if r.status_code != 200:
                return PublishResult(False, f"instagram container {r.status_code}: {_scrub(r.text)[:200]}")
            j = r.json()
            container, uri = str(j.get("id", "")), j.get("uri", "")
            if not container or not uri:
                return PublishResult(False, "instagram container : ni id ni uri d'envoi dans la réponse")
            r2 = await c.post(uri, content=_morceaux(video_path), headers={
                "Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(size),
                "Content-Length": str(size)})
            if r2.status_code != 200 or not r2.json().get("success"):
                return PublishResult(False, f"instagram upload {r2.status_code}: {_scrub(r2.text)[:200]}")
            for attente in POLL_DELAIS:
                await asyncio.sleep(attente)
                s = await c.get(f"{g}/{container}", params={"fields": "status_code,status", "access_token": tok})
                code = s.json().get("status_code")
                if code == "FINISHED":
                    break
                if code in ("ERROR", "EXPIRED"):
                    return PublishResult(False, f"instagram container {code}: {_scrub(str(s.json().get('status', '')))[:200]}")
            else:
                return PublishResult(False, f"instagram: conteneur jamais FINISHED après {sum(POLL_DELAIS)} s")
            r3 = await c.post(f"{g}/{ig}/media_publish", data={"creation_id": container, "access_token": tok})
        if r3.status_code != 200:
            return PublishResult(False, f"instagram publish {r3.status_code}: {_scrub(r3.text)[:200]}")
        mid = str(r3.json().get("id") or "")
        return PublishResult(True, f"instagram: reel {mid}", mid or None)
    except Exception as e:
        return PublishResult(False, f"instagram error: {_scrub(str(e))}")


def _valeur(d: dict) -> int:
    if isinstance(d.get("total_value"), dict):
        return int(d["total_value"].get("value") or 0)
    return int(((d.get("values") or [{}])[0] or {}).get("value") or 0)


async def fetch_insights(media_ids: list[str]) -> dict[str, dict]:
    out = {}
    tok, g = settings.IG_ACCESS_TOKEN.strip(), _graph()
    async with _client() as c:
        for mid in media_ids:
            r = await c.get(f"{g}/{mid}/insights", params={"metric": METRICS, "access_token": tok})
            if r.status_code != 200:
                continue
            vals = {d.get("name"): _valeur(d) for d in r.json().get("data", [])}
            out[mid] = {"views": vals.get("views", 0), "likes": vals.get("likes", 0),
                        "comments": vals.get("comments", 0), "shares": vals.get("shares", 0),
                        "saves": vals.get("saved", 0)}
    return out


publishers.register("instagram", available, publish)
