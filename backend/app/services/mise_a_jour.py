"""Vérification de mise à jour (plan Settings T10 — tâche #18 du suivi, 29/09/2026).

Le dépôt est une CONSTANTE : le tronc bâti par `scripts/build-installer.ps1` exclut `.git`, l'application installée
ne peut donc pas lire `git config`. Valeur relevée le 29/09/2026 par `git config --get remote.origin.url`
(https://github.com/hugboss1/DeepotusVideo.git).

Contrat relu le 29/09/2026 par un appel réel à `GET https://api.github.com/repos/hugboss1/DeepotusVideo/releases/latest`
(sans jeton, dépôt public) : `tag_name` v2.8.0, `draft`/`prerelease` faux, un asset
`DeepotusVideoGen-Setup-2.8.0.exe` de 130 400 236 o. Le lien `browser_download_url` REDIRIGE (302) vers
`release-assets.githubusercontent.com` — mesuré le même jour ; le plan du 03/09 citait `objects.githubusercontent.com`,
périmé. Chaque saut de redirection est donc gardé (hôtes GitHub seulement), pas seulement l'URL de départ.

Trois règles, tenues par le banc test_mise_a_jour :
  * une vérification par jour au plus (cache disque `maj.json`) ;
  * JAMAIS bloquant : réseau muet = on rend le cache et l'on DIT l'échec ;
  * on télécharge, on ne lance RIEN — c'est l'utilisateur qui lance l'installeur (README).
"""
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx
from loguru import logger

from app.config import APP_VERSION, DATA_ROOT, SSL_VERIFY

DEPOT = "hugboss1/DeepotusVideo"
URL = f"https://api.github.com/repos/{DEPOT}/releases/latest"
PREFIXE_TELECHARGEMENT = f"https://github.com/{DEPOT}/releases/download/"
CACHE = DATA_ROOT / "maj.json"
DOSSIER = DATA_ROOT / "telechargements"
CADENCE_S = 24 * 3600

_ETAT = {"nom": "", "octets": 0, "total": 0, "fini": False, "en_cours": False, "erreur": "", "chemin": ""}


def _tuple(tag: str) -> tuple:
    """(2, 6, 0) depuis « v2.6.0 », « 2.6.0-rc1 »… ; (0, 0, 0) si illisible. On compare des NOMBRES : « v2.10.0 »
    est plus récent que « v2.9.9 », ce qu'une comparaison de texte dirait à l'envers."""
    bouts = re.findall(r"\d+", str(tag or ""))[:3]
    while len(bouts) < 3:
        bouts.append("0")
    return tuple(int(b) for b in bouts)


def _hote_permis(url: str) -> bool:
    h = (urlparse(str(url)).hostname or "").lower()
    return urlparse(str(url)).scheme == "https" and (h == "github.com" or h.endswith(".githubusercontent.com"))


async def _json(url: str, timeout: float = 10.0):
    """Le seul point de sortie réseau de la vérification. Remplacé au banc."""
    async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=timeout, follow_redirects=True) as c:
        r = await c.get(url, headers={"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
                                      "User-Agent": f"DeepotusVideoGen/{APP_VERSION}"})
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, {}


def _lire_cache() -> dict:
    try:
        if CACHE.is_file():
            d = json.loads(CACHE.read_text(encoding="utf-8"))
            if isinstance(d, dict):
                return d
    except (OSError, ValueError):
        pass
    return {}


def _asset(rel: dict) -> dict:
    """L'installeur, pas le premier asset venu : un .exe servi depuis les Releases de CE dépôt."""
    for a in rel.get("assets") or []:
        u = str(a.get("browser_download_url") or "")
        if str(a.get("name") or "").lower().endswith(".exe") and u.startswith(PREFIXE_TELECHARGEMENT):
            return {"nom": str(a.get("name")), "octets": int(a.get("size") or 0), "url": u}
    return {}


