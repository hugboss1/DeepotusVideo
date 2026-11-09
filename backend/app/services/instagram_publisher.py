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
import json
import re
from pathlib import Path

import httpx

from app.config import DATA_ROOT, settings, SSL_VERIFY
from app.services.comptes import cred   # t203 : identifiants du compte courant (clés plates sans compte)
from app.services import metrics_service, publishers
from app.services.publishers import PublishResult

VERSION = "v25.0"
RESUMABLE_SUPPORTED = True          # mesuré le 29/09/2026 (voir le docstring)
METRICS = "views,likes,comments,shares,saved"
# t491 : le temps de visionnage moyen d'un Reel (millisecondes), demandé À PART : un refus (compte, type de
# média, version) ne doit pas faire perdre les cinq mesures
METRIC_VISIONNAGE = "ig_reels_avg_watch_time"
# un premier coup d'œil à 15 s (un Reel court est souvent prêt), puis au rythme recommandé ; 4 min 45 au total
POLL_DELAIS = (15, 30, 60, 60, 60, 60)
_MORCEAU = 1 << 20


def _client(timeout: float = 60.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(verify=SSL_VERIFY, timeout=timeout)


def _graph() -> str:
    tok = cred.IG_ACCESS_TOKEN.strip()
    hote = "graph.instagram.com" if tok.startswith("IG") else "graph.facebook.com"
    return f"https://{hote}/{VERSION}"


def _scrub(text: str) -> str:
    tok = cred.IG_ACCESS_TOKEN.strip()
    return text.replace(tok, "***") if tok else text


def available() -> bool:
    return cred.has_instagram and RESUMABLE_SUPPORTED


async def _morceaux(path: str):
    with open(path, "rb") as f:
        while True:
            b = f.read(_MORCEAU)
            if not b:
                return
            yield b


# ---- t494 (lot G4, 09/11/2026) : les FORMES d'un post Instagram ---------------------------------------------------------
# Doc relue le 09/11/2026 (developers.facebook.com/docs/instagram-platform/content-publishing, …/reference/ig-user/media,
# …/content-publishing/resumable-uploads) :
# - une IMAGE ne se crée que par `image_url` (« the image must be on a public server », JPEG seul, 8 Mo, largeur 320 à
#   1440, rapport 4:5 à 1.91:1) : aucun envoi d'un fichier local ;
# - l'envoi résumable (fichier local) existe pour REELS, STORIES et VIDEO de carrousel, vidéo seulement ;
# - `trial_params` ({"graduation_strategy": MANUAL | SS_PERFORMANCE}, media_type REELS) n'est PAS dans les paramètres de
#   l'envoi résumable (« Other parameters are not supported ») : un reel d'essai passe donc par `video_url` ;
# - carrousel : enfants `is_carousel_item`, parent `media_type=CAROUSEL` + `children`, 20 éléments au plus, compte pour
#   UN post ; Story : pas de légende.
# Décision de l'utilisateur (09/11) : ce qui exige une adresse publique passe par un DÉPÔT TEMPORAIRE chez fal (la clé
# fal sert déjà aux générations), seulement si le réglage `depot_fal` est activé — jamais par défaut. Sans lui, la forme
# est refusée AVANT tout appel, et le refus dit quoi activer.
FORMES = ("reel", "essai", "image", "carrousel", "story")
GRADUATIONS = ("MANUAL", "SS_PERFORMANCE")
CARROUSEL_MIN, CARROUSEL_MAX = 2, 20
IMAGE_LARGEUR_MAX, IMAGE_LARGEUR_MIN, IMAGE_POIDS_MAX = 1440, 320, 8 * 1024 * 1024
RAPPORT_MIN, RAPPORT_MAX = 0.8, 1.91          # largeur / hauteur d'une image de post ou de carrousel
POLL_IMAGE = (2, 5, 10, 20)
_FICHIER_REGLAGE = DATA_ROOT / "scheduler" / "instagram.json"
_NOM_IMAGE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ -]{0,180}\.(png|jpe?g|webp)$", re.I)


