# -*- coding: utf-8 -*-
"""Le Plateau 3D — les routes (t127 T3-T4, 07/10/2026), montées sous /api/scenes3d.

Spec §9 ; plan docs/superpowers/plans/2026-10-07-plan-plateau-3d.md. TOUT est local et gratuit : aucune route ici ne
touche un fournisseur payant (la génération vidéo reste derrière sa propre porte).

  GET    ""                     liste (?chapter_id= / ?shot_id=)
  POST   ""                     crée — {nom?, chapter_id?, shot_id?, aspect?, focale_mm?, capteur_mm?, instances?,
                                camera?, keyframes?} ; une scène liée à un plan hérite de son chapitre ; une scène vide
                                reçoit un sujet capsule (1,7 m) et une caméra à 6 m, 35 mm
  GET|PUT|DELETE /{id}          lire / modifier (partiel, chaque champ revérifié) / supprimer (le dossier part aussi)
  GET    /sources               les maillages posables : jobs assets3d (versions) et entités de la bible à maillage
  GET    /source-dims           ?job=&file= → {dims, tris, offset} d'un maillage (pour poser ses dims)
  GET    /maillage              ?job=&file=&niveau=allege|plein → le GLB à AFFICHER (décimé « prop » en allégé, en cache)
  POST   /{id}/compose          compose le GLB de scène (scene3d_glb) → scene.v<n>.glb + rapport + fiche mesh_report
  GET    /{id}/scene.glb        ?v= → le GLB de scène (dernière version par défaut)
  POST   /{id}/mesure           {camera?, seuils?, scene?} → h, shot_type, focale… + l'écart avec le plan lié
  POST   /{id}/mouvement        {keyframes?, scene?} → camera_move, motion_prompt, avertissements + écart et durée
  POST   /{id}/capture          {quand: debut|fin, image_b64} → PNG validé dans les images, Bibliothèque « plateau »
  POST   /{id}/vers-plan        {appliquer: {...}, confirmer?} → avant/après ; écrit SEULEMENT avec confirmer:true

`scene` (dans /mesure et /mouvement) = l'état AFFICHÉ par l'écran ({instances, aspect, capteur_mm}) quand il n'est pas
encore enregistré : la mesure porte sur ce qu'on voit, pas sur le disque.
"""
import asyncio
import base64
import io
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response

from app.config import settings
from app.services import scene3d as S
from app.services import scene3d_glb as G
from app.services.storage import Scene3D, async_session_factory

router = APIRouter()

_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_JOB = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_FICHIER = re.compile(r"^model(\.v\d{1,4})?\.glb$")
_ROLES = ("sujet", "decor", "repere")
_MAX_INSTANCES = 64
_COULEUR = re.compile(r"^#[0-9A-Fa-f]{6}$")
_PNG_MAX = 12 * 1024 * 1024
_SHOT_TYPES = ("establishing", "wide", "medium", "close-up", "extreme close-up", "over-shoulder", "POV", "insert")


def _dossier(sid: str) -> Path:
    return settings.outputs_path / "scenes3d" / sid


def _jobs_dir() -> Path:
    from app.services import mesh_sources
    return mesh_sources._jobs_dir()


def _chemin_maillage(job, fichier) -> Path:
    if not isinstance(job, str) or not _JOB.match(job) or not isinstance(fichier, str) or not _FICHIER.match(fichier):
        raise HTTPException(400, "maillage : job ou fichier illisible (model.glb ou model.vN.glb).")
    p = _jobs_dir() / job / fichier
    if not p.is_file():
        raise HTTPException(404, f"maillage introuvable : {job}/{fichier}.")
    return p


