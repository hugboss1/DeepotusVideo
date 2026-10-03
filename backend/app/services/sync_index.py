# -*- coding: utf-8 -*-
"""Plan mobile T12 + T13 (tâche #58, 01/10/2026) — la Bibliothèque vue du téléphone : le MANIFESTE (ce qui existe,
avec taille, empreinte et provenance ; les projets épinglés qui descendent EN ENTIER) et le DÉPÔT vérifié (une image
venue du téléphone entre au magasin seulement si son empreinte est la bonne, et rien ne reste en cas d'échec).

DÉCISIONS DE L'UTILISATEUR (01/10) : les écritures du téléphone sont ouvertes au réseau local UNE PAR UNE — le dépôt
seul ici (`main._ECRITURES_OUVERTES`) ; l'appareil est toujours celui du JETON. Épingler un projet se décide sur le PC.

Écarts au plan du 03/09, et pourquoi :
  - le téléchargement repris passe par GET /api/images/{nom} (FileResponse sert les plages) : pas de route doublon ;
  - le manifeste porte `noms` (TOUT ce qui existe) : le mode incrémental, fondé sur le mtime, ne voit ni une
    suppression ni un fichier importé avec un vieux mtime — la liste des noms, si ;
  - la recette d'une image du téléphone va dans `outputs/_sync/recettes/<nom>.json`, PAS à côté de l'image : le
    dossier des images est la Bibliothèque de l'utilisateur.
"""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.services import library_index as LI
from app.services.sync_lot import _iso, _sha256

PROTOCOLE = 1
EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
TAILLE_MAX = 50 * 1024 * 1024        # une image de téléphone ; au-delà, 413 sans rien lire de plus
RECETTE_MAX = 16 * 1024


class DepotRefuse(Exception):
    """Un dépôt refusé : `code` HTTP et la raison, dite telle quelle au téléphone."""

    def __init__(self, code: int, raison: str):
        super().__init__(raison)
        self.code = code
        self.raison = raison


# ── projets épinglés ─────────────────────────────────────────────────────────────────────────────────────────────────

def _fichier_projets() -> Path:
    return settings.outputs_path / "_sync" / "projets.json"


def _lire_projets() -> dict:
    p = _fichier_projets()
    if not p.is_file():
        return {}
    try:
        tout = json.loads(p.read_text(encoding="utf-8"))
        return tout if isinstance(tout, dict) else {}
    except (ValueError, OSError):
        return {}