def reglage() -> dict:
    """{depot_fal} : False tant que l'utilisateur ne l'a pas activé (fichier absent ou illisible = False)."""
    try:
        d = json.loads(_FICHIER_REGLAGE.read_text("utf-8")) or {}
    except (OSError, ValueError):
        d = {}
    return {"depot_fal": d.get("depot_fal") is True}


def regler(depot_fal: bool) -> dict:
    _FICHIER_REGLAGE.parent.mkdir(parents=True, exist_ok=True)
    _FICHIER_REGLAGE.write_text(json.dumps({"depot_fal": depot_fal is True}), "utf-8")
    return reglage()


def format_post(brut) -> dict:
    """Le format Instagram d'un post, NORMALISÉ depuis `brief.instagram` : {forme, graduation, images}. Tout ce qui est
    inconnu retombe sur le Reel (comportement d'avant t494) ; les images sont des NOMS simples de la Bibliothèque."""
    b = brut if isinstance(brut, dict) else {}
    forme = b.get("forme") if b.get("forme") in FORMES else "reel"
    grad = b.get("graduation") if b.get("graduation") in GRADUATIONS else "MANUAL"
    images = [x for x in (b.get("images") or []) if isinstance(x, str) and _NOM_IMAGE.match(x)] if isinstance(b.get("images"), list) else []
    return {"forme": forme, "graduation": grad, "images": images[:CARROUSEL_MAX]}


def exige_depot(forme: str, a_video: bool) -> bool:
    """La forme a-t-elle besoin d'une adresse publique ? Le Reel et la Story VIDÉO partent du fichier local."""
    return forme in ("essai", "image", "carrousel") or (forme == "story" and not a_video)


async def _deposer(path: Path) -> str:                              # seam : le dépôt temporaire chez fal
    import fal_client
    return await fal_client.upload_file_async(str(path))


def _jpeg(src: str, dossier: Path, story: bool) -> Path:
    """Une copie JPEG sRGB de l'image, dans les bornes d'Instagram (largeur, poids). ValueError dit pourquoi une image
    ne convient pas : on ne recadre JAMAIS en silence."""
    from PIL import Image
    with Image.open(src) as im:
        im = im.convert("RGB")
        l, h = im.size
        if not story and not (RAPPORT_MIN <= l / h <= RAPPORT_MAX):
            raise ValueError(f"{Path(src).name} : rapport {l}×{h} hors de 4:5 à 1.91:1, recadrez l'image")
        if l < IMAGE_LARGEUR_MIN:
            raise ValueError(f"{Path(src).name} : {l} px de large, il en faut au moins {IMAGE_LARGEUR_MIN}")
        if l > IMAGE_LARGEUR_MAX:
            im = im.resize((IMAGE_LARGEUR_MAX, max(1, round(h * IMAGE_LARGEUR_MAX / l))), Image.LANCZOS)
        dest = dossier / (Path(src).stem[:60] + ".jpg")
        for q in (90, 82, 74, 66):
            im.save(dest, "JPEG", quality=q, optimize=True)
            if dest.stat().st_size <= IMAGE_POIDS_MAX:
                return dest
    raise ValueError(f"{Path(src).name} : plus de 8 Mo même compressée")


async def _quota(c, g, ig, tok):
    """None si l'on peut publier, sinon le refus (le compteur d'Instagram fait foi)."""
    lim = await c.get(f"{g}/{ig}/content_publishing_limit", params={"fields": "quota_usage,config", "access_token": tok})
    if lim.status_code != 200:
        return PublishResult(False, f"instagram content_publishing_limit {lim.status_code}: "
                                    f"{_scrub(lim.text)[:160]} — envoi suspendu faute de compteur")
    d = (lim.json().get("data") or [{}])[0]
    used, total = int(d.get("quota_usage") or 0), int((d.get("config") or {}).get("quota_total") or 100)
    if used >= total:
        return PublishResult(False, f"quota instagram : {used}/{total} sur 24 h glissantes (compteur d'Instagram)")
    return None


