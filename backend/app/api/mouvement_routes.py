# -*- coding: utf-8 -*-
"""t343 (29/10/2026, lot Scenario B8) — /api/etabli/mouvement : un MOUVEMENT sur le rig d'un modèle de l'Établi.

Boucle locale SEULEMENT (`routes._require_localhost`) ; la route qui dépense a aussi `_require_local_depense`.
- `GET  ""?job=&version=`        les sources du job (mouvements rangés, clips Meshy), les clips et les os de la
                                 version, l'état de la voie vidéo (clé, prix) ; gratuit.
- `GET  /videos`                 les vidéos finies de la Bibliothèque (téléphone compris : /videos/upload) ; gratuit.
- `POST /importer`               multipart {job, fichier .bvh|.glb} : lu, puis rangé dans `<job>/mouvements/`.
- `POST /appliquer`              {job, version, source, nom, retimage, aligner} → une version de plus avec le clip
                                 nommé (reciblé, retimé). Local et gratuit.
- `GET  /video/devis`            {job, clip_id | video_filename, debut, fin} → bornes et devis Uthana ; gratuit.
- `POST /video`                  la voie PAYANTE. Ordre des refus, tous AVANT la dépense : job (400/404) → vidéo
                                 (400/404) → clé Uthana (503) → bornes (400) → `confirme_cout` absent (409, avec le
                                 devis) → plafonds (402, « moteurs3d »). Le travail part en tâche de fond.
- `GET  /video/etat`             {job, tache} → l'état ; fini : le mouvement est rangé dans le job.
- `POST /godot`                  {job, version, hitboxes, nom} → ZIP Godot 4 (GLB + .tscn + script des attaches).
"""
from __future__ import annotations

import asyncio
import json
import re
import time
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from loguru import logger

from app.config import settings
from app.services import mouvement_rig as MR
from app.services import uthana as UT

router = APIRouter()
CATEGORIE = "moteurs3d"
_EXT_VIDEOS = (".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi")
_VIDEOS_MAX = 40
_TACHES: dict[str, asyncio.Task] = {}


def _local(request: Request) -> None:
    from app.api.routes import _require_localhost
    _require_localhost(request)


def _depense_locale(request: Request) -> None:
    from app.api.routes import _require_local_depense
    _require_local_depense(request)


def _job_nu(job) -> str:
    j = str(job or "")
    if not j or Path(j).name != j or j in (".", ".."):
        raise HTTPException(400, "job : le nom du dossier du job 3D est attendu")
    from app.services import mesh_report
    if not mesh_report.job_dir(j).is_dir():
        raise HTTPException(404, f"job 3D introuvable : {j}")
    return j


def _version(job, version, quoi):
    from app.api import routes as R
    return R._etabli_glb_cible(job, version, quoi)


@router.get("", dependencies=[Depends(_local)])
async def etat(job: str, version: int = 1):
    from app.services import mesh_edit
    j, data, depuis = _version(job, int(version), "mouvement")
    inv = mesh_edit.rig_inventory(data)
    return {"job": j, "depuis": depuis, "a_squelette": inv["a_squelette"],
            "os": [{"nom": o["nom"], "role": MR.role(o["nom"])} for o in inv["os"]], "clips": inv["clips"],
            "sources": await asyncio.to_thread(MR.sources, j),
            "video": {"cle": bool(UT.cle()), "modele": UT.MODELE, "usd_seconde": UT.devis(1)["usd_seconde"],
                      "duree_min": UT.DUREE_MIN, "duree_max": UT.DUREE_MAX},
            "retimage": {"vitesse": [MR.VITESSE_MIN, MR.VITESSE_MAX], "fps": [MR.FPS_MIN, MR.FPS_MAX],
                         "fondu_max": MR.FONDU_MAX}}


@router.get("/videos", dependencies=[Depends(_local)])
async def videos():
    """Les rendus vidéo finis de la Bibliothèque, les plus récents d'abord ; « telephone » pour un import (ugc)."""
    from sqlalchemy import select as _sel
    from app.services.storage import JobRecord, async_session_factory
    async with async_session_factory() as session:
        jobs = (await session.execute(_sel(JobRecord).where(JobRecord.status == "done")
                                      .where(JobRecord.final_video_path.is_not(None))
                                      .order_by(JobRecord.created_at.desc()).limit(_VIDEOS_MAX * 2))).scalars().all()
    out = []
    for j in jobs:
        p = Path(str(j.final_video_path or ""))
        if p.suffix.lower() not in _EXT_VIDEOS or not p.is_file():
            continue
        out.append({"job_id": j.id, "nom": p.name, "titre": (j.title or p.stem)[:120], "secondes": j.duration_s,
                    "origine": "telephone" if j.provider == "ugc" else "bibliotheque"})
        if len(out) >= _VIDEOS_MAX:
            break
    return {"videos": out}


