# -*- coding: utf-8 -*-
"""t434 (lot M1 « Méthodes », 08/11/2026) — B2 : les ANCRES D'IDENTITÉ (conception
docs/superpowers/specs/2026-11-08-scenario-explorations-agents-design.md §4).

Une ancre = une image APPROUVÉE (fiche personnage, packshot, master produit, image de style) dont dérivent toutes les
vues d'un travail. Elle n'est liée à aucune entité de la Bible : un agent métier la pose, la relit, la transmet en
référence à chaque génération (`references`) et vérifie après coup qu'une sortie ne s'en est pas éloignée
(`verifier`, par identity_drift : écart de couleur ΔE76 et de silhouette).

Stockage : <données>/briques/ancres.json (liste) + une COPIE de l'image dans <données>/briques/ancres/ (l'ancre ne
bouge pas si l'original est déplacé ou supprimé). Local et gratuit.
"""
from __future__ import annotations

import json
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.services import briques as BR

NATURES = ("personnage", "produit", "decor", "style", "autre")
MAX_ANCRES = 500
MAX_NOM = 80
MAX_NOTE = 400
_VERROU = threading.Lock()


def _dossier() -> Path:
    return BR.racine() / "briques"


def _fichier() -> Path:
    return _dossier() / "ancres.json"


def _lire() -> list[dict]:
    try:
        d = json.loads(_fichier().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [a for a in d if isinstance(a, dict) and a.get("id")] if isinstance(d, list) else []


def _ecrire(ancres: list[dict]) -> None:
    f = _fichier()
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(ancres, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(f)


def _txt(v, n) -> str:
    return " ".join(str(v or "").split())[:n] if isinstance(v, str) else ""


def lister(espace_id: str = "", nature: str = "") -> list[dict]:
    """Les ancres (les plus récentes d'abord), filtrées par espace et par nature."""
    out = [a for a in _lire() if (not espace_id or a.get("espace_id") == espace_id)
           and (not nature or a.get("nature") == nature)]
    return sorted(out, key=lambda a: a.get("cree", ""), reverse=True)


def lire(ancre_id: str) -> dict | None:
    return next((a for a in _lire() if a.get("id") == ancre_id), None)


def creer(nom: str, nature: str, chemin: str, espace_id: str = "", note: str = "") -> dict:
    """Pose une ancre depuis une IMAGE du dossier de données (copiée). ValueError : nom vide, nature inconnue,
    fichier refusé ou pas une image, trop d'ancres."""
    nom = _txt(nom, MAX_NOM)
    if not nom:
        raise ValueError("Donne un nom à l'ancre.")
    if nature not in NATURES:
        raise ValueError("Nature d'ancre inconnue.")
    p = BR.confiner(chemin)
    if BR.nature(p) != "image":
        raise ValueError("Une ancre est une image.")
    with _VERROU:
        ancres = _lire()
        if len(ancres) >= MAX_ANCRES:
            raise ValueError("Trop d'ancres : supprimes-en avant d'en poser une nouvelle.")
        aid = "anc_" + uuid4().hex[:12]
        dest = _dossier() / "ancres" / f"{aid}{p.suffix.lower()}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dest)
        a = {"id": aid, "nom": nom, "nature": nature, "fichier": str(dest.relative_to(BR.racine())).replace("\\", "/"),
             "origine": str(p.relative_to(BR.racine())).replace("\\", "/"), "espace_id": _txt(espace_id, 40),
             "note": _txt(note, MAX_NOTE), "cree": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        ancres.append(a)
        _ecrire(ancres)
    return a


def supprimer(ancre_id: str) -> bool:
    """Retire l'ancre et sa copie ; False si elle n'existe pas."""
    with _VERROU:
        ancres = _lire()
        a = next((x for x in ancres if x.get("id") == ancre_id), None)
        if a is None:
            return False
        _ecrire([x for x in ancres if x.get("id") != ancre_id])
    try:
        (BR.racine() / a["fichier"]).unlink(missing_ok=True)
    except OSError:
        pass
    return True


def references(ids: list[str]) -> list[Path]:
    """Les images (chemins absolus) des ancres demandées, dans l'ordre, pour les passer en référence d'une
    génération (image_urls / reference_image_urls / entités vidéo). ValueError sur une ancre inconnue ou absente."""
    out = []
    for i in ids or []:
        a = lire(i)
        if a is None:
            raise ValueError(f"Ancre inconnue : {i}")
        out.append(BR.confiner(a["fichier"]))
    return out


def verifier(ancre_id: str, chemin: str) -> dict:
    """La sortie `chemin` (image, ou l'image du milieu d'une vidéo) contre l'ancre : identity_drift (verdict
    « stable » ou « derive », seuils, ce que la mesure ne voit pas)."""
    from app.services import identity_drift as ID
    a = lire(ancre_id)
    if a is None:
        raise ValueError(f"Ancre inconnue : {ancre_id}")
    ref = BR.confiner(a["fichier"])
    p = BR.confiner(chemin)
    n = BR.nature(p)
    if n not in ("image", "video"):
        raise ValueError("On vérifie une image ou une vidéo contre une ancre.")
    img = BR._premiere_image(p) if n == "video" else p
    return {"ancre": {"id": a["id"], "nom": a["nom"], "nature": a["nature"]}, **ID.derive(ref, img)}
