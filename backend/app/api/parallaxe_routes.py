# -*- coding: utf-8 -*-
"""t341 (29/10/2026, lot Scenario B5) — /api/parallaxe : décor en calques de parallaxe du Tile Lab.

Boucle locale SEULEMENT (`routes._require_localhost`) ; la route qui peut dépenser a aussi `_require_local_depense`.
- `GET  /modeles?w=&h=&n=`   les voies (locale gratuite, deux modèles fal) et LEUR DEVIS pour cette image ; gratuit.
- `POST /decouper`           {image, n, modele, boucler, nom, confirme_cout} → la méta du décor. Ordre des refus, tous
                             AVANT la dépense : image (400/404) → n, modèle (400) → clé fal (503) → `confirme_cout`
                             absent (409, avec le devis) → bornes du modèle (400) → plafonds (402, catégorie « tuiles »).
                             Les calques entrent dans la Bibliothèque (source « tuiles », parent = la peinture).
- `GET  ""`, `GET /{pid}`    la liste des décors, une méta.
- `PUT  /{pid}`              ordre, noms, facteurs, « devant le jeu », visibilité, répétition (parallaxe.modifier).
- `GET  /{pid}/calque/{cid}` le PNG d'un calque ; `GET /{pid}/source` la peinture.
- `GET  /{pid}/export?format=godot|png`  le ZIP (Godot ParallaxBackground .tscn + PNG, ou les PNG seuls).
"""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, Response
from loguru import logger
from PIL import Image, UnidentifiedImageError

from app.config import settings
from app.services import parallaxe as PX

router = APIRouter()
CATEGORIE = "tuiles"


def _local(request: Request) -> None:
    from app.api.routes import _require_localhost
    _require_localhost(request)


def _depense_locale(request: Request) -> None:
    from app.api.routes import _require_local_depense
    _require_local_depense(request)


def _source(nom) -> tuple[str, Path]:
    """Une image de la Bibliothèque, désignée par son NOM (un chemin est refusé)."""
    brut = str(nom or "").strip()
    if not brut or Path(brut).name != brut:
        raise HTTPException(400, "image : le nom d'une image de la Bibliothèque est attendu")
    p = settings.images_path / brut
    if not p.is_file():
        raise HTTPException(404, f"image introuvable dans la Bibliothèque : {brut}")
    return brut, p


def _taille(p: Path) -> tuple[int, int]:
    try:
        with Image.open(p) as im:
            return im.size
    except (UnidentifiedImageError, OSError):
        raise HTTPException(400, "image illisible : PNG, JPEG ou WebP attendu")


def _cle_fal() -> bool:
    return bool((settings.FAL_KEY or "").strip())


@router.get("/modeles", dependencies=[Depends(_local)])
async def modeles(w: int = 3072, h: int = 1024, n: int = 5):
    try:
        n = PX.lire_n(n)
    except ValueError as e:
        raise HTTPException(400, str(e))
    out = []
    for mid, m in PX.MODELES.items():
        try:
            PX.verifier_taille(mid, int(w), int(h))
            borne = None
        except ValueError as e:
            borne = str(e)
        out.append({"id": mid, "voie": m["voie"], "libelle": m["libelle"], "endpoint": m["endpoint"],
                    "devis": PX.devis(mid, n, int(w), int(h)), "cle": "FAL_KEY" if m["voie"] == "fal" else None,
                    "cle_ok": m["voie"] == "local" or _cle_fal(), "borne": borne})
    return {"modeles": out, "noms": PX.noms_pour(n), "facteurs": PX.facteurs_pour(n)}


