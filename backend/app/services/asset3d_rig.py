# -*- coding: utf-8 -*-
"""Rig et animations Meshy pour un job `assets3d` (fal) — T104, plan-moteurs-3d T2 (R10e P1).

docs.meshy.ai/en/api/rigging, /animation et /remesh relues le 06/10/2026 :
  - POST openapi/v1/rigging : `model_url` (.glb, face vers +Z) OU `input_task_id`, `height_meters` (défaut 1.7) ;
    humanoïdes TEXTURÉS seulement ; au-delà de 300 000 faces : non supporté → remesh d'abord
    (POST openapi/v1/remesh, `target_polycount` 100–300 000) ; réponse result.rigged_character_glb_url +
    result.basic_animations.{walking,running}_glb_url ; 5 crédits.
  - POST openapi/v1/animations : `rig_task_id`, `action_id` (entier de la bibliothèque) ; réponse
    result.animation_glb_url ; 3 crédits l'action.
Le proxy allowliste déjà ces trois chemins (meshy_service.ALLOWED_BASES) — ce module RELIE le flux fal à ce qui
était déjà atteignable. Chaque tâche Meshy lancée est rendue dans `taches`, DANS L'ORDRE du devis
(pricing.estimate kind asset3d_rig : remesh?, rig, actions…) : la route rattache chaque dépense à SA tâche.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from loguru import logger

from app.services import asset3d_service as A3
from app.services import meshy_service as MS

RIG_BASE = "openapi/v1/rigging"
ANIM_BASE = "openapi/v1/animations"
REMESH_BASE = "openapi/v1/remesh"
RIG_MAX_FACES = 300_000              # docs.meshy.ai/en/api/rigging, relue le 06/10/2026
RIG_REMESH_POLYCOUNT = 100_000       # sous la limite, topologie triangle
ANIMS_DE_BASE = ("walking", "running")


def _urls_du_rig(task: dict) -> dict:
    """{'rig', 'rig_fbx', 'walking', 'running'} → URL, depuis la forme documentée (result.*). La clé historique du
    mock (rigged_model_url) reste acceptée."""
    res = task.get("result") if isinstance(task.get("result"), dict) else task
    out = {}
    glb = res.get("rigged_character_glb_url") or res.get("rigged_model_url")
    if glb:
        out["rig"] = glb
    if res.get("rigged_character_fbx_url"):
        out["rig_fbx"] = res["rigged_character_fbx_url"]
    for nom in ANIMS_DE_BASE:
        u = (res.get("basic_animations") or {}).get(f"{nom}_glb_url")
        if u:
            out[nom] = u
    return out


def devis(job: str, actions=()) -> dict:
    """Ce que le rig coûtera, AVANT : les faces sont LUES sur le GLB courant. FileNotFoundError si le job n'existe
    pas."""
    from app.services import mesh_optimize, pricing
    d = A3._job_dir(job)
    if not d.is_dir():
        raise FileNotFoundError(f"job 3D inconnu : {job}")
    nom = A3._glb_courant(job)
    if not (d / nom).is_file():
        raise FileNotFoundError(f"{nom} introuvable pour ce job")
    st = mesh_optimize.glb_stats(d / nom)
    remesh = st["tris"] > RIG_MAX_FACES
    est = pricing.estimate({"kind": "asset3d_rig", "remesh_requis": remesh, "actions": list(actions or [])})
    return {"fichier": nom, "tris": st["tris"], "remesh_requis": remesh, **est}


def texturee(glb: Path) -> bool:
    from app.services import mesh_report
    return int((mesh_report.gltf_inventory(glb) or {}).get("textures") or 0) > 0


async def rigger_asset3d(job: str, *, height_m: float = 1.7, actions=(), on_step=None) -> dict:
    """Rig Meshy du GLB courant → model.v{n}.glb (squelette) + anim_*.v{n}.glb. Refuse AVANT toute dépense :
    géométrie non approuvée, maillage sans texture (Meshy le refuse — autant le dire ici, gratuitement)."""
    async def _step(label, pct):
        if on_step:
            await on_step(label, pct)

    d = A3._job_dir(job)
    if not d.is_dir():
        raise FileNotFoundError(f"job 3D inconnu : {job}")
    man = A3.read_manifest(job)
    if not A3.approval(job).get("approved"):
        raise PermissionError("Géométrie non approuvée : valide le volume avant de payer un rig.")
    src = d / A3._glb_courant(job)
    if not texturee(src):
        raise ValueError("Meshy ne rigge que des maillages TEXTURÉS (docs relues le 06/10/2026) : "
                         "texture-le d'abord (POST …/texturer), puis reviens.")
    from app.services import mesh_optimize
    tris = mesh_optimize.glb_stats(src)["tris"]
    h = float(height_m) if float(height_m) > 0 else 1.7
    taches: list[str] = []

    await _step("Envoi du maillage", 15)
    model_url = await A3._upload(src)

    remesh_id = None
    if tris > RIG_MAX_FACES:
        await _step(f"Remesh Meshy ({tris} faces > {RIG_MAX_FACES})", 25)
        r_payload = {"model_url": model_url, "topology": "triangle",
                     "target_polycount": RIG_REMESH_POLYCOUNT, "target_formats": ["glb"]}
        remesh_id = await MS.create_task(REMESH_BASE, r_payload)
        taches.append(remesh_id)
        await MS.record_created(remesh_id, REMESH_BASE, r_payload)
        t = await A3._attendre_meshy(REMESH_BASE, remesh_id, on_step, depart=25, fin=45)
        await MS.record_state(t, REMESH_BASE)
        payload = {"input_task_id": remesh_id, "height_meters": h}
    else:
        payload = {"model_url": model_url, "height_meters": h}

    await _step("Meshy rigging", 50)
    tid = await MS.create_task(RIG_BASE, payload)
    taches.append(tid)
    await MS.record_created(tid, RIG_BASE, payload)
    task = await A3._attendre_meshy(RIG_BASE, tid, on_step, depart=50, fin=80)
    await MS.record_state(task, RIG_BASE)
    urls = _urls_du_rig(task)
    if "rig" not in urls:
        raise RuntimeError(f"meshy: la tâche {tid} n'a rendu aucun GLB riggé (clés : {sorted(urls) or 'aucune'})")

    # crédits CONSOMMÉS : le squelette entre dans le registre tout de suite
    v = A3.next_version(job)
    dest = d / f"model.v{v}.glb"
    dest.write_bytes(await MS._fetch_url(urls["rig"]))
    anims: dict[str, str] = {}
    for nom in ANIMS_DE_BASE:
        if nom in urls:
            f = d / f"anim_{nom}.v{v}.glb"
            f.write_bytes(await MS._fetch_url(urls[nom]))
            anims[nom] = f.name
    anim_tasks: list[str] = []
    acts = [int(a) for a in (actions or [])]
    for i, aid in enumerate(acts):
        await _step(f"Animation {i + 1}/{len(acts)} ({MS.ACTIONS_RIG.get(aid, aid)})", 82 + 15 * i // len(acts))
        a_payload = {"rig_task_id": tid, "action_id": aid}
        atid = await MS.create_task(ANIM_BASE, a_payload)
        taches.append(atid)
        anim_tasks.append(atid)
        await MS.record_created(atid, ANIM_BASE, a_payload)
        at = await A3._attendre_meshy(ANIM_BASE, atid, None)
        await MS.record_state(at, ANIM_BASE)
        res = at.get("result") or {}
        if res.get("animation_glb_url"):
            f = d / f"anim_action_{aid}.v{v}.glb"
            f.write_bytes(await MS._fetch_url(res["animation_glb_url"]))
            anims[f"action_{aid}"] = f.name
        else:
            logger.warning(f"rig {job} : l'action {aid} (tâche {atid}) n'a rendu aucun GLB")

    A3.write_manifest(d, {**man, "version": v, "file": dest.name,
                          "rig": {"meshy_task": tid, "remesh_task": remesh_id, "height_m": h,
                                  "animations": anims, "rig_fbx_url": urls.get("rig_fbx")}})
    from app.services import mesh_report
    await asyncio.to_thread(mesh_report.write_report, job, dest.name, version=v,
                            extra={"outil": "meshy", "operation": "rig", "meshy_task": tid,
                                   "remesh_task": remesh_id, "animations": sorted(anims)})
    await _step("Complete", 100)
    return {"version": v, "file": dest.name, "meshy_task": tid, "remesh": remesh_id is not None,
            "animations": anims, "anim_tasks": anim_tasks, "taches": taches,
            "url": f"/api/assets/3d/{Path(job).name}/version/{v}"}


def animations_du_job(job: str) -> list[dict]:
    """Les clips rapatriés qui existent VRAIMENT sur le disque."""
    d = A3._job_dir(job)
    try:
        rig = A3.read_manifest(job).get("rig") or {}
    except FileNotFoundError:
        return []
    return [{"nom": nom, "file": f, "url": f"/api/assets/3d/{Path(job).name}/animation/{nom}"}
            for nom, f in sorted((rig.get("animations") or {}).items())
            if (d / Path(str(f)).name).is_file()]
