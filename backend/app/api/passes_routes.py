# -*- coding: utf-8 -*-
"""t334 (A4 du lot Scenario, 29/10/2026) — /api/passes : les PASSES HEADLESS d'un plan (clay Workbench, look EEVEE,
profondeur, normales, masques) rendues par Blender en arrière-plan avec la caméra du plan. GRATUIT et LOCAL : aucune
garde de dépense (aucun fournisseur), le lancement est réservé à la machine locale. Service : services/passes_blender.py.

  GET  /etat                         {blender: {dispo, exe, version, raison}, installer}
  GET  /plan/{shot_id}               {blender, scene (la scène du Plateau du plan, ou null), runs (5 derniers), job}
  POST /plan/{shot_id}               {sequence?, passes?} → 202 {job} ; 404 plan → 409 sans scène / scène vide /
                                     une passe tourne déjà → 503 Blender absent (dit quoi installer)
  GET  /chapitre/{chapter_id}        {plans: {shot_id: dernier run}} — les vignettes des cartes de l'Atelier
  GET  /job/{jid}                    l'avancement ; POST /job/{jid}/annuler → tue Blender
  GET  /fichier/{shot_id}/{run}/{nom}  une image (PNG) ou un aperçu (MP4) d'un run

Les images fixes de chaque passe (la première image d'une séquence) entrent dans la Bibliothèque, provenance
« passe » (passe_<plan>_<run>_<passe>.png), recette {outil: passes_blender, plan, scène, passe, run, blender}.
"""
from __future__ import annotations

import asyncio
import re
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from loguru import logger

from app import i18n
from app.config import settings
from app.services import passes_blender as PB

router = APIRouter()

_ID = re.compile(r"^[0-9A-Za-z-]{1,40}$")
_JID = re.compile(r"^pb_\d{8}-\d{6}-[0-9a-f]{4}$")
_TACHES: set = set()


def _lang(request) -> str:
    return i18n.langue_requete(request) if request is not None else i18n.langue_ui()


def _local(request: Request) -> None:
    from app.api.routes import _require_localhost
    _require_localhost(request)


def _racine() -> Path:
    return settings.outputs_path


def _blender_public(e: dict, lang: str) -> dict:
    out = dict(e)
    if not e.get("dispo"):
        out["installer"] = i18n.msg("passes.installer", lang, min=".".join(str(x) for x in PB.VERSION_MIN))
    return out


async def _plan_et_scene(shot_id: str, lang: str):
    """(plan, scène du Plateau liée au plan la plus récente, ou None). 404 plan."""
    from sqlalchemy import select
    from app.services.storage import Scene3D, Shot, async_session_factory
    from app.services.scene3d_routes import _dict
    if not _ID.match(shot_id or ""):
        raise HTTPException(404, i18n.msg("passes.plan_introuvable", lang))
    async with async_session_factory() as session:
        s = await session.get(Shot, shot_id)
        if s is None:
            raise HTTPException(404, i18n.msg("passes.plan_introuvable", lang))
        r = (await session.execute(select(Scene3D).where(Scene3D.shot_id == shot_id)
                                   .order_by(Scene3D.updated_at.desc()).limit(1))).scalars().first()
        return s, (_dict(r) if r is not None else None)


def _scene_public(d: dict | None) -> dict | None:
    if d is None:
        return None
    kfs = d.get("keyframes") or []
    return {"id": d["id"], "nom": d.get("nom"), "aspect": d.get("aspect"), "instances": len(d.get("instances") or []),
            "keyframes": len(kfs), "anime": len(kfs) >= 2,
            "duree_s": round(kfs[-1]["t"] - kfs[0]["t"], 3) if len(kfs) >= 2 else 0.0}


def _job_courant(shot_id: str) -> dict | None:
    j = PB.job_actif(shot_id)
    if j is None:                      # le dernier job fini de ce plan, pour qu'un rechargement voie l'erreur
        finis = [x for x in PB._JOBS.values() if x["shot_id"] == shot_id]
        j = finis[-1] if finis else None
    return PB.job_public(j) if j else None


@router.get("/etat")
async def etat(request: Request):
    e = await asyncio.to_thread(PB.etat_blender)
    return {"blender": _blender_public(e, _lang(request))}