# ── validation ───────────────────────────────────────────────────────────────
def _instances(v) -> list:
    if not isinstance(v, list):
        raise HTTPException(400, "instances : une liste.")
    if len(v) > _MAX_INSTANCES:
        raise HTTPException(400, f"au plus {_MAX_INSTANCES} instances par scène.")
    out, vus = [], set()
    for i, x in enumerate(v):
        if not isinstance(x, dict):
            raise HTTPException(400, f"instance {i} illisible.")
        iid = str(x.get("id") or f"inst_{i + 1:02d}")[:40]
        if iid in vus:
            raise HTTPException(400, f"identifiant d'instance en double : {iid}.")
        vus.add(iid)
        src = x.get("source") or {"kind": "proxy", "forme": "boite"}
        if not isinstance(src, dict):
            raise HTTPException(400, f"{iid} : source illisible.")
        kind = src.get("kind", "proxy")
        if kind == "proxy":
            if src.get("forme") not in G.FORMES:
                raise HTTPException(400, f"{iid} : forme inconnue — {', '.join(G.FORMES)}.")
            source = {"kind": "proxy", "forme": src["forme"]}
        elif kind == "assets3d":
            if not isinstance(src.get("job"), str) or not _JOB.match(src["job"]) or not _FICHIER.match(str(src.get("file") or "")):
                raise HTTPException(400, f"{iid} : maillage — job ou fichier illisible.")
            source = {"kind": "assets3d", "job": src["job"], "file": src["file"]}
        else:
            raise HTTPException(400, f"{iid} : source inconnue ({kind}) — proxy ou assets3d.")
        niveau = x.get("niveau", "proxy" if kind == "proxy" else "allege")
        if niveau not in G.NIVEAUX or (kind == "proxy") != (niveau == "proxy"):
            raise HTTPException(400, f"{iid} : niveau {niveau} incohérent avec la source.")
        role = x.get("role", "decor")
        if role not in _ROLES:
            raise HTTPException(400, f"{iid} : rôle inconnu — {', '.join(_ROLES)}.")
        tr = x.get("transform") or {}
        try:
            transform = {"pos": S._vec(tr.get("pos", [0, 0, 0]), "pos"), "rot": S._vec(tr.get("rot", [0, 0, 0]), "rot"),
                         "scale": S._num(tr.get("scale", 1), "scale", 0, strict=True)}
            dims = S._vec(x.get("dims"), "dims") if x.get("dims") is not None else None
        except ValueError as e:
            raise HTTPException(400, f"{iid} : {e}")
        if dims is not None and min(dims) <= 0:
            raise HTTPException(400, f"{iid} : dims positives attendues.")
        if dims is None and kind == "proxy":
            raise HTTPException(400, f"{iid} : une primitive a besoin de dims [l, h, p].")
        couleur = x.get("couleur") if isinstance(x.get("couleur"), str) and _COULEUR.match(x["couleur"]) else "#8a8f98"
        out.append({"id": iid, "nom": str(x.get("nom") or iid)[:80], "source": source, "niveau": niveau,
                    "dims": dims, "transform": transform, "couleur": couleur, "role": role,
                    "entity_id": str(x["entity_id"])[:40] if x.get("entity_id") else None})
    if sum(1 for x in out if x["role"] == "sujet") > 1:
        raise HTTPException(400, "un seul sujet par scène.")
    return out


def _camera(v) -> dict:
    if not isinstance(v, dict):
        raise HTTPException(400, "camera : {orbit, target, fov}.")
    try:
        cam = {"orbit": S._vec(v.get("orbit"), "orbit"), "target": S._vec(v.get("target"), "target"),
               "fov": S._num(v.get("fov"), "fov", 0, strict=True)}
    except ValueError as e:
        raise HTTPException(400, f"camera : {e}")
    if cam["orbit"][2] <= 0 or cam["fov"] >= 180:
        raise HTTPException(400, "camera hors bornes.")
    return cam


def _keyframes(v) -> list:
    if v == []:
        return []
    try:
        return S.valider_keyframes(v)
    except ValueError as e:
        raise HTTPException(400, f"keyframes : {e}")


def _scalaires(body, rec=None) -> dict:
    out = {}
    if "nom" in body:
        out["nom"] = (str(body["nom"] or "").strip() or "scène")[:120]
    if "aspect" in body:
        if body["aspect"] not in S.ASPECTS:
            raise HTTPException(400, f"aspect : {', '.join(S.ASPECTS)}.")
        out["aspect"] = body["aspect"]
    for k, lo, hi in (("focale_mm", 8, 400), ("capteur_mm", 4, 60)):
        if k in body:
            try:
                f = S._num(body[k], k, 0, strict=True)
            except ValueError as e:
                raise HTTPException(400, str(e))
            if not lo <= f <= hi:
                raise HTTPException(400, f"{k} : de {lo} à {hi}.")
            out[k] = f
    return out


