# -*- coding: utf-8 -*-
"""t352 (27/10/2026) — la collecte de veille NIVEAU 1, portée de `scripts/collecte.py` du skill veille-concurrents.

Sources ouvertes, lecture seule : Hacker News (API Algolia), commentaires YouTube (yt-dlp, sans clé, sans télécharger la
vidéo), avis App Store (flux RSS public d'Apple). Reddit (OAuth) et le navigateur restent hors de l'app (spec §8).

Une ligne par verbatim dans `brut/<source>-<concurrent>.jsonl` :
  {concurrent, source, url, date, auteur_hash, texte, score, collecte_le, requete}
L'auteur n'est JAMAIS écrit en clair (empreinte courte) ; doublon = même lien ET même texte (les avis App Store partagent
un même lien). Plafonds par requête, par vidéo, par app, au total et en durée ; une panne arrête une cible, pas la
collecte : ce qui est acquis reste, la panne rejoint les limites du rapport.

Coutures du banc : `_GET_JSON` (url -> dict), `_YTDLP` (vidéo, maxi -> info yt-dlp), `_ytdlp_commande`, `_horloge`.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import hashlib
import html
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path
from typing import Callable

import httpx

UA = "deepotus-veille/0.1 (veille concurrentielle, lecture seule)"
MAX_PAR_REQUETE = 100                  # commentaires HN par requête
MAX_PAR_VIDEO = 150                    # commentaires par vidéo
MAX_VIDEOS_PAR_CONCURRENT = 3
MAX_AVIS_APP_PAYS = 100                # avis par app et par pays
MAX_CONCURRENTS = 15
MAX_REQUETES = 4                       # requêtes HN par concurrent
MAX_APPS = 2
MAX_PAYS = 3
MAX_BRUT = 3000                        # textes neufs par collecte
DUREE_MAX = 900.0                      # secondes, toute la collecte
DELAI_HTTP = 20.0
DELAI_YTDLP = 180.0                    # secondes par vidéo
DEPUIS_JOURS = 548                     # 18 mois (HN)

_ID = re.compile(r"^[a-z0-9_-]{1,30}$")
_VIDEO = re.compile(r"^[A-Za-z0-9_-]{11}$")
_APP = re.compile(r"^\d{1,12}$")
_PAYS = re.compile(r"^[a-z]{2}$")
PERIMETRE_DEFAUT: dict = json.loads((Path(__file__).with_name("veille_perimetre_defaut.json")).read_text(encoding="utf-8"))


class _Absent(Exception):
    """yt-dlp introuvable : la source YouTube est indisponible pour toute la collecte."""


class _Plafond(Exception):
    """Plafond global atteint (textes ou durée)."""


# ---- périmètre -------------------------------------------------------------------------------------------------------

def _textes(v, n: int, maxi: int = 120) -> list[str]:
    if not isinstance(v, list):
        return []
    return [s.strip()[:maxi] for s in v if isinstance(s, str) and s.strip()][:n]


def valider_perimetre(p: dict) -> dict:
    """Le périmètre normalisé et borné aux plafonds ; ValueError sur un identifiant hors liste blanche."""
    if not isinstance(p, dict) or not isinstance(p.get("concurrents"), list):
        raise ValueError("périmètre : liste « concurrents » attendue")
    out, vus = [], set()
    for c in p["concurrents"][:MAX_CONCURRENTS]:
        if not isinstance(c, dict) or not isinstance(c.get("id"), str) or not _ID.match(c["id"]):
            raise ValueError(f"périmètre : id de concurrent invalide : {str((c or {}).get('id'))[:40]}")
        if c["id"] in vus:
            continue
        vus.add(c["id"])
        youtube, apps, pays = _textes(c.get("youtube"), 50), _textes(c.get("appstore"), 50), _textes(c.get("pays"), 50)
        for v, rx, quoi in ((youtube, _VIDEO, "vidéo YouTube"), (apps, _APP, "id App Store"), (pays, _PAYS, "pays")):
            mauvais = [x for x in v if not rx.match(x)]
            if mauvais:
                raise ValueError(f"périmètre : {quoi} invalide : {mauvais[0][:40]}")
        out.append({"id": c["id"], "famille": str(c.get("famille") or "")[:30], "hn": _textes(c.get("hn"), MAX_REQUETES),
                    "youtube": youtube[:MAX_VIDEOS_PAR_CONCURRENT], "appstore": apps[:MAX_APPS],
                    "pays": pays[:MAX_PAYS] or ["us"]})
    jours = p.get("depuis_jours", DEPUIS_JOURS)
    jours = jours if isinstance(jours, int) and 1 <= jours <= 3650 else DEPUIS_JOURS
    return {"version": 1, "depuis_jours": jours, "concurrents": out}


# ---- les lignes ------------------------------------------------------------------------------------------------------

def empreinte(auteur: str | None) -> str:
    return hashlib.sha256(auteur.encode("utf-8")).hexdigest()[:10] if auteur else ""


def cle(l: dict) -> str:
    """Doublon = même lien ET même texte."""
    return hashlib.sha256((str(l.get("url")) + "|" + str(l.get("texte"))).encode("utf-8")).hexdigest()


def _ligne(concurrent, source, url, date, auteur, texte, score, requete) -> dict:
    return {"concurrent": concurrent, "source": source, "url": url, "date": date, "auteur_hash": empreinte(auteur),
            "texte": (texte or "").strip(), "score": score,
            "collecte_le": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "requete": requete}


def _sans_html(t: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", re.sub(r"<p>", "\n", t or "")))


# ---- réseau (coutures) -----------------------------------------------------------------------------------------------

async def _get_json_defaut(url: str) -> dict:
    async with httpx.AsyncClient(timeout=DELAI_HTTP, follow_redirects=True, headers={"User-Agent": UA}) as c:
        r = await c.get(url)
        r.raise_for_status()
        return r.json()


def _ytdlp_commande_defaut() -> list[str] | None:
    """Le module yt_dlp du python de l'app, sinon l'exécutable du PATH, sinon None (yt-dlp n'est pas embarqué)."""
    if importlib.util.find_spec("yt_dlp") is not None:
        return [sys.executable, "-m", "yt_dlp"]
    exe = shutil.which("yt-dlp")
    return [exe] if exe else None


async def _ytdlp_defaut(video: str, maxi: int) -> dict:
    cmd = _ytdlp_commande()
    if not cmd:
        raise _Absent("yt-dlp introuvable")
    with tempfile.TemporaryDirectory(prefix="dzveille_") as tmp:
        modele = str(Path(tmp) / "v")
        args = cmd + ["--skip-download", "--write-comments", "--no-warnings", "--no-playlist",
                      "--extractor-args", f"youtube:max_comments={maxi},all,100;comment_sort=top",
                      "-o", modele, f"https://www.youtube.com/watch?v={video}"]
        drapeaux = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        await asyncio.to_thread(subprocess.run, args, check=True, capture_output=True, timeout=DELAI_YTDLP,
                                creationflags=drapeaux)
        return json.loads(Path(modele + ".info.json").read_text(encoding="utf-8"))


_GET_JSON = _get_json_defaut
_YTDLP = _ytdlp_defaut
_ytdlp_commande = _ytdlp_commande_defaut
_horloge = time.monotonic


def _objet(v) -> dict:
    """Une réponse JSON doit être un objet : une liste ou une chaîne est une panne de la source, pas de la collecte."""
    if not isinstance(v, dict):
        raise ValueError(f"réponse inattendue ({type(v).__name__})")
    return v


# ---- les sources -----------------------------------------------------------------------------------------------------

async def _hn(cid: str, requete: str, depuis: int, echeance: float, limites: list) -> list[dict]:
    out, page = [], 0
    while len(out) < MAX_PAR_REQUETE and _horloge() < echeance:
        q = urllib.parse.urlencode({"query": requete, "tags": "comment", "hitsPerPage": 100, "page": page,
                                    "numericFilters": f"created_at_i>{depuis}"})
        try:
            data = _objet(await _GET_JSON(f"https://hn.algolia.com/api/v1/search?{q}"))
            hits = [h for h in data.get("hits") or [] if isinstance(h, dict)]
            nb_pages = int(data.get("nbPages") or 0)
        except Exception as e:  # noqa: BLE001 — la panne arrête cette requête, l'acquis reste
            limites.append(f"hn « {requete[:40]} » page {page} : {type(e).__name__} : {str(e)[:120]}")
            break
        for h in hits:
            out.append(_ligne(cid, "hn", f"https://news.ycombinator.com/item?id={h.get('objectID')}",
                              h.get("created_at"), h.get("author"), _sans_html(h.get("comment_text") or ""),
                              h.get("points"), requete))
        page += 1
        if page >= nb_pages:
            break
        await asyncio.sleep(0.5 if _GET_JSON is _get_json_defaut else 0)
    return out[:MAX_PAR_REQUETE]


async def _youtube(cid: str, video: str) -> list[dict]:
    info = await _YTDLP(video, MAX_PAR_VIDEO)
    url = f"https://www.youtube.com/watch?v={video}"
    out = []
    for c in (info.get("comments") or [])[:MAX_PAR_VIDEO]:
        ts = c.get("timestamp")
        date = dt.datetime.fromtimestamp(ts, dt.timezone.utc).isoformat() if ts else None
        out.append(_ligne(cid, "youtube", f"{url}&lc={c.get('id')}", date, c.get("author"), c.get("text"),
                          c.get("like_count"), str(info.get("title") or "")[:200]))
    return out


async def _appstore(cid: str, app_id: str, pays: str, echeance: float, limites: list) -> list[dict]:
    out = []
    for page in range(1, 11):
        if _horloge() >= echeance:
            break
        url = f"https://itunes.apple.com/{pays}/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json"
        try:
            data = _objet(await _GET_JSON(url))
            entrees = _objet(data.get("feed") or {}).get("entry") or []
        except Exception as e:  # noqa: BLE001 — toute panne est dite ; seule la page au-delà de la fin (400/404) est muette
            statut = getattr(getattr(e, "response", None), "status_code", None)
            if page == 1 or statut not in (400, 404):
                limites.append(f"appstore {app_id} {pays} page {page} : {type(e).__name__} : {str(e)[:120]}")
            break
        if isinstance(entrees, dict):
            entrees = [entrees]
        avis = [e for e in entrees if isinstance(e, dict) and "im:rating" in e]
        if not avis:
            break
        for e in avis:
            try:
                note = int(e["im:rating"]["label"])
                texte = f"{e['title']['label']} — {e['content']['label']}"
            except (KeyError, TypeError, ValueError):
                continue
            out.append(_ligne(cid, f"appstore-{pays}", ((e.get("link") or {}).get("attributes") or {}).get("href", url),
                              (e.get("updated") or {}).get("label"), ((e.get("author") or {}).get("name") or {}).get("label"),
                              texte, note, f"id={app_id}"))
        if len(out) >= MAX_AVIS_APP_PAYS:
            break
        await asyncio.sleep(0.5 if _GET_JSON is _get_json_defaut else 0)
    return out[:MAX_AVIS_APP_PAYS]


# ---- la collecte -----------------------------------------------------------------------------------------------------

def _ecrire(brut: Path, source: str, cid: str, lignes: list[dict], reste: int) -> int:
    """Ajoute les lignes neuves (sans doublon contre le fichier) ; rend le nombre écrit, au plus `reste`."""
    f = brut / f"{source.split('-')[0]}-{cid}.jsonl"
    deja = set()
    if f.exists():
        for l in f.read_text(encoding="utf-8").splitlines():
            try:
                deja.add(cle(json.loads(l)))
            except ValueError:
                continue
    neuves = []
    for l in lignes:
        k = cle(l)
        if l["texte"] and k not in deja and len(neuves) < reste:
            deja.add(k)
            neuves.append(l)
    if neuves:
        with f.open("a", encoding="utf-8", newline="\n") as fh:
            for l in neuves:
                fh.write(json.dumps(l, ensure_ascii=False) + "\n")
    return len(neuves)


async def collecter(perimetre: dict, brut: Path, echeance: float, journal: Callable[[str], None]) -> dict:
    """Collecte le périmètre (déjà validé) dans `brut/` ; ne lève pas sur une panne de source.
    Rend {"ajoutes": {source: n}, "limites": [str]}."""
    brut.mkdir(parents=True, exist_ok=True)
    ajoutes: dict[str, int] = {}
    limites: list[str] = []
    depuis = int(time.time()) - int(perimetre.get("depuis_jours") or DEPUIS_JOURS) * 86400
    youtube_ok = True

    def garde():
        if _horloge() >= echeance:
            raise _Plafond(f"durée maximale atteinte ({int(DUREE_MAX)} s) : collecte arrêtée")
        if sum(ajoutes.values()) >= MAX_BRUT:
            raise _Plafond(f"plafond de {MAX_BRUT} textes atteint : collecte arrêtée")

    def noter(source: str, cid: str, lignes: list[dict]):
        n = _ecrire(brut, source, cid, lignes, MAX_BRUT - sum(ajoutes.values()))
        cle_source = source.split("-")[0]
        ajoutes[cle_source] = ajoutes.get(cle_source, 0) + n
        journal(f"{source} {cid} : +{n}")

    try:
        for c in perimetre.get("concurrents") or []:
            cid = c["id"]
            for q in c.get("hn") or []:
                garde()
                noter("hn", cid, await _hn(cid, q, depuis, echeance, limites))
            for v in c.get("youtube") or []:
                garde()
                if not youtube_ok:
                    break
                try:
                    noter("youtube", cid, await _youtube(cid, v))
                except _Absent:
                    youtube_ok = False
                    limites.append("youtube : yt-dlp introuvable, source indisponible")
                except Exception as e:  # noqa: BLE001 — vidéo privée, supprimée, délai…
                    limites.append(f"youtube {v} : {type(e).__name__} : {str(e)[:120]}")
            for app_id in c.get("appstore") or []:
                for pays in c.get("pays") or ["us"]:
                    garde()
                    noter(f"appstore-{pays}", cid, await _appstore(cid, app_id, pays, echeance, limites))
        if sum(ajoutes.values()) >= MAX_BRUT:
            limites.append(f"plafond de {MAX_BRUT} textes atteint : collecte arrêtée")
        elif _horloge() >= echeance:      # l'échéance tombée pendant la dernière cible : la dire aussi
            limites.append(f"durée maximale atteinte ({int(DUREE_MAX)} s) : collecte arrêtée")
    except _Plafond as e:
        limites.append(str(e))
    return {"ajoutes": ajoutes, "limites": limites}