@router.get("/plan/{shot_id}")
async def plan(shot_id: str, request: Request):
    lang = _lang(request)
    _s, d = await _plan_et_scene(shot_id, lang)
    e = await asyncio.to_thread(PB.etat_blender)
    return {"shot_id": shot_id, "blender": _blender_public(e, lang), "scene": _scene_public(d),
            "runs": PB.lire_runs(PB.dossier_plan(_racine(), shot_id)), "job": _job_courant(shot_id),
            "passes": list(PB.PASSES), "bornes": {"fps": PB.SEQ_FPS, "images_max": PB.SEQ_MAX_IMAGES}}


@router.get("/chapitre/{chapter_id}")
async def chapitre(chapter_id: str):
    """Le dernier run de chaque plan du chapitre (vignettes des cartes) : une lecture de disque, gratuite."""
    from sqlalchemy import select
    from app.services.storage import Shot, async_session_factory
    if not _ID.match(chapter_id or ""):
        return {"plans": {}}
    async with async_session_factory() as session:
        ids = (await session.execute(select(Shot.id).where(Shot.chapter_id == chapter_id))).scalars().all()
    out = {}
    for sid in ids:
        runs = PB.lire_runs(PB.dossier_plan(_racine(), sid), 1)
        if runs:
            out[sid] = runs[0]
    return {"plans": out}


def _lire_maillage(inst):
    from app.services.scene3d_routes import _lire_maillage as lm
    return lm(inst)


async def _ranger(j: dict, shot, scene: dict, params: dict, dossier: Path, exe_version: str) -> None:
    """Après Blender : inventaire, aperçus vidéo, manifeste, Bibliothèque. Une erreur ici finit le job en erreur."""
    from app.services import library_index as LI
    n = len(params["cameras"])
    try:
        fichiers = PB.inventaire(dossier, params["passes"], n)
    except PB.PasseRefusee as e:
        j.update(statut="erreur", erreur=str(e)[:300])
        return
    passes = {}
    noms_biblio = []
    for p, fs in fichiers.items():
        entree = {"fichiers": fs}
        if n > 1:
            entree["video"] = await asyncio.to_thread(PB.video_sequence, dossier, p, params["fps"])
        nom = f"passe_{shot.id[:8]}_{j['run']}_{p}.png"
        try:
            settings.images_path.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dossier / fs[0], settings.images_path / nom)
            entree["bibliotheque"] = nom
            noms_biblio.append((p, nom))
        except OSError as e:                      # la Bibliothèque manque : le run reste lisible dans le plan
            logger.warning("passes : copie Bibliothèque impossible ({})", e)
        passes[p] = entree
    manifeste = {"run": j["run"], "shot_id": shot.id, "chapter_id": shot.chapter_id, "scene_id": scene["id"],
                 "date": datetime.now().isoformat(timespec="seconds"), "blender": exe_version,
                 "sequence": n > 1, "images": n, "fps": params["fps"], "temps": params["temps"],
                 "largeur": params["largeur"], "hauteur": params["hauteur"], "passes": passes,
                 "profondeur": {"proche_m": params["proche"], "loin_m": params["loin"], "convention": "blanc_proche",
                                "bits": 16},
                 "normales": {"espace": "camera", "convention": "opengl"},
                 "couleurs": params["couleurs"], "palette": params["palette"], "exclus": params["exclus"]}
    PB.ecrire_manifeste(dossier, manifeste)
    for p, nom in noms_biblio:
        await LI.noter([nom], "passe", recette={"outil": "passes_blender", "plan": shot.id, "scene": scene["id"],
                                                 "passe": p, "run": j["run"], "blender": exe_version,
                                                 "images": n, "t": params["temps"][0]},
                       parent=getattr(shot, "keyframe_image", None) or None, relation="passe")
    PB.purger(PB.dossier_plan(_racine(), shot.id))
    j.update(statut="fini", progression=100)


async def _executer(j: dict, exe: dict, script: Path, dossier: Path, shot, scene: dict, params: dict) -> None:
    try:
        if await asyncio.to_thread(PB.executer, j, exe["exe"], script, dossier):
            await _ranger(j, shot, scene, params, dossier, exe.get("version") or "")   # « fini » après la Bibliothèque
    except Exception as e:                        # jamais un job « rendu » éternel
        logger.exception("passes : échec du job {}", j["id"])
        j.update(statut="erreur", erreur=str(e)[:300])
    finally:
        import time as _t
        j["fin"] = _t.time()
        if j["statut"] in ("annule", "erreur"):
            shutil.rmtree(dossier, ignore_errors=True)