async def _attendre(c, g, container, tok, delais):
    """None quand le conteneur est FINISHED, sinon le refus."""
    for attente in delais:
        await asyncio.sleep(attente)
        s = await c.get(f"{g}/{container}", params={"fields": "status_code,status", "access_token": tok})
        code = s.json().get("status_code")
        if code == "FINISHED":
            return None
        if code in ("ERROR", "EXPIRED"):
            return PublishResult(False, f"instagram container {code}: {_scrub(str(s.json().get('status', '')))[:200]}")
    return PublishResult(False, f"instagram: conteneur jamais FINISHED après {sum(delais)} s")


async def _conteneur(c, g, ig, donnees):
    """(id, uri, refus) d'un POST /<IG>/media."""
    r = await c.post(f"{g}/{ig}/media", data=donnees)
    if r.status_code != 200:
        return "", "", PublishResult(False, f"instagram container {r.status_code}: {_scrub(r.text)[:200]}")
    j = r.json()
    return str(j.get("id", "")), j.get("uri", ""), None


async def _publier_conteneur(c, g, ig, tok, container, nom):
    r3 = await c.post(f"{g}/{ig}/media_publish", data={"creation_id": container, "access_token": tok})
    if r3.status_code != 200:
        return PublishResult(False, f"instagram publish {r3.status_code}: {_scrub(r3.text)[:200]}")
    mid = str(r3.json().get("id") or "")
    return PublishResult(True, f"instagram: {nom} {mid}", mid or None)