async def verifier(force: bool = False) -> dict:
    cache = _lire_cache()
    # le cache n'est « frais » que pour LA version installée : après une mise à jour, on redemande
    frais = (not force and cache and cache.get("installee") == APP_VERSION
             and (time.time() - float(cache.get("verifie_a") or 0)) < CADENCE_S)
    if frais:
        return cache
    erreur = ""
    try:
        code, rel = await _json(URL)
        if code == 200 and isinstance(rel, dict) and rel.get("tag_name"):
            if rel.get("draft") or rel.get("prerelease"):
                rel = {"_ignoree": True}          # une préversion n'est pas une mise à jour proposée
        else:
            erreur = f"GitHub a répondu {code}"
            rel = {}
    except Exception as e:  # noqa: BLE001 — jamais bloquant, c'est la règle
        erreur = str(e)[:200] or type(e).__name__
        rel = {}
    if not rel:
        logger.info(f"mise_a_jour: vérification impossible ({erreur or 'réponse vide'})")
        if cache and cache.get("installee") == APP_VERSION:
            cache = dict(cache)
            cache["erreur"] = erreur
            return cache
        return {"disponible": False, "installee": APP_VERSION, "tag": "", "nom": "", "notes": "", "url": "",
                "publie_le": "", "asset": {}, "verifie_a": time.time(), "erreur": erreur}
    tag = "" if rel.get("_ignoree") else str(rel.get("tag_name") or "")
    out = {"disponible": bool(tag) and _tuple(tag) > _tuple(APP_VERSION),
           "installee": APP_VERSION, "tag": tag, "nom": str(rel.get("name") or tag) if tag else "",
           "notes": str(rel.get("body") or "")[:4000] if tag else "",
           "url": str(rel.get("html_url") or "") if tag else "",
           "publie_le": str(rel.get("published_at") or "") if tag else "",
           "asset": _asset(rel) if tag else {}, "verifie_a": time.time(), "erreur": ""}
    try:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        tmp = CACHE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(CACHE)
    except OSError as e:
        logger.warning(f"mise_a_jour: cache non écrit ({e})")
    return out


async def _flux(url: str, cible: Path, taille: int, etat: dict, transport=None) -> None:
    """Le seul point de sortie réseau du téléchargement. Remplacé au banc. Chaque requête — redirections comprises —
    passe par `_garde` : un saut hors des hôtes GitHub interrompt tout."""
    async def _garde(req):
        if not _hote_permis(str(req.url)):
            raise httpx.RequestError(f"redirection refusée vers {req.url.host}", request=req)

    async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=httpx.Timeout(30.0, read=120.0), follow_redirects=True,
                                 event_hooks={"request": [_garde]}, transport=transport) as c:
        async with c.stream("GET", url, headers={"User-Agent": f"DeepotusVideoGen/{APP_VERSION}"}) as r:
            r.raise_for_status()
            etat["total"] = int(r.headers.get("content-length") or taille or 0)
            with cible.open("wb") as f:
                async for bloc in r.aiter_bytes(1 << 16):
                    f.write(bloc)
                    etat["octets"] += len(bloc)


def etat_telechargement() -> dict:
    return dict(_ETAT)


async def telecharger(url: str, nom: str, octets: int) -> dict:
    """Range l'installeur dans DATA_ROOT/telechargements et s'arrête là. On NE LANCE JAMAIS le fichier.
    Refus : URL hors des Releases de ce dépôt, téléchargement déjà en cours, taille reçue ≠ taille annoncée."""
    if not str(url).startswith(PREFIXE_TELECHARGEMENT):
        return {"ok": False, "erreur": f"téléchargement refusé : seules les Releases de github.com/{DEPOT} sont permises"}
    if _ETAT["en_cours"]:
        return {"ok": False, "erreur": "un téléchargement est déjà en cours"}
    nom = re.sub(r"[^A-Za-z0-9._-]", "_", str(nom or "installeur.exe"))[:120] or "installeur.exe"
    DOSSIER.mkdir(parents=True, exist_ok=True)
    cible = DOSSIER / nom
    partiel = DOSSIER / (nom + ".partiel")
    _ETAT.update(nom=nom, octets=0, total=int(octets or 0), fini=False, en_cours=True, erreur="", chemin="")
    try:
        await _flux(url, partiel, int(octets or 0), _ETAT)
        recu = partiel.stat().st_size
        if octets and recu != int(octets):
            raise OSError(f"taille reçue {recu} o ≠ taille annoncée {int(octets)} o")
        partiel.replace(cible)
    except Exception as e:  # noqa: BLE001
        _ETAT.update(fini=True, en_cours=False, erreur=str(e)[:200] or type(e).__name__)
        try:
            partiel.unlink(missing_ok=True)
        except OSError:
            pass
        return {"ok": False, "erreur": _ETAT["erreur"]}
    _ETAT.update(fini=True, en_cours=False, chemin=str(cible))
    logger.info(f"mise_a_jour: installeur téléchargé -> {cible} ({cible.stat().st_size} o) — à lancer par l'utilisateur")
    return {"ok": True, "chemin": str(cible), "octets": cible.stat().st_size}