def _dict(r: Scene3D) -> dict:
    def j(v, defaut):
        try:
            return json.loads(v) if v else defaut
        except ValueError:
            return defaut
    return {"id": r.id, "chapter_id": r.chapter_id, "shot_id": r.shot_id, "nom": r.nom, "aspect": r.aspect,
            "focale_mm": r.focale_mm, "capteur_mm": r.capteur_mm, "instances": j(r.instances, []),
            "camera": j(r.camera, None), "keyframes": j(r.keyframes, []), "glb_file": r.glb_file,
            "glb_version": r.glb_version or 0,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None}


async def _lire(session, sid) -> Scene3D:
    if not _ID.match(sid or ""):
        raise HTTPException(404, "Scène introuvable.")
    r = await session.get(Scene3D, sid)
    if r is None:
        raise HTTPException(404, "Scène introuvable.")
    return r


async def _shot(session, shot_id):
    from app.services.storage import Shot
    return await session.get(Shot, shot_id) if shot_id else None


def _scene_pour_mesure(d, override):
    sc = {"aspect": d["aspect"], "capteur_mm": d["capteur_mm"], "instances": d["instances"]}
    if isinstance(override, dict):
        if "instances" in override:
            sc["instances"] = _instances(override["instances"])
        sc.update(_scalaires({k: override[k] for k in ("aspect", "capteur_mm") if k in override}))
    if any(i.get("dims") is None for i in sc["instances"] if i.get("role") == "sujet"):
        raise HTTPException(409, "le sujet n'a pas encore de dimensions (maillage non mesuré) : posez-le d'abord.")
    return sc


# ── CRUD ─────────────────────────────────────────────────────────────────────
@router.get("")
async def lister(chapter_id: str = "", shot_id: str = ""):
    from sqlalchemy import select
    async with async_session_factory() as session:
        q = select(Scene3D).order_by(Scene3D.updated_at.desc())
        if chapter_id:
            q = q.where(Scene3D.chapter_id == chapter_id)
        if shot_id:
            q = q.where(Scene3D.shot_id == shot_id)
        rows = (await session.execute(q.limit(200))).scalars().all()
    return {"scenes": [{k: v for k, v in _dict(r).items() if k not in ("instances", "keyframes", "camera")}
                       | {"instances": len(_dict(r)["instances"])} for r in rows]}


@router.post("")
async def creer(body: dict):
    body = body if isinstance(body, dict) else {}
    sc = {"nom": "scène", "aspect": "16:9", "focale_mm": 35.0, "capteur_mm": 14.2}
    sc.update(_scalaires(body))
    inst = _instances(body["instances"]) if "instances" in body else _instances([
        {"id": "sujet", "nom": "Sujet", "source": {"kind": "proxy", "forme": "capsule"}, "dims": [0.5, 1.7, 0.4],
         "role": "sujet", "couleur": "#d8a657"}])
    cam = _camera(body["camera"]) if "camera" in body else {
        "orbit": [0, 90, 6], "target": [0, 0.85, 0], "fov": round(S.fov_de_focale(sc["focale_mm"], sc["capteur_mm"]), 4)}
    kfs = _keyframes(body.get("keyframes", []))
    async with async_session_factory() as session:
        chapter_id = body.get("chapter_id") or None
        shot_id = body.get("shot_id") or None
        if shot_id:
            s = await _shot(session, shot_id)
            if s is None:
                raise HTTPException(404, "Plan introuvable.")
            chapter_id = s.chapter_id
            if "nom" not in body:
                sc["nom"] = f"plan {s.idx + 1}"
        r = Scene3D(id=str(uuid4()), chapter_id=chapter_id, shot_id=shot_id, instances=json.dumps(inst),
                    camera=json.dumps(cam), keyframes=json.dumps(kfs), **sc)
        session.add(r)
        await session.commit()
        await session.refresh(r)
        return _dict(r)