async def _video_locale(c, g, ig, tok, video_path, donnees, nom):
    """Reel ou Story vidéo par l'envoi résumable d'un fichier local (le chemin d'avant t494, à l'octet pour le Reel)."""
    size = Path(video_path).stat().st_size
    container, uri, refus = await _conteneur(c, g, ig, dict(donnees, upload_type="resumable", access_token=tok))
    if refus:
        return refus
    if not container or not uri:
        return PublishResult(False, "instagram container : ni id ni uri d'envoi dans la réponse")
    r2 = await c.post(uri, content=_morceaux(video_path), headers={
        "Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(size), "Content-Length": str(size)})
    if r2.status_code != 200 or not r2.json().get("success"):
        return PublishResult(False, f"instagram upload {r2.status_code}: {_scrub(r2.text)[:200]}")
    return await _attendre(c, g, container, tok, POLL_DELAIS) or await _publier_conteneur(c, g, ig, tok, container, nom)


async def _par_adresse(c, g, ig, tok, donnees, nom, delais):
    """Un conteneur créé depuis une adresse publique (dépôt), attendu puis publié."""
    container, _uri, refus = await _conteneur(c, g, ig, dict(donnees, access_token=tok))
    if refus:
        return refus
    if not container:
        return PublishResult(False, "instagram container : pas d'id dans la réponse")
    return await _attendre(c, g, container, tok, delais) or await _publier_conteneur(c, g, ig, tok, container, nom)


async def publish(caption: str, video_path, image_path, meta: dict) -> PublishResult:
    meta = meta if isinstance(meta, dict) else {}
    brief = meta.get("brief") if isinstance(meta.get("brief"), dict) else {}
    f = format_post(brief.get("instagram"))
    forme = f["forme"]
    a_video = bool(video_path and Path(video_path).is_file())
    image_path = image_path or meta.get("image")
    if forme in ("reel", "essai") and not a_video:
        return PublishResult(False, "instagram: un Reel exige une vidéo (aucun rendu attaché)")
    images = []
    if forme == "carrousel":
        images = [str(settings.images_path / n) for n in f["images"]]
        manquantes = [Path(p).name for p in images if not Path(p).is_file()]
        if manquantes:
            return PublishResult(False, f"instagram: image(s) du carrousel introuvable(s) : {', '.join(manquantes)[:160]}")
        if not (CARROUSEL_MIN <= len(images) <= CARROUSEL_MAX):
            return PublishResult(False, f"instagram: un carrousel demande {CARROUSEL_MIN} à {CARROUSEL_MAX} images "
                                        f"({len(images)} choisie(s))")
    elif forme == "image" or (forme == "story" and not a_video):
        if not image_path or not Path(image_path).is_file():
            return PublishResult(False, f"instagram: {'une Story' if forme == 'story' else 'un post image'} exige une "
                                        "image ou une vidéo attachée" if forme == "story" else
                                        "instagram: un post image exige une image attachée")
        images = [str(image_path)]
    if exige_depot(forme, a_video):
        if not reglage()["depot_fal"]:
            return PublishResult(False, f"instagram: la forme « {forme} » demande une adresse publique ; activez le dépôt "
                                        "temporaire chez fal dans le format Instagram du post")
        if not (settings.FAL_KEY or "").strip():
            return PublishResult(False, "instagram: le dépôt temporaire demande une clé fal (Réglages › Clés d'API)")
    tok, ig, g = cred.IG_ACCESS_TOKEN.strip(), cred.IG_BUSINESS_ID.strip(), _graph()
    try:
        import tempfile
        with tempfile.TemporaryDirectory(prefix="dzig_") as tmp:
            try:
                jpegs = [_jpeg(p, Path(tmp), forme == "story") for p in images]
            except ValueError as e:
                return PublishResult(False, f"instagram: {e}")
            async with _client(timeout=900.0) as c:
                refus = await _quota(c, g, ig, tok)
                if refus:
                    return refus
                if forme == "reel":
                    return await _video_locale(c, g, ig, tok, video_path, {
                        "media_type": "REELS", "caption": caption[:2200], "share_to_feed": "true"}, "reel")
                if forme == "story" and a_video:
                    return await _video_locale(c, g, ig, tok, video_path, {"media_type": "STORIES"}, "story")
                if forme == "essai":
                    url = await _deposer(Path(video_path))
                    return await _par_adresse(c, g, ig, tok, {
                        "media_type": "REELS", "video_url": url, "caption": caption[:2200],
                        "trial_params": json.dumps({"graduation_strategy": f["graduation"]})}, "reel d'essai", POLL_DELAIS)
                urls = [await _deposer(p) for p in jpegs]
                if forme == "image":
                    return await _par_adresse(c, g, ig, tok, {"image_url": urls[0], "caption": caption[:2200]},
                                              "image", POLL_IMAGE)
                if forme == "story":
                    return await _par_adresse(c, g, ig, tok, {"image_url": urls[0], "media_type": "STORIES"},
                                              "story", POLL_IMAGE)
                enfants = []
                for u in urls:
                    cid, _uri, refus = await _conteneur(c, g, ig, {"image_url": u, "is_carousel_item": "true",
                                                                   "access_token": tok})
                    if refus:
                        return refus
                    if not cid:
                        return PublishResult(False, "instagram container : pas d'id pour une image du carrousel")
                    enfants.append(cid)
                return await _par_adresse(c, g, ig, tok, {"media_type": "CAROUSEL", "children": ",".join(enfants),
                                                          "caption": caption[:2200]}, "carrousel", POLL_IMAGE)
    except Exception as e:
        return PublishResult(False, f"instagram error: {_scrub(str(e))}")


def _valeur(d: dict) -> int:
    if isinstance(d.get("total_value"), dict):
        return int(d["total_value"].get("value") or 0)
    return int(((d.get("values") or [{}])[0] or {}).get("value") or 0)


async def fetch_insights(media_ids: list[str]) -> dict[str, dict]:
    out = {}
    tok, g = cred.IG_ACCESS_TOKEN.strip(), _graph()
    async with _client() as c:
        for mid in media_ids:
            r = await c.get(f"{g}/{mid}/insights", params={"metric": METRICS, "access_token": tok})
            if r.status_code != 200:
                continue
            vals = {d.get("name"): _valeur(d) for d in r.json().get("data", [])}
            out[mid] = {"views": vals.get("views", 0), "likes": vals.get("likes", 0),
                        "comments": vals.get("comments", 0), "shares": vals.get("shares", 0),
                        "saves": vals.get("saved", 0)}
            r2 = await c.get(f"{g}/{mid}/insights", params={"metric": METRIC_VISIONNAGE, "access_token": tok})
            if r2.status_code == 200:
                v2 = {d.get("name"): _valeur(d) for d in r2.json().get("data", [])}
                if v2.get(METRIC_VISIONNAGE):
                    out[mid]["avg_watch_ms"] = v2[METRIC_VISIONNAGE]
    return out


# ---- t492 (lot G2, 09/11/2026) : les chiffres du COMPTE pour l'écran Croissance ----------------------------------------
# Chaque mesure a son propre appel : un compte, un type de connexion ou une version qui en refuse une ne fait pas
# perdre les autres ; ce qui n'a pas pu être lu est nommé dans `illisibles`. Gardé en mémoire CACHE_COMPTE_S secondes.
METRIQUES_COMPTE = ("reach", "views", "total_interactions", "follows_and_unfollows")
JOURS_COMPTE_MAX = 30                 # la fenêtre d'un appel d'insights de compte
CACHE_COMPTE_S = 900
_cache_compte: dict = {}


def _total_et_ventilation(d: dict) -> tuple[int, dict]:
    """(total, {dimension: valeur}) d'une mesure rendue en `total_value`, ventilée ou non."""
    tv = d.get("total_value") if isinstance(d.get("total_value"), dict) else {}
    vent = {}
    for b in tv.get("breakdowns") or []:
        for r in (b or {}).get("results") or []:
            dims = r.get("dimension_values") or []
            if dims:
                vent[str(dims[0]).upper()] = int(r.get("value") or 0)
    total = int(tv.get("value") or 0) or sum(vent.values())
    return total, vent


async def fetch_compte(days: int = 30, maintenant: float | None = None) -> dict | None:
    """{username, followers, reach, views, interactions, follows, unfollows, non_abonnes_pct, jours, illisibles} du
    compte Instagram COURANT ; None si aucun compte n'est relié. Aucune écriture, le jeton n'est dans aucun détail."""
    import time
    if not available():
        return None
    tok, ig_id, g = cred.IG_ACCESS_TOKEN.strip(), cred.IG_BUSINESS_ID.strip(), _graph()
    jours = max(1, min(JOURS_COMPTE_MAX, int(days or 30)))
    t = time.time() if maintenant is None else maintenant
    cle = (ig_id, jours)
    if cle in _cache_compte and t - _cache_compte[cle][0] < CACHE_COMPTE_S:
        return _cache_compte[cle][1]
    out = {"username": None, "followers": None, "reach": None, "views": None, "interactions": None, "follows": None,
           "unfollows": None, "non_abonnes_pct": None, "jours": jours, "illisibles": []}
    fin = int(t)
    base = {"period": "day", "metric_type": "total_value", "since": fin - jours * 86400, "until": fin,
            "access_token": tok}
    async with _client() as c:
        r = await c.get(f"{g}/{ig_id}", params={"fields": "username,followers_count", "access_token": tok})
        if r.status_code == 200:
            j = r.json()
            out["username"], out["followers"] = j.get("username"), j.get("followers_count")
        else:
            out["illisibles"].append("profil")
        for m in METRIQUES_COMPTE:
            p = dict(base, metric=m)
            if m in ("views", "follows_and_unfollows"):
                p["breakdown"] = "follow_type"
            r = await c.get(f"{g}/{ig_id}/insights", params=p)
            data = (r.json().get("data") or []) if r.status_code == 200 else []
            if not data:
                out["illisibles"].append(m)
                continue
            total, vent = _total_et_ventilation(data[0])
            if m == "reach":
                out["reach"] = total
            elif m == "total_interactions":
                out["interactions"] = total
            elif m == "views":
                out["views"] = total
                if total and "NON_FOLLOWER" in vent:
                    out["non_abonnes_pct"] = round(100.0 * vent["NON_FOLLOWER"] / total)
            else:
                out["follows"], out["unfollows"] = vent.get("FOLLOWER"), vent.get("NON_FOLLOWER")
    _cache_compte[cle] = (t, out)
    return out


publishers.register("instagram", available, publish)
metrics_service.FETCHERS["instagram"] = fetch_insights   # tâche #29 : la passe de métriques