@router.post("/importer", dependencies=[Depends(_local)])
async def importer(job: str = Form(...), fichier: UploadFile = File(...)):
    j = _job_nu(job)
    nom = Path(str(fichier.filename or "")).name
    if Path(nom).suffix.lower() == ".fbx":
        raise HTTPException(400, "FBX non lu ici (aucun lecteur FBX embarqué) : exporte-le en GLB ou en BVH depuis Blender")
    if Path(nom).suffix.lower() not in MR.EXTENSIONS:
        raise HTTPException(400, "mouvement : un fichier .bvh ou .glb est attendu")
    data = await fichier.read(MR.MAX_OCTETS + 1)
    if len(data) > MR.MAX_OCTETS:
        raise HTTPException(413, "mouvement trop lourd : 40 Mo au plus")
    try:
        fiche = await asyncio.to_thread(MR.ranger, j, nom, data, {"origine": "import"})
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "source": {"type": "fichier", "nom": fiche["fichier"]}, "fiche": fiche}


@router.post("/appliquer", dependencies=[Depends(_local)])
async def appliquer(body: dict):
    """LOCAL et gratuit : le mouvement reciblé et retimé devient le clip nommé d'une version de plus."""
    from app.api import routes as R
    body = body or {}
    j, data, depuis = _version(body.get("job"), body.get("version"), "mouvement")
    aligner = body.get("aligner", True) is not False

    def calculer():
        src = MR.charger_source(j, body.get("source"), data)
        return MR.appliquer(data, src, nom=body.get("nom"), retimage=body.get("retimage"), aligner=aligner)
    try:
        sortie, rapport = await asyncio.to_thread(calculer)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    src = body.get("source") or {}
    return R._etabli_ecrire(j, sortie, "mouvement", {
        "depuis": depuis, "source": {"type": src.get("type"), "nom": src.get("nom")}, **rapport})


async def _video_et_infos(body: dict, http=None):
    from app.api import routes as R
    from app.services import previs_plan as PV
    chemin = await R._sfx_video_source(body, "à capter", http)
    infos = await asyncio.to_thread(PV.infos_clip, chemin)
    return chemin, infos


def _bornes(body: dict, infos: dict) -> dict:
    debut, fin = body.get("debut", 0), body.get("fin")
    for v in (debut, fin):
        if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float))):
            raise HTTPException(400, "rognage : début et fin en secondes")
    try:
        return UT.verifier(infos, debut or 0, fin)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/cle", dependencies=[Depends(_local)])
async def poser_cle(body: dict):
    """Pose la clé Uthana là où vivent les clés (coffre ouvert, sinon .env), appliquée à chaud — comme les clés de
    recherche de la prospection (t354). Jamais renvoyée ni journalisée."""
    from app.services import coffre as CF
    v = str((body or {}).get("valeur") or "").strip()
    if not v or len(v) > 300 or any(ch.isspace() for ch in v):
        raise HTTPException(400, "clé illisible : une seule chaîne, sans espace")
    ou = CF.enregistrer_cle("UTHANA_API_KEY", v)
    return {"ok": True, "ou": ou, "cle": bool(UT.cle())}


@router.get("/video/devis", dependencies=[Depends(_local)])
async def video_devis(request: Request, job: str, clip_id: str = "", video_filename: str = "",
                      debut: float = 0.0, fin: float | None = None):
    _job_nu(job)
    _chemin, infos = await _video_et_infos({"clip_id": clip_id, "video_filename": video_filename}, request)
    out = {"infos": infos, "cle": bool(UT.cle()), "modele": UT.MODELE}
    try:
        b = UT.verifier(infos, debut, fin)
        out.update(bornes=b, devis=UT.devis(b["secondes"]), refus=None)
    except ValueError as e:
        out.update(bornes=None, devis=UT.devis(min(infos.get("secondes") or 0, UT.DUREE_MAX)), refus=str(e))
    return out


def _etat_chemin(job: str, tache: str) -> Path:
    return MR.dossier(job) / "_videos" / f"{tache}.json"


def _poser_etat(job: str, tache: str, **champs) -> dict:
    p = _etat_chemin(job, tache)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        e = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        e = {"tache": tache}
    e.update(champs, maj_le=time.strftime("%Y-%m-%dT%H:%M:%S"))
    p.write_text(json.dumps(e, ensure_ascii=False), encoding="utf-8")
    return e


