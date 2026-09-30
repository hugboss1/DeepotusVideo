# -*- coding: utf-8 -*-
"""La memoire des sujets deja couverts (plan 2026-09-03 T7, tache #34 du suivi, 30/09/2026).

Chaque reel News lance laisse une trace : les jetons de ses articles, leur source, la date. Deux usages :
  - `marquer()` : un article proche d'un sujet deja couvert porte `deja_couvert` = le titre du sujet en question
    (l'ecran l'affiche en ambre, il ne le cache pas — c'est a l'utilisateur de trancher) ;
  - `penalites_de_source()` : une source sur-representee sur la fenetre recente rend un malus, que
    `news_rank.classer` retranche du score.

Ecart date (30/09) : le plan attendait la chaine du lot 2 (T13) pour noter ; d'ici la, `/news/illustration` note les
articles d'un reel lance avec succes. Le fichier vit sous `news/couverture.json`, a cote de `sources.json` et
`cache.json` : pas de table, pas de migration.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from loguru import logger

from app.config import settings
from app.services.news_filter import jetons, titres_presque_identiques

FENETRE_JOURS = 30       # au-dela, un sujet cesse d'etre « deja couvert »
SUJETS_MAX = 400         # borne dure du fichier
MALUS_MAX = 25           # points retranches au plus, sur 100
JETONS_PAR_SUJET = 24


def chemin_couverture() -> Path:
    d = settings.outputs_path.parent / "news"
    d.mkdir(parents=True, exist_ok=True)
    return d / "couverture.json"


def _lire() -> dict:
    p = chemin_couverture()
    if not p.is_file():
        return {"sujets": []}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        logger.warning("news couverture.json illisible - memoire vide")
        return {"sujets": []}
    if not isinstance(d, dict) or not isinstance(d.get("sujets"), list):
        return {"sujets": []}
    d["sujets"] = [s for s in d["sujets"] if isinstance(s, dict)]
    return d


def _ecrire(doc: dict) -> None:
    p = chemin_couverture()
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(p)


def sujets_couverts() -> list[dict]:
    return _lire()["sujets"]


def _quand(v: str | None) -> datetime:
    if v:
        try:
            d = datetime.fromisoformat(str(v))
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def noter_couverture(items: list[dict], *, post_id: str = "", quand: str | None = None) -> int:
    """Enregistre les sujets d'un reel lance. Rend le nombre de sujets notes."""
    doc = _lire()
    horodatage = _quand(quand).isoformat(timespec="seconds")
    ajoutes = 0
    for it in items:
        titre = str(it.get("title") or "").strip()
        if not titre:
            continue
        doc["sujets"].append({
            "titre": titre[:200],
            "jetons": jetons(titre)[:JETONS_PAR_SUJET],
            "source_id": str(it.get("source_id") or ""),
            "source_name": str(it.get("source_name") or ""),
            "post_id": str(post_id or ""),
            "quand": horodatage,
        })
        ajoutes += 1
    if not ajoutes:
        return 0
    # borne dure : le plus ancien part en premier
    doc["sujets"].sort(key=lambda s: _quand(s.get("quand")))
    doc["sujets"] = doc["sujets"][-SUJETS_MAX:]
    _ecrire(doc)
    return ajoutes


def _recents(maintenant: str | None, jours: int) -> list[dict]:
    ref = _quand(maintenant)
    limite = ref - timedelta(days=jours)
    return [s for s in sujets_couverts() if limite <= _quand(s.get("quand")) <= ref + timedelta(minutes=5)]


def marquer(items: list[dict], *, maintenant: str | None = None) -> list[dict]:
    """Rend une COPIE des articles, chacun portant `deja_couvert` : le titre du sujet deja traite dont il est proche,
    ou None. Le « proche » est CELUI du dedoublonnage (T2) : la meme fonction, pas une copie de ses seuils."""
    couverts = _recents(maintenant, FENETRE_JOURS)
    sortie: list[dict] = []
    for it in items:
        copie = dict(it)
        titre = str(it.get("title") or "")
        trouve = None
        for s in couverts:
            ancien = str(s.get("titre") or "")
            if titres_presque_identiques(titre, ancien):
                trouve = ancien
                break
        copie["deja_couvert"] = trouve
        sortie.append(copie)
    return sortie


def penalites_de_source(*, maintenant: str | None = None, jours: int = 14) -> dict:
    """{source_id: malus 0..MALUS_MAX} sur la fenetre recente. Le malus est proportionnel a l'ecart entre la part de
    la source et une part equitable : a sa part equitable, une source ne perd rien."""
    compte: dict = {}
    for s in _recents(maintenant, jours):
        sid = str(s.get("source_id") or "")
        if sid:
            compte[sid] = compte.get(sid, 0) + 1
    if len(compte) < 2:
        return {}
    total = sum(compte.values())
    equitable = 1.0 / len(compte)
    malus: dict = {}
    for sid, n in compte.items():
        exces = max(0.0, n / total - equitable)
        malus[sid] = int(round(MALUS_MAX * min(1.0, exces / (1 - equitable))))
    return malus
