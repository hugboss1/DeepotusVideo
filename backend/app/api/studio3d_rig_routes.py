# -*- coding: utf-8 -*-
"""Routes de l'écran RIG du 3D Studio — t395 (31/10/2026). Préfixe /api/studio3d/rig.

Le rig SEMI-AUTOMATIQUE, local et gratuit (service `app.services.rig_local`) :
  - GET  /proposition/{job}?version=N : le gabarit SMPL de 22 os calé sur la boîte du modèle, et les articulations de
    départ (celles d'un squelette déjà posé par ce service, sinon le gabarit) ; lecture seule ;
  - POST /appliquer/{job} {version?, joints: {os: [x, y, z]}, poitrine?: bool} : squelette + poids → une VERSION de plus.
L'auto-rig IA (Meshy, payant) garde SA route, déjà gardée : GET/POST /api/assets/3d/{job}/rig[/devis] — l'écran
l'appelle tel quel, après devis et confirmation. Aucune dépense ici.
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter()

_NOM_JOB = re.compile(r"^[\w.-]{1,160}$")


def _version(job: str, version) -> tuple[str, int, str, bytes]:
    """(job aplati, version, fichier, octets) de la version demandée, ou de la dernière ; 404 si absente."""
    from app.services import studio3d_ouvert as SO
    if not isinstance(job, str) or not _NOM_JOB.match(job) or job in (".", ".."):
        raise HTTPException(400, f"job « {str(job)[:40]} » : nom de dossier invalide")
    if version is not None and (isinstance(version, bool) or not isinstance(version, int) or version < 1):
        raise HTTPException(400, "version : un entier à partir de 1")
    try:
        f = SO.fiche(job, version)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    v = int(f["version"])
    nom = "model.glb" if v <= 1 else f"model.v{v}.glb"
    p = SO._job_dir(f["job"]) / nom
    if not p.is_file():
        raise HTTPException(404, f"{f['job']}/{nom} introuvable")
    return f["job"], v, nom, p.read_bytes()


@router.get("/proposition/{job}")
async def rig_proposition(job: str, version: int | None = None):
    """Le gabarit et les articulations de départ pour la version ouverte (la dernière par défaut)."""
    from app.services import rig_local as RL
    j, v, nom, data = await asyncio.to_thread(_version, job, version)
    try:
        p = await asyncio.to_thread(RL.proposition, data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"job": j, "version": v, "fichier": nom, **p}


@router.post("/appliquer/{job}")
async def rig_appliquer(job: str, body: dict | None = None):
    """Squelette + poids recalculés → `model.v{n+1}.glb`. Local et gratuit. 400 articulations invalides ou GLB hors
    périmètre (compressé, trop de sommets), 404 job ou version absents."""
    from app.services import rig_local as RL
    body = body if isinstance(body, dict) else {}
    poitrine = body.get("poitrine", False)
    if not isinstance(poitrine, bool):
        raise HTTPException(400, "poitrine : vrai ou faux")
    if not isinstance(body.get("joints"), dict):
        raise HTTPException(400, "joints : un objet {os: [x, y, z]} est attendu")
    j, v, nom, data = await asyncio.to_thread(_version, job, body.get("version"))
    try:
        fiche = await asyncio.to_thread(RL.appliquer, j, v, data, body["joints"], avec_poitrine=poitrine,
                                        fichier=nom)
    except ValueError as e:
        raise HTTPException(400, str(e))
    src = fiche.get("source") or {}
    return {"ok": True, "job": j, "depuis": v, "version": fiche.get("version"), "fichier": fiche.get("file"),
            "os": src.get("os"), "sommets": src.get("sommets"), "methode": src.get("methode"),
            "retire": src.get("retire"), "url": f"/api/assets/3d/{Path(j).name}/version/{fiche.get('version')}"}