@router.post("/plan/{shot_id}", status_code=202)
async def lancer(shot_id: str, request: Request, body: dict | None = None):
    _local(request)
    lang = _lang(request)
    body = body if isinstance(body, dict) else {}
    shot, d = await _plan_et_scene(shot_id, lang)
    if d is None:
        raise HTTPException(409, i18n.msg("passes.sans_scene", lang))
    sequence = body.get("sequence") is True
    passes = body.get("passes")
    if passes is not None and (not isinstance(passes, list) or not passes or len(passes) > len(PB.PASSES)
                               or not all(isinstance(x, str) and x in PB.PASSES for x in passes)):
        raise HTTPException(400, i18n.msg("passes.passes_inconnues", lang, liste=", ".join(PB.PASSES)))
    if PB.job_actif() is not None:
        raise HTTPException(409, i18n.msg("passes.deja", lang))
    exe = await asyncio.to_thread(PB.etat_blender)
    if not exe.get("dispo"):
        raise HTTPException(503, _blender_public(exe, lang)["installer"])
    # le GLB de la scène, composé ICI dans le dossier du run (sans faisceau, sans version de plus au Plateau)
    run = PB.nouveau_run()
    dossier = PB.dossier_plan(_racine(), shot_id) / run
    dossier.mkdir(parents=True, exist_ok=True)
    try:
        from app.services import scene3d_glb as G
        _cols, _orig, exclus = PB.couleurs(d["instances"])
        solides = [i for i in d["instances"] if i.get("id") not in exclus]
        if not solides:
            raise PB.PasseRefusee("scène vide")
        glb, _rap = await asyncio.to_thread(G.composer, solides, _lire_maillage)
        (dossier / "scene.glb").write_bytes(glb)
        params = PB.parametres(d, glb=str(dossier / "scene.glb"), sortie=str(dossier), sequence=sequence,
                               passes=passes)
        script = dossier / "passes_blender.py"
        script.write_text(PB.generer_script(params), encoding="utf-8")
        j = PB.nouveau_job(shot_id, run, len(params["cameras"]) > 1, len(params["passes"]) * len(params["cameras"]))
    except (PB.PasseRefusee, ValueError) as e:
        shutil.rmtree(dossier, ignore_errors=True)
        raise HTTPException(409, i18n.msg("passes.scene_inutilisable", lang, msg=str(e)[:200]))
    except RuntimeError as e:                     # gltfpack absent pour un maillage allégé
        shutil.rmtree(dossier, ignore_errors=True)
        raise HTTPException(503, i18n.msg("passes.scene_inutilisable", lang, msg=str(e)[:200]))
    t = asyncio.create_task(_executer(j, exe, script, dossier, shot, d, params))
    _TACHES.add(t)
    t.add_done_callback(_TACHES.discard)
    return {"job": PB.job_public(j), "images": len(params["cameras"]), "passes": params["passes"],
            "blender": exe.get("version")}


@router.get("/job/{jid}")
async def lire_job(jid: str, request: Request):
    j = PB.job(jid) if _JID.match(jid or "") else None
    if j is None:
        raise HTTPException(404, i18n.msg("passes.job_introuvable", _lang(request)))
    return PB.job_public(j)


@router.post("/job/{jid}/annuler")
async def annuler(jid: str, request: Request):
    _local(request)
    j = PB.job(jid) if _JID.match(jid or "") else None
    if j is None:
        raise HTTPException(404, i18n.msg("passes.job_introuvable", _lang(request)))
    return {"annule": PB.annuler(jid), "job": PB.job_public(j)}


@router.get("/fichier/{shot_id}/{run}/{nom}")
async def fichier(shot_id: str, run: str, nom: str, request: Request):
    if not _ID.match(shot_id or "") or not PB.run_valide(run) or not PB.fichier_valide(nom):
        raise HTTPException(404, i18n.msg("passes.fichier_introuvable", _lang(request)))
    p = PB.dossier_plan(_racine(), shot_id) / run / nom
    if not p.is_file():
        raise HTTPException(404, i18n.msg("passes.fichier_introuvable", _lang(request)))
    return FileResponse(p, media_type="video/mp4" if nom.endswith(".mp4") else "image/png")