async def epingler(nom: str, fichiers: list) -> dict:
    """Un projet épinglé descend EN ENTIER sur le téléphone. Un JSON, pas une table : l'entité « projet » appartient
    à un autre chantier (R9 P2), ce fichier en est le pense-bête. Les noms sont NUS (aucun chemin ne sort)."""
    tout = _lire_projets()
    tout[nom] = sorted({Path(str(f)).name for f in (fichiers or []) if Path(str(f)).name})
    p = _fichier_projets()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".part")
    tmp.write_text(json.dumps(tout, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, p)
    return {"nom": nom, "fichiers": tout[nom]}


# ── le manifeste ─────────────────────────────────────────────────────────────────────────────────────────────────────

def _seuil(depuis: str | None) -> float:
    """`depuis` est l'ISO UTC d'un manifeste précédent. Une date NAÏVE lue par `fromisoformat` serait prise pour de
    l'heure LOCALE par `.timestamp()` : on la déclare UTC. Illisible -> 0 (l'index complet, pas une erreur)."""
    if not depuis:
        return 0.0
    try:
        return datetime.fromisoformat(str(depuis).replace("Z", "")).replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        return 0.0


def _images() -> list[Path]:
    dossier = settings.images_path
    if not dossier.is_dir():
        return []
    return sorted(f for f in dossier.iterdir()
                  if f.is_file() and f.suffix.lower() in EXTENSIONS and not f.name.startswith("."))


async def manifeste(depuis: str | None = None) -> dict:
    """L'index complet (ou ce qui a bougé depuis `depuis`), les noms de TOUT ce qui existe, les projets épinglés."""
    seuil = _seuil(depuis)
    prov = await LI.carte()
    tout = _images()
    index, poids = [], 0
    for f in tout:
        st = f.stat()
        if st.st_mtime <= seuil:
            continue
        connu = prov.get(f.name) or {}  # un dict par fichier depuis la tâche #77 (03/10/2026)
        index.append({"nom": f.name, "taille": st.st_size, "mtime": round(st.st_mtime, 3), "sha256": _sha256(f),
                      "source": connu.get("source") or LI.heuristique(f.name),
                      "origine": connu.get("origin") or "heuristique",
                      "url": f"/api/images/{f.name}"})
        poids += st.st_size
    projets = [{"nom": k, "fichiers": v, "entier": True} for k, v in sorted(_lire_projets().items())]
    return {"protocole": PROTOCOLE, "index": index, "noms": [f.name for f in tout], "projets": projets,
            "poids_index": poids, "genere_a": _iso(datetime.utcnow())}


# ── le dépôt ─────────────────────────────────────────────────────────────────────────────────────────────────────────

def nom_depot(nom: str) -> str:
    """Le nom NU (aucun chemin), d'une extension d'image ; sinon 400."""
    sur = Path(str(nom or "")).name
    if not sur or sur.startswith(".") or Path(sur).suffix.lower() not in EXTENSIONS:
        raise DepotRefuse(400, f"Nom refusé : {sur or '(vide)'} — attendu une image .png, .jpg, .jpeg ou .webp")
    return sur


def lire_recette(brut: str | None) -> dict:
    if brut in (None, ""):
        return {}
    if len(brut) > RECETTE_MAX:
        raise DepotRefuse(400, "Recette trop longue")
    try:
        r = json.loads(brut)
    except ValueError:
        raise DepotRefuse(400, "Recette illisible (JSON attendu)") from None
    if not isinstance(r, dict):
        raise DepotRefuse(400, "Recette illisible (objet JSON attendu)")
    return r


async def deposer(nom: str, contenu: bytes, empreinte: str, recette: dict, appareil: dict) -> dict:
    """Écrit l'image si son sha256 est celui annoncé. Le MÊME contenu redéposé (reprise après une coupure) ne crée
    pas de doublon ; un AUTRE contenu sous le même nom devient `nom-1.ext`. Écriture `.part` puis renommage : un
    échec ne laisse rien. Le contenu a déjà été décodé par Pillow (route), et sa taille bornée."""
    if len(contenu) > TAILLE_MAX:
        raise DepotRefuse(413, f"Image trop lourde ({len(contenu)} o, maximum {TAILLE_MAX} o)")
    vrai = hashlib.sha256(contenu).hexdigest()
    if vrai != str(empreinte or "").strip().lower():
        raise DepotRefuse(422, "Empreinte sha256 différente de celle annoncée : le transfert a abîmé le fichier, rien n'est gardé")
    dossier = settings.images_path
    dossier.mkdir(parents=True, exist_ok=True)
    dest = dossier / nom
    stem, ext, n = dest.stem, dest.suffix, 1
    while dest.exists():
        if _sha256(dest) == vrai:
            return {"filename": dest.name, "sha256": vrai, "taille": len(contenu), "deja": True}
        dest = dossier / f"{stem}-{n}{ext}"
        n += 1
    part = dest.with_name(dest.name + ".part")
    try:
        part.write_bytes(contenu)
        os.replace(part, dest)
    finally:
        if part.exists():
            part.unlink()
    await LI.noter([dest.name], "mobile")
    rec = dict(recette)
    rec.update({"appareil": {"id": appareil["id"], "nom": appareil["nom"]}, "sha256": vrai,
                "depose_le": _iso(datetime.utcnow())})
    rdir = settings.outputs_path / "_sync" / "recettes"
    rdir.mkdir(parents=True, exist_ok=True)
    (rdir / f"{dest.name}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"filename": dest.name, "sha256": vrai, "taille": len(contenu), "deja": False}