@router.get("/sources")
async def sources():
    from app.services import mesh_sources
    from app.services.storage import BibleEntity
    from sqlalchemy import select
    jobs = await asyncio.to_thread(mesh_sources.lister)
    async with async_session_factory() as session:
        ents = (await session.execute(select(BibleEntity).where(BibleEntity.model3d_job.is_not(None)))).scalars().all()
    return {"jobs": [{"job": j["id"], "nom": j.get("nom") or j["id"],
                      "versions": [{"file": e["file"], "libelle": e.get("libelle"), "triangles": e.get("triangles")}
                                   for e in j.get("etapes") or [] if _FICHIER.match(str(e.get("file") or ""))]}
                     for j in jobs if isinstance(j, dict) and _JOB.match(str(j.get("id") or ""))],
            "entites": [{"id": e.id, "nom": e.name, "kind": e.kind, "job": e.model3d_job,
                         "file": e.model3d_file or "model.glb"} for e in ents]}


def _offset_et_dims(data: bytes) -> dict:
    from app.services import print3d
    tris = print3d.lire_glb_triangles(data)
    if not tris:
        raise HTTPException(415, "maillage vide.")
    lo = [min(p[i] for t in tris for p in t) for i in range(3)]
    hi = [max(p[i] for t in tris for p in t) for i in range(3)]
    return {"dims": [hi[i] - lo[i] for i in range(3)], "tris": len(tris),
            "offset": [-(lo[0] + hi[0]) / 2, -lo[1], -(lo[2] + hi[2]) / 2]}


@router.get("/source-dims")
async def source_dims(job: str = "", file: str = "model.glb"):
    p = _chemin_maillage(job, file)
    try:
        return await asyncio.to_thread(lambda: _offset_et_dims(p.read_bytes()))
    except ValueError as e:
        raise HTTPException(415, f"maillage illisible : {e}")


def _allege(p: Path) -> tuple[bytes, bool]:
    """Le GLB décimé « prop » d'une version, en cache (outputs/scenes3d/_cache, clé = empreinte des octets)."""
    import hashlib
    from app.services import mesh_optimize
    data = p.read_bytes()
    cle = hashlib.sha256(data).hexdigest()[:24]
    c = settings.outputs_path / "scenes3d" / "_cache" / f"{cle}.prop.glb"
    if c.is_file():
        return c.read_bytes(), True
    try:
        out, _info = mesh_optimize.decimer_octets(data, preset="prop")
    except ValueError:                                 # déjà sous la cible : tel quel
        return data, False
    c.parent.mkdir(parents=True, exist_ok=True)
    c.write_bytes(out)
    return out, True


@router.get("/maillage")
async def maillage(job: str = "", file: str = "model.glb", niveau: str = "allege"):
    if niveau not in ("allege", "plein"):
        raise HTTPException(400, "niveau : allege ou plein.")
    p = _chemin_maillage(job, file)
    if niveau == "plein":
        return FileResponse(p, media_type="model/gltf-binary")
    try:
        data, decime = await asyncio.to_thread(_allege, p)
    except RuntimeError as e:                          # gltfpack absent : dit, pas avalé
        raise HTTPException(503, f"décimation impossible : {e}")
    return Response(data, media_type="model/gltf-binary", headers={"X-Decime": "1" if decime else "0"})


@router.get("/{sid}")
async def lire(sid: str):
    """La scène, et le PLAN lié quand il y en a un (l'écran cale sa timeline sur `duration_s` et montre les écarts)."""
    async with async_session_factory() as session:
        r = await _lire(session, sid)
        d = _dict(r)
        s = await _shot(session, r.shot_id)
        if s is not None:
            d["plan"] = {"id": s.id, "idx": s.idx, "shot_type": s.shot_type, "camera_move": s.camera_move,
                         "duration_s": s.duration_s, "action": s.action or "",
                         "motion_prompt": getattr(s, "motion_prompt", None) or "",
                         "keyframe_image": getattr(s, "keyframe_image", None),
                         "keyframe_end": getattr(s, "keyframe_end", None)}
        return d


@router.put("/{sid}")
async def modifier(sid: str, body: dict):
    body = body if isinstance(body, dict) else {}
    async with async_session_factory() as session:
        r = await _lire(session, sid)
        for k, v in _scalaires(body).items():
            setattr(r, k, v)
        if "instances" in body:
            r.instances = json.dumps(_instances(body["instances"]))
        if "camera" in body:
            r.camera = json.dumps(_camera(body["camera"]))
        if "keyframes" in body:
            r.keyframes = json.dumps(_keyframes(body["keyframes"]))
        r.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(r)
        return _dict(r)