@router.post("/decouper", dependencies=[Depends(_local), Depends(_depense_locale)])
async def decouper(body: dict):
    body = body if isinstance(body, dict) else {}
    nom, chemin = _source(body.get("image"))
    try:
        n = PX.lire_n(body.get("n", 5))
    except ValueError as e:
        raise HTTPException(400, str(e))
    modele = str(body.get("modele") or "local")
    if modele not in PX.MODELES:
        raise HTTPException(400, f"modèle inconnu : {modele[:40]}")
    w, h = _taille(chemin)
    devis = PX.devis(modele, n, w, h)
    if PX.MODELES[modele]["voie"] == "fal":
        if not _cle_fal():
            raise HTTPException(503, "Clé fal absente — ajoute-la dans les Réglages : la décomposition IA passe par fal.")
        if body.get("confirme_cout") is not True:
            raise HTTPException(409, {"message": "Décomposition IA payante : confirme le coût avant de lancer.",
                                      "devis": devis})
    try:
        PX.verifier_taille(modele, w, h)
    except ValueError as e:
        raise HTTPException(400, str(e))
    with Image.open(chemin) as im:
        src = im.convert("RGB")
    if PX.MODELES[modele]["voie"] == "fal":
        from app.api import routes as R
        await R._plafond({"kind": "parallaxe_calques", "modele": modele, "n": n, "w": w, "h": h}, CATEGORIE)
        try:
            calques = await PX.decomposer_par_ia(chemin, modele, n)
        except ValueError as e:
            raise HTTPException(400, str(e))
        except RuntimeError as e:
            raise HTTPException(502, str(e))
    else:
        calques = await asyncio.to_thread(PX.decouper_local, src, n)
    pid = PX.nouveau_pid()
    meta = await asyncio.to_thread(PX.enregistrer, pid, nom, src, calques, modele=modele,
                                   devis_usd=devis["usd"], boucler=bool(body.get("boucler")),
                                   nom=str(body.get("nom") or ""))
    await _bibliotheque(meta)
    logger.info(f"parallaxe/decouper {modele} n={n} {w}x{h} -> {pid} ({len(meta['calques'])} calques)")
    return meta


async def _bibliotheque(meta: dict) -> None:
    """LA PROVENANCE : chaque calque est COPIÉ dans la Bibliothèque (`tile_plx_…` → source « tuiles »), rattaché à la
    peinture (parent, relation « parallaxe ») avec sa recette. Une panne d'index n'empêche jamais le décor."""
    from app.services import library_index as LI
    d = PX.dossier(meta["pid"])
    for k, c in enumerate(meta["calques"], start=1):
        copie = settings.images_path / f"tile_{meta['pid']}_{k}_{c['id']}.png"
        try:
            shutil.copyfile(d / "calques" / c["fichier"], copie)
            await LI.noter([copie.name], "tuiles", parent=meta["source"], relation="parallaxe",
                           recette={"outil": "parallaxe", "decor": meta["pid"], "modele": meta["modele"],
                                    "calque": c["id"], "ordre": k, "facteur": c["facteur"]})
        except Exception as e:  # noqa: BLE001
            logger.warning(f"parallaxe : copie / index du calque {c['id']} ignorés ({e})")


@router.get("", dependencies=[Depends(_local)])
async def lister():
    return {"decors": PX.lister()}


def _meta(pid: str) -> dict:
    try:
        return PX.lire_meta(pid)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@router.get("/{pid}", dependencies=[Depends(_local)])
async def lire(pid: str):
    return _meta(pid)


@router.put("/{pid}", dependencies=[Depends(_local)])
async def modifier(pid: str, body: dict):
    _meta(pid)
    try:
        return PX.modifier(pid, body if isinstance(body, dict) else {})
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/{pid}/calque/{cid}", dependencies=[Depends(_local)])
async def calque(pid: str, cid: str):
    _meta(pid)
    try:
        p = PX.chemin_calque(pid, cid)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    return FileResponse(p, media_type="image/png", headers={"Cache-Control": "no-store"})


@router.get("/{pid}/source", dependencies=[Depends(_local)])
async def source(pid: str):
    _meta(pid)
    return FileResponse(PX.dossier(pid) / "source.png", media_type="image/png")


@router.get("/{pid}/export", dependencies=[Depends(_local)])
async def exporter(pid: str, format: str = "godot"):
    _meta(pid)
    try:
        nom, octets = await asyncio.to_thread(PX.archive, pid, format)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return Response(content=octets, media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{nom}"'})
