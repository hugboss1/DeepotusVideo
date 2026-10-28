# -*- coding: utf-8 -*-
"""t368 (28/10/2026) — A3 « ce que font les concurrents » (plan docs/superpowers/plans/2026-10-28-veille-apify-t365-t369.md,
décision 5), rangé sous `veille/<eid>/concurrents/` :
  pages  : les pages prix / fonctions du périmètre relues par NOTRE lecteur (gratuit, robots.txt respecté, cadence du
           lecteur t354) ; le texte gardé, le DIFF avec la lecture précédente rendu (pages.json = la dernière relecture) ;
  pubs   : les pubs actives d'une page Facebook (collecte Apify acceptée) résumées {texte ≤ 300, debut, plateformes,
           lien, actif} (pubs-<concurrent>.json) ;
  serp   : les positions des domaines des concurrents sur nos mots-clés (collecte Apify acceptée) (serp.json).
Lecture seule sur le web ; aucun envoi. Coutures de banc : _LIRE, _ROBOTS.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit

MAX_DIFF_LIGNES = 60
MAX_DIFF = 4000
MAX_PUBS = 50
MAX_RANGS = 10
TEXTE = 300


async def _lire_defaut(url: str) -> str:
    from app.services import agent_outils as AO
    u = urlsplit(url)
    await AO._cadence(u.netloc)
    return await AO._telecharger(url)


async def _robots_defaut(url: str) -> bool:
    from app.services import agent_outils as AO
    return await AO._robots_permet(url)


_LIRE, _ROBOTS = _lire_defaut, _robots_defaut


def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _dossier(eid: str):
    from app.services import veille as V
    return V._racine(eid) / "concurrents"


def _ecrire(f, doc) -> None:
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(f.suffix + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    tmp.replace(f)


def _lire_json(f, defaut):
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return defaut


def _propre(texte: str) -> str:
    lignes = (re.sub(r"[ \t]+", " ", l).strip() for l in str(texte or "").splitlines())
    return "\n".join(l for l in lignes if l)


async def relire_pages(eid: str) -> dict:
    """Relit chaque page du périmètre ; {lues, changees, interdites, changements: [{concurrent, url, change, diff}]}."""
    from app.services import agent_outils as AO, veille as V
    perim = V.perimetre(eid)
    racine = _dossier(eid)
    out, lues, interdites = [], 0, 0
    for c in perim["concurrents"]:
        for url in c.get("pages") or []:
            try:
                AO._url_sure(url)
            except Exception:  # noqa: BLE001 — hôte local ou interdit : jamais lu
                continue
            if not await _ROBOTS(url):
                interdites += 1
                out.append({"concurrent": c["id"], "url": url, "change": False, "diff": "", "refus": "robots"})
                continue
            try:
                texte = _propre(await _LIRE(url))
            except Exception as e:  # noqa: BLE001 — page absente : dite, on passe à la suivante
                out.append({"concurrent": c["id"], "url": url, "change": False, "diff": "",
                            "refus": f"illisible ({type(e).__name__})"})
                continue
            lues += 1
            f = racine / "pages" / c["id"] / (hashlib.sha1(url.encode("utf-8")).hexdigest()[:12] + ".txt")
            avant = f.read_text(encoding="utf-8") if f.exists() else None
            diff = ""
            if avant is not None and avant != texte:
                d = list(difflib.unified_diff(avant.splitlines(), texte.splitlines(), "avant", "maintenant", lineterm="", n=1))
                diff = "\n".join(d[:MAX_DIFF_LIGNES])[:MAX_DIFF]
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(texte, encoding="utf-8")
            out.append({"concurrent": c["id"], "url": url, "change": bool(diff), "diff": diff})
    _ecrire(racine / "pages.json", {"le": _maintenant(), "pages": out})
    return {"lues": lues, "changees": sum(1 for x in out if x["change"]), "interdites": interdites, "changements": out}


def _champ(it: dict, chemins):
    from app.services import apify_suite as SU
    return SU._champ(it, chemins)


def _http(u) -> str:
    u = str(u or "")
    return u[:500] if re.match(r"^https?://", u, re.I) else ""


def noter_pubs(eid: str, concurrent: str, items: list) -> int:
    from app.services import apify_suite as SU
    pubs = []
    for it in (items if isinstance(items, list) else [])[:MAX_PUBS]:
        if not isinstance(it, dict):
            continue
        texte = _champ(it, ["snapshot.body.text", "adCreativeBody", "snapshot.title", "title"])
        plat = _champ(it, ["publisherPlatform", "publisherPlatforms"])
        pubs.append({"texte": str(texte or "").strip()[:TEXTE],
                     "debut": SU._date(_champ(it, ["startDateFormatted", "startDate", "start_date"])),
                     "plateformes": [str(p)[:30] for p in plat][:6] if isinstance(plat, list) else [],
                     "lien": _http(_champ(it, ["url", "adLibraryURL", "adSnapshotUrl"])),
                     "actif": it.get("isActive") if isinstance(it.get("isActive"), bool) else None})
    _ecrire(_dossier(eid) / f"pubs-{concurrent}.json", {"le": _maintenant(), "pubs": pubs})
    return len(pubs)


def _domaine(url: str) -> str:
    h = (urlsplit(str(url or "")).hostname or "").lower()
    return h[4:] if h.startswith("www.") else h


def noter_serp(eid: str, items: list) -> int:
    from app.services import veille as V
    domaines = {c["domaine"]: c["id"] for c in V.perimetre(eid)["concurrents"] if c.get("domaine")}

    def qui(d: str):
        return next((cid for dom, cid in domaines.items() if d == dom or d.endswith("." + dom)), None)

    mots = {}
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict):
            continue
        terme = str(_champ(it, ["searchQuery.term", "query"]) or "").strip()[:120]
        if not terme:
            continue
        rangs = []
        for r in (it.get("organicResults") or [])[:MAX_RANGS]:
            if isinstance(r, dict) and isinstance(r.get("position"), int):
                d = _domaine(r.get("url"))
                rangs.append({"rang": r["position"], "domaine": d, "concurrent": qui(d)})
        mots[terme] = rangs
    _ecrire(_dossier(eid) / "serp.json", {"le": _maintenant(), "mots_cles": mots})
    return len(mots)


def lire(eid: str) -> dict:
    """{pubs: {concurrent: [..]}, pages: [..] (dernière relecture), pages_le, serp: {le, mots_cles}}."""
    d = _dossier(eid)
    pubs = {}
    for f in sorted(d.glob("pubs-*.json")) if d.exists() else []:
        pubs[f.stem[5:]] = (_lire_json(f, {}) or {}).get("pubs") or []
    pages = _lire_json(d / "pages.json", {}) or {}
    return {"pubs": pubs, "pages": pages.get("pages") or [], "pages_le": pages.get("le"),
            "serp": _lire_json(d / "serp.json", {}) or {}}