@router.delete("/{sid}")
async def supprimer(sid: str):
    async with async_session_factory() as session:
        r = await _lire(session, sid)
        await session.delete(r)
        await session.commit()
    shutil.rmtree(_dossier(sid), ignore_errors=True)
    return {"ok": True}


# ── composition ──────────────────────────────────────────────────────────────
def _lire_maillage(inst):
    src = inst.get("source") or {}
    try:
        return _chemin_maillage(src.get("job"), src.get("file")).read_bytes()
    except HTTPException:
        return None


@router.post("/{sid}/compose")
async def composer(sid: str):
    from app.services import mesh_report
    async with async_session_factory() as session:
        r = await _lire(session, sid)
        d = _dict(r)
        if not d["instances"]:
            raise HTTPException(400, "scène vide : rien à composer.")
        try:
            glb, rap = await asyncio.to_thread(G.composer, d["instances"], _lire_maillage)
        except ValueError as e:
            raise HTTPException(400, str(e))
        except RuntimeError as e:
            raise HTTPException(503, f"décimation impossible : {e}")
        v = (r.glb_version or 0) + 1
        dest = _dossier(sid) / f"scene.v{v}.glb"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(glb)
        fiche = await asyncio.to_thread(lambda: mesh_report.report(dest, version=v, avec_silhouettes=False))
        # les dims MESURÉES des maillages remontent dans la scène : la mesure du cadre parlera de la même boîte
        mesurees = {x["id"]: x["dims"] for x in rap["instances"]}
        for inst in d["instances"]:
            if inst["source"]["kind"] != "proxy":
                inst["dims"] = mesurees.get(inst["id"], inst.get("dims"))
        r.instances = json.dumps(d["instances"])
        r.glb_file, r.glb_version, r.updated_at = dest.name, v, datetime.utcnow()
        await session.commit()
    return {"ok": True, "version": v, "file": dest.name, "bytes": len(glb), "rapport": rap, "fiche": fiche}


@router.get("/{sid}/scene.glb")
async def scene_glb(sid: str, v: int = 0):
    async with async_session_factory() as session:
        r = await _lire(session, sid)
    n = v or r.glb_version or 0
    p = _dossier(sid) / f"scene.v{n}.glb"
    if n <= 0 or not p.is_file():
        raise HTTPException(404, "GLB de scène pas encore composé.")
    return FileResponse(p, media_type="model/gltf-binary", filename=f"plateau_{sid[:8]}_v{n}.glb")


# ── mesures ──────────────────────────────────────────────────────────────────
@router.post("/{sid}/mesure")
async def mesurer(sid: str, body: dict):
    body = body if isinstance(body, dict) else {}
    async with async_session_factory() as session:
        r = await _lire(session, sid)
        d = _dict(r)
        s = await _shot(session, r.shot_id)
    cam = _camera(body["camera"]) if "camera" in body else (d["camera"] and _camera(d["camera"]))
    if not cam:
        raise HTTPException(400, "aucune caméra à mesurer.")
    seuils = body.get("seuils")
    if seuils is not None:
        if not isinstance(seuils, dict) or set(seuils) - set(S.SEUILS) or not all(
                isinstance(v, (int, float)) and 0 < v < 10 for v in seuils.values()):
            raise HTTPException(400, f"seuils : {', '.join(S.SEUILS)} → nombres positifs.")
    try:
        m = S.mesure(_scene_pour_mesure(d, body.get("scene")), cam, seuils=seuils)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if s is not None:
        m["plan"] = {"shot_type": s.shot_type, "ecart": s.shot_type != m["shot_type"]}
    return m


@router.post("/{sid}/mouvement")
async def mouvement(sid: str, body: dict):
    body = body if isinstance(body, dict) else {}
    async with async_session_factory() as session:
        r = await _lire(session, sid)
        d = _dict(r)
        s = await _shot(session, r.shot_id)
    kfs = _keyframes(body["keyframes"]) if "keyframes" in body else d["keyframes"]
    if not kfs:
        raise HTTPException(400, "aucun keyframe : posez-en au moins un.")
    try:
        m = S.mouvement(_scene_pour_mesure(d, body.get("scene")), kfs, capteur_mm=d["capteur_mm"])
    except ValueError as e:
        raise HTTPException(400, str(e))
    if s is not None:
        m["plan"] = {"camera_move": s.camera_move, "ecart": s.camera_move != m["camera_move"],
                     "duration_s": s.duration_s}
        if kfs[-1]["t"] > s.duration_s + 1e-6:
            m["avertissements"].append(f"le dernier keyframe ({kfs[-1]['t']:.2f} s) dépasse la durée du plan "
                                       f"({s.duration_s:.2f} s).")
    return m