async def _travail(job: str, tache: str, chemin: Path, bornes: dict, nom: str, devis: dict):
    """Tâche de fond : passage préparé (ffmpeg) → Uthana → GLB rangé dans les mouvements du job."""
    passage = MR.dossier(job) / "_videos" / f"{tache}.mp4"
    try:
        await asyncio.to_thread(UT.preparer, chemin, passage, bornes["debut"], bornes["fin"])

        async def suivre(e):
            _poser_etat(job, tache, **e)
        r = await UT.video_vers_mouvement(passage, nom, on_etat=suivre)
        fiche = await asyncio.to_thread(MR.ranger, job, f"{nom}.glb", r["glb"], {
            "origine": "uthana", "video": chemin.name, "rognage": [bornes["debut"], bornes["fin"]],
            "uthana_job": r["job"], "uthana_mouvement": r["mouvement"], "devis_usd": devis["usd"]})
        _poser_etat(job, tache, etat="fini", source={"type": "fichier", "nom": fiche["fichier"]}, fiche=fiche)
    except Exception as e:                              # noqa: BLE001 — l'état DIT l'échec, la tâche ne meurt pas muette
        logger.warning(f"mouvement vidéo {tache} : {type(e).__name__}")
        _poser_etat(job, tache, etat="echec", erreur=str(e)[:300])
    finally:
        passage.unlink(missing_ok=True)
        _TACHES.pop(tache, None)


@router.post("/video", dependencies=[Depends(_local), Depends(_depense_locale)])
async def video(request: Request, body: dict):
    """La voie PAYANTE (Uthana). Tous les refus arrivent AVANT la dépense ; la garde des plafonds juste avant."""
    from app.api import routes as R
    body = body or {}
    j = _job_nu(body.get("job"))
    chemin, infos = await _video_et_infos(body, request)
    if not UT.cle():
        raise HTTPException(503, "Clé Uthana absente — colle-la dans Établi › Rig › Mouvement, « Depuis une vidéo ».")
    bornes = _bornes(body, infos)
    devis = UT.devis(bornes["secondes"])
    if body.get("confirme_cout") is not True:
        raise HTTPException(409, {"message": "Vidéo → mouvement payant : confirme le coût avant de lancer.",
                                  "devis": devis})
    nom = re.sub(r"[^A-Za-z0-9_-]+", "_", str(body.get("nom") or Path(chemin).stem)).strip("_")[:40] or "video"
    tache = uuid4().hex[:12]
    await R._plafond({"kind": "video_mouvement", "secondes": bornes["secondes"]}, CATEGORIE, f"uthana:{tache}")
    _poser_etat(j, tache, etat="prepare", video=chemin.name, devis=devis, nom=nom, bornes=bornes)
    _TACHES[tache] = asyncio.create_task(_travail(j, tache, chemin, bornes, nom, devis))
    return {"ok": True, "tache": tache, "devis": devis, "etat": "prepare"}


@router.get("/video/etat", dependencies=[Depends(_local)])
async def video_etat(job: str, tache: str):
    j = _job_nu(job)
    if not re.fullmatch(r"[0-9a-f]{12}", str(tache or "")):
        raise HTTPException(400, "tâche : identifiant de 12 caractères hexadécimaux attendu")
    p = _etat_chemin(j, tache)
    if not p.is_file():
        raise HTTPException(404, "tâche inconnue pour ce job")
    e = json.loads(p.read_text(encoding="utf-8"))
    if e.get("etat") not in ("fini", "echec") and tache not in _TACHES:
        e["etat"] = "interrompu"                           # le serveur a redémarré pendant le travail
    return e


@router.post("/godot", dependencies=[Depends(_local)])
async def godot(body: dict):
    """ZIP Godot 4 : le GLB de la version (clips compris), la scène .tscn et ses hitboxes sur les os choisis."""
    body = body or {}
    j, data, depuis = _version(body.get("job"), body.get("version"), "hitboxes")
    nom = str(body.get("nom") or "Personnage")
    try:
        octets, rapport = await asyncio.to_thread(MR.archive_godot, data, body.get("hitboxes"),
                                                  dossier=f"{j}_v{depuis['version']}", nom=nom)
    except ValueError as e:
        raise HTTPException(400, str(e))
    fichier = f"{j}_v{depuis['version']}_godot.zip"
    return Response(content=octets, media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{fichier}"',
                             "X-DZ-Hitboxes": str(len(rapport["hitboxes"])),
                             "X-DZ-Clips": str(len(rapport["clips"]))})