# ── captures et pont vers le plan ────────────────────────────────────────────
@router.post("/{sid}/capture")
async def capture(sid: str, body: dict):
    from PIL import Image
    from app.services import library_index as LI
    body = body if isinstance(body, dict) else {}
    quand = body.get("quand")
    if quand not in ("debut", "fin"):
        raise HTTPException(400, "quand : debut ou fin.")
    brut = str(body.get("image_b64") or "")
    if brut.startswith("data:"):
        brut = brut.split(",", 1)[-1]
    try:
        data = base64.b64decode(brut, validate=True)
    except (ValueError, TypeError):
        raise HTTPException(400, "image_b64 illisible.")
    if not data or len(data) > _PNG_MAX:
        raise HTTPException(400, "image vide ou trop lourde (12 Mo au plus).")
    try:
        with Image.open(io.BytesIO(data)) as im:
            im.verify()
            fmt = im.format
    except Exception:
        raise HTTPException(415, "ce n'est pas une image.")
    if fmt != "PNG":
        raise HTTPException(415, "PNG attendu.")
    async with async_session_factory() as session:
        r = await _lire(session, sid)
        d = _dict(r)
    dossier = settings.images_path
    dossier.mkdir(parents=True, exist_ok=True)
    n = 1
    while (dossier / f"plateau_{sid[:8]}_{quand}_{n}.png").exists():
        n += 1
    nom = f"plateau_{sid[:8]}_{quand}_{n}.png"
    (dossier / nom).write_bytes(data)
    t = None
    if d["keyframes"]:
        t = d["keyframes"][0]["t"] if quand == "debut" else d["keyframes"][-1]["t"]
    await LI.noter([nom], "plateau", recette={"outil": "plateau", "scene": sid, "quand": quand, "t": t,
                                              "aspect": d["aspect"], "focale_mm": d["focale_mm"]})
    return {"ok": True, "filename": nom, "quand": quand}


@router.post("/{sid}/vers-plan")
async def vers_plan(sid: str, body: dict):
    body = body if isinstance(body, dict) else {}
    ap = body.get("appliquer")
    if not isinstance(ap, dict) or not ap:
        raise HTTPException(400, "appliquer : {shot_type?, camera_move?, motion_prompt?, keyframe_image?, keyframe_end?}.")
    from app.models.schemas import CameraMove
    nouveau = {}
    for k, v in ap.items():
        if k == "shot_type":
            if v not in _SHOT_TYPES:
                raise HTTPException(400, "shot_type inconnu.")
        elif k == "camera_move":
            if v not in {m.value for m in CameraMove}:
                raise HTTPException(400, "camera_move inconnu.")
        elif k == "motion_prompt":
            if not isinstance(v, str) or not v.strip() or len(v) > 600:
                raise HTTPException(400, "motion_prompt : un texte de 600 caractères au plus.")
            v = v.strip()
        elif k in ("keyframe_image", "keyframe_end"):
            if not isinstance(v, str) or Path(v).name != v or not v.startswith("plateau_") \
                    or not (settings.images_path / v).is_file():
                raise HTTPException(400, f"{k} : une capture du Plateau existante.")
        else:
            raise HTTPException(400, f"champ inconnu : {k}.")
        nouveau[k] = v
    async with async_session_factory() as session:
        r = await _lire(session, sid)
        s = await _shot(session, r.shot_id)
        if s is None:
            raise HTTPException(409, "cette scène n'est liée à aucun plan du storyboard.")
        avant = {k: getattr(s, k, None) for k in nouveau}
        change = {k: v for k, v in nouveau.items() if avant.get(k) != v}
        if body.get("confirmer") is True and change:
            for k, v in change.items():
                setattr(s, k, v)
            s.updated_at = datetime.utcnow()
            await session.commit()
        return {"ok": True, "shot_id": s.id, "avant": avant, "apres": nouveau, "change": sorted(change),
                "applique": bool(body.get("confirmer") is True and change)}
