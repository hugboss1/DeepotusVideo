# -*- coding: utf-8 -*-
"""t189 (G7, plan « Génération IA enrichie », 12/10/2026) — le STORYBOARD 3D : SAM 3 de fal reconstruit les objets de
l'image d'un plan en GLB placés ; ils deviennent les instances de la scène du Plateau 3D de ce plan.

Schémas fal RELUS le 12/10/2026 (ils font foi ; le plan d'origine se trompait sur certains points) :
  * `fal-ai/sam-3/3d-objects` — requis `image_url` ; `prompt` (défaut fal « car » : on l'envoie TOUJOURS, ou des
    boîtes), `box_prompts` [{x_min, y_min, x_max, y_max, object_id?} entiers], `point_prompts`, `mask_urls`,
    `detection_threshold` (0,1–1), `seed`, `export_textured_glb` (défaut faux : on envoie vrai), `pointmap_url`.
    Sortie : `model_glb` (scène combinée en multi-objets, maillage unique sinon), `individual_glbs` (SEULEMENT en
    multi-objets, éléments possiblement nuls), `metadata` = [{object_index, rotation, translation, scale,
    camera_pose}] où rotation / translation / scale sont des tableaux IMBRIQUÉS ([[x,y,z,w]], [[tx,ty,tz]],
    [[sx,sy,sz]]) ou null ; `gaussian_splat`, `artifacts_zip` (ignorés ici).
  * `fal-ai/sam-3/3d-body` (option « corps humain ») — requis `image_url` ; `include_3d_keypoints` (défaut vrai : on
    envoie faux, sinon des sphères polluent le GLB), `export_meshes` (faux : les .ply ne servent pas),
    `include_mhr_params` (faux), `mask_url`. Sortie : `model_glb` (tous les corps combinés), `visualization`,
    `metadata` (points clés, AUCUNE transformation par objet) => UNE instance « sujet », transformation identité.

PRIX relevés sur fal.ai le 12/10/2026 : les deux pages affichent « $0.02 per unit », unité NON précisée. On chiffre
0,02 $ par requête et on le dit (« unité fal à confirmer au premier tir ») ; le « 0,005 $ par requête » du plan est le
prix de `fal-ai/sam-3/image`, un AUTRE endpoint (détourage), à ne pas confondre.

Les appels réseau passent par les trois coutures de matte_service (`_upload`, `_fal_subscribe`, `_download`) que les
bancs remplacent. PAYANT : la route passe la garde des plafonds AVANT d'appeler `reconstruire`.
"""
from __future__ import annotations

import asyncio
import json
import math
import re
import shutil
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from loguru import logger

from app.config import settings

# ── registre ─────────────────────────────────────────────────────────────────
MODELES = {
    "sam-3-3d-objects": {"label": "SAM 3 — objets 3D", "endpoint": "fal-ai/sam-3/3d-objects",
                         "prix": "sam3_3d_objects_usd", "corps": False},
    "sam-3-3d-body": {"label": "SAM 3 — corps humain 3D", "endpoint": "fal-ai/sam-3/3d-body",
                      "prix": "sam3_3d_body_usd", "corps": True},
}
ENDPOINTS = {mid: m["endpoint"] for mid, m in MODELES.items()}
DEFAUT = "sam-3-3d-objects"
UNITE_NOTE = "unité fal à confirmer au premier tir"
SEUIL_BORNES = (0.1, 1.0)
_MAX_BOITES = 32
_MAX_PROMPT = 300
_MAX_OBJETS = 32                     # scene3d_routes plafonne à 64 instances : on en laisse pour le décor posé à la main

# La convention d'axes SUPPOSÉE entre SAM 3 et le Plateau (repère three.js : +Y en haut, mètres, Euler XYZ). Rien dans
# le schéma fal ne la précise : aujourd'hui l'IDENTITÉ (translation recopiée, quaternion lu [x, y, z, w]). Elle sera
# TRANCHÉE au premier tir réel, avec l'accord de l'utilisateur (une scène connue, regardée au Plateau) ; tout
# changement passe par `_vers_plateau`, et par elle seule.
AXES_SAM3 = {"repere": "identite", "ordre_quaternion": "xyzw", "unite": "metre",
             "a_trancher": "au premier tir réel, avec l'utilisateur"}


def op_devis(modele: str, n: int = 1) -> dict:
    """L'op de devis (pricing.estimate) : la MÊME pour le devis, la garde des plafonds et le coût rendu."""
    return {"kind": "objets3d", "modele": str(modele or DEFAUT), "n": max(1, int(n))}


# ── requêtes ─────────────────────────────────────────────────────────────────
def nettoyer_prompt(prompt) -> str:
    return re.sub(r"\s+", " ", str(prompt or "")).strip()[:_MAX_PROMPT]


def noms_depuis_prompt(prompt) -> list[str]:
    """Les noms d'objets lus dans le prompt (découpé sur les virgules). SAM 3 ne rend AUCUN libellé par objet : ces
    noms ne sont qu'une aide à l'écran, posés dans l'ordre `object_index`."""
    return [p.strip()[:80] for p in nettoyer_prompt(prompt).split(",") if p.strip()]


def valider_boites(boxes) -> list[dict]:
    """[{x_min, y_min, x_max, y_max, object_id?}] en ENTIERS (pixels de l'image source), ou ValueError nommée."""
    if boxes in (None, []):
        return []
    if not isinstance(boxes, list) or len(boxes) > _MAX_BOITES:
        raise ValueError(f"boîtes : une liste d'au plus {_MAX_BOITES} rectangles {{x_min, y_min, x_max, y_max}}.")
    out = []
    for i, b in enumerate(boxes):
        if isinstance(b, (list, tuple)) and len(b) == 4:
            b = dict(zip(("x_min", "y_min", "x_max", "y_max"), b))
        if not isinstance(b, dict):
            raise ValueError(f"boîte {i + 1} illisible.")
        try:
            v = {k: float(b[k]) for k in ("x_min", "y_min", "x_max", "y_max")}
        except (KeyError, TypeError, ValueError):
            raise ValueError(f"boîte {i + 1} illisible : x_min, y_min, x_max, y_max attendus.")
        if not all(math.isfinite(x) for x in v.values()) or min(v.values()) < 0 \
                or v["x_max"] <= v["x_min"] or v["y_max"] <= v["y_min"]:
            raise ValueError(f"boîte {i + 1} vide ou hors de l'image.")
        boite = {k: int(round(x)) for k, x in v.items()}
        if b.get("object_id") is not None:
            try:
                boite["object_id"] = int(b["object_id"])
            except (TypeError, ValueError):
                raise ValueError(f"boîte {i + 1} : object_id entier attendu.")
        out.append(boite)
    return out


def build_request(image_url: str, prompt, boxes, modele: str = DEFAUT, detection_threshold=None) -> tuple[str, dict]:
    """(endpoint, arguments) d'un tir SAM 3. PUR. Objets : l'image + le GLB texturé + des boîtes si on en a, sinon le
    prompt nettoyé (jamais rien : fal chercherait des « car ») ; corps : l'image et trois options coupées."""
    m = MODELES.get(str(modele or ""))
    if m is None:
        raise ValueError(f"modèle SAM 3 inconnu : {modele!r} (connus : {', '.join(MODELES)})")
    if m["corps"]:
        return m["endpoint"], {"image_url": image_url, "include_3d_keypoints": False, "export_meshes": False,
                               "include_mhr_params": False}
    args = {"image_url": image_url}
    b = valider_boites(boxes)
    if b:
        args["box_prompts"] = b
    else:
        p = nettoyer_prompt(prompt)
        if not p:
            raise ValueError("décrivez les objets à reconstruire (ex. « personnage, table »), ou tracez des boîtes.")
        args["prompt"] = p
    args["export_textured_glb"] = True
    if detection_threshold is not None:
        args["detection_threshold"] = float(detection_threshold)
    return m["endpoint"], args


# ── géométrie PURE ───────────────────────────────────────────────────────────
def _aplatir(v):
    """[x, y, z] ou [[x, y, z]] (forme de fal) -> [floats] ; None (ou vide) -> None."""
    if v is None:
        return None
    while isinstance(v, (list, tuple)) and len(v) == 1 and isinstance(v[0], (list, tuple)):
        v = v[0]
    if not isinstance(v, (list, tuple)) or not v:
        return None
    try:
        out = [float(x) for x in v]
    except (TypeError, ValueError):
        return None
    return out if all(math.isfinite(x) for x in out) else None


def _euler_deg(q) -> list[float]:
    """Quaternion [x, y, z, w] -> angles d'Euler en DEGRÉS, ordre XYZ de three.js (M = Rx·Ry·Rz, celui de
    scene3d._rotation) : la décomposition de THREE.Euler.setFromRotationMatrix(m, "XYZ") — y = asin(m13),
    x = atan2(-m23, m33), z = atan2(-m12, m11) ; au blocage de cardan (|m13| ≈ 1), x = atan2(m32, m22), z = 0.
    Ce n'est PAS la formule « ZYX aérospatiale » du plan, qui décrit un autre ordre."""
    x, y, z, w = (list(q) + [0, 0, 0, 1])[:4] if q else (0.0, 0.0, 0.0, 1.0)
    n = math.sqrt(x * x + y * y + z * z + w * w)
    if n < 1e-12:
        return [0.0, 0.0, 0.0]
    x, y, z, w = x / n, y / n, z / n, w / n
    m11 = 1 - 2 * (y * y + z * z)
    m12 = 2 * (x * y - z * w)
    m13 = 2 * (x * z + y * w)
    m22 = 1 - 2 * (x * x + z * z)
    m23 = 2 * (y * z - x * w)
    m32 = 2 * (y * z + x * w)
    m33 = 1 - 2 * (x * x + y * y)
    ry = math.asin(max(-1.0, min(1.0, m13)))
    if abs(m13) < 0.9999999:
        rx, rz = math.atan2(-m23, m33), math.atan2(-m12, m11)
    else:
        rx, rz = math.atan2(m32, m22), 0.0
    return [math.degrees(rx) + 0.0, math.degrees(ry) + 0.0, math.degrees(rz) + 0.0]


def _vers_plateau(pos, rot) -> tuple[list, list]:
    """SAM 3 -> Plateau, selon AXES_SAM3 (identité aujourd'hui). LE seul endroit à changer quand la convention sera
    tranchée au premier tir réel."""
    return [float(v) for v in pos], [float(v) for v in rot]


def instances_depuis_sam3(meta, jobs, noms, dims=None) -> list[dict]:
    """Les instances du Plateau d'une reconstruction SAM 3. PUR.
    `meta` : les métadonnées (une par GLB gardé), triées ici par `object_index` ; `jobs` : les dossiers assets3d dans
    le même ordre ; `noms` : ceux du prompt (sinon « objet N ») ; `dims` : [l, h, p] mesurées par GLB, ou None.
    Rôle : le PREMIER objet est le sujet, les autres le décor. Le plan voulait « celui qui correspond au premier mot
    du prompt », mais SAM 3 ne rend aucun libellé par objet : c'est l'ordre `object_index` qui fait foi."""
    tri = sorted([m for m in (meta or []) if isinstance(m, dict)],
                 key=lambda m: m.get("object_index") if isinstance(m.get("object_index"), (int, float)) else 1e9)
    noms = list(noms or [])
    dims = list(dims or [])
    out = []
    for i, job in enumerate(jobs):
        m = tri[i] if i < len(tri) else {}
        t = _aplatir(m.get("translation"))
        pos = t[:3] if t and len(t) >= 3 else [0.0, 0.0, 0.0]
        q = _aplatir(m.get("rotation"))
        rot = _euler_deg(q) if q and len(q) == 4 else [0.0, 0.0, 0.0]
        s = _aplatir(m.get("scale"))
        ech = max(1e-3, sum(s[:3]) / 3) if s and len(s) >= 3 else 1.0
        pos, rot = _vers_plateau(pos, rot)
        inst = {"id": f"sam3_{i + 1:02d}", "nom": noms[i] if i < len(noms) and noms[i] else f"objet {i + 1}",
                "source": {"kind": "assets3d", "job": job, "file": "model.glb"}, "niveau": "allege",
                "role": "sujet" if i == 0 else "decor",
                "transform": {"pos": pos, "rot": rot, "scale": ech}}
        d = dims[i] if i < len(dims) else None
        if d:
            inst["dims"] = [float(x) for x in d]
        out.append(inst)
    return out


# ── le tir ───────────────────────────────────────────────────────────────────
def image_source(shot) -> str | None:
    """Le nom de l'image envoyée à SAM 3 : l'image de PRODUCTION du plan, sinon son croquis (jamais les bornes du
    Plateau, qui sont des captures de la scène 3D elle-même)."""
    for k in ("image", "sketch_image"):
        v = getattr(shot, k, None)
        if v:
            return Path(str(v)).name
    return None


def _url(v):
    if isinstance(v, dict):
        return v.get("url") or None
    return v if isinstance(v, str) and v else None


def _cibles(res: dict) -> list[tuple[int, str]]:
    """[(object_index, url)] des GLB à rapatrier : les individuels NON nuls, sinon le maillage unique."""
    res = res if isinstance(res, dict) else {}
    indiv = res.get("individual_glbs")
    out = [(k, _url(u)) for k, u in enumerate(indiv or []) if _url(u)]
    if not out and _url(res.get("model_glb")):
        out = [(0, _url(res.get("model_glb")))]
    return out[:_MAX_OBJETS]


def _meta_de(res: dict, k: int) -> dict:
    meta = res.get("metadata") if isinstance(res, dict) else None
    if not isinstance(meta, list):
        return {}
    for m in meta:
        if isinstance(m, dict) and m.get("object_index") == k:
            return m
    return meta[k] if k < len(meta) and isinstance(meta[k], dict) else {}


def _dims(data: bytes):
    """[l, h, p] mesurées comme le Plateau les mesure (scene3d_routes._offset_et_dims), ou None si illisible."""
    from app.services import scene3d_routes as SR
    try:
        d = SR._offset_et_dims(data)["dims"]
        return d if d and min(d) > 0 else None
    except Exception:  # noqa: BLE001 — un GLB illisible donne une instance sans dims, jamais un plantage
        return None


async def _scene_du_plan(shot, instances: list[dict]) -> str:
    """Crée la scène du plan (comme POST /scenes3d : chapitre hérité, « plan N », 9:16 comme les images de plan) ou
    met à jour la plus récente : ses anciennes instances sam3_* partent, les autres restent ; un sujet gardé devient
    décor puisque SAM 3 pose le sien (un seul sujet par scène)."""
    from sqlalchemy import select
    from app.services import scene3d_routes as SR
    from app.services.storage import Scene3D, async_session_factory
    async with async_session_factory() as session:
        r = (await session.execute(select(Scene3D).where(Scene3D.shot_id == shot.id)
                                   .order_by(Scene3D.updated_at.desc()).limit(1))).scalars().first()
        if r is None:
            return (await SR.creer({"shot_id": shot.id, "aspect": "9:16", "instances": instances}))["id"]
        try:
            gardees = [i for i in (json.loads(r.instances) if r.instances else [])
                       if isinstance(i, dict) and not str(i.get("id") or "").startswith("sam3_")]
        except ValueError:
            gardees = []
        if any(i.get("role") == "sujet" for i in instances):
            for i in gardees:
                if i.get("role") == "sujet":
                    i["role"] = "decor"
        r.instances = json.dumps(SR._instances(instances + gardees))
        r.updated_at = datetime.utcnow()
        await session.commit()
        return r.id


async def reconstruire(shot_id: str, prompt, boxes, modele: str = DEFAUT, detection_threshold=None) -> dict:
    """Le tir SAM 3 d'un plan, puis sa scène du Plateau. PAYANT : la route a déjà passé la clé, les champs et la garde
    des plafonds. Rend {scene_id, objets: [{id, nom, job, role}], n, usd}. ValueError (plan, image) ou RuntimeError
    (réponse de fal inexploitable : rien n'est écrit, aucun dossier ne reste)."""
    from app.services import matte_service as MT, mesh_sources, pricing as P
    from app.services.asset3d_service import write_manifest
    from app.services.storage import Shot, async_session_factory
    async with async_session_factory() as session:
        shot = await session.get(Shot, shot_id)
    if shot is None:
        raise ValueError("Plan introuvable.")
    nom_img = image_source(shot)
    src = settings.images_path / nom_img if nom_img else None
    if src is None or not src.is_file():
        raise ValueError("ce plan n'a ni image de production ni croquis à reconstruire.")
    url = await MT._upload(src)
    endpoint, args = build_request(url, prompt, boxes, modele, detection_threshold)
    res = await MT._fal_subscribe(endpoint, args)
    cibles = _cibles(res)
    if not cibles:
        cles = ", ".join(map(str, res or {})) if isinstance(res, dict) else type(res).__name__
        raise RuntimeError(f"SAM 3 (fal) : aucun GLB dans la réponse (clés : {cles}).")
    corps = MODELES[modele]["corps"]
    noms = noms_depuis_prompt(prompt)
    if corps and not noms:
        noms = ["sujet"]
    racine = mesh_sources._jobs_dir()
    lot = uuid4().hex[:8]
    ecrits, jobs, meta, dims = [], [], [], []
    try:
        for i, (k, u) in enumerate(cibles):
            job = f"sam3_{lot}_{i}"
            d = racine / job
            d.mkdir(parents=True, exist_ok=True)
            ecrits.append(d)
            dest = d / "model.glb"
            await MT._download(u, dest)
            data = dest.read_bytes() if dest.is_file() else b""
            if data[:4] != b"glTF":
                raise RuntimeError(f"SAM 3 (fal) : le fichier rendu n'est pas un GLB (en-tête glTF absent, "
                                   f"{len(data)} octets).")
            jobs.append(job)
            meta.append({} if corps else _meta_de(res, k))
            dims.append(await asyncio.to_thread(_dims, data))
        instances = instances_depuis_sam3(meta, jobs, noms, dims)
        for inst in instances:
            write_manifest(racine / inst["source"]["job"],
                           {"name": inst["nom"], "engine": modele, "stage": "storyboard", "shot_id": shot_id,
                            "outil": "storyboard3d"})
        scene_id = await _scene_du_plan(shot, instances)
    except BaseException:
        for d in ecrits:
            shutil.rmtree(d, ignore_errors=True)
        raise
    usd = P.estimate(op_devis(modele))["total_usd"]
    logger.info(f"storyboard3d : plan {shot_id} -> {len(instances)} objet(s), scène {scene_id} ({usd} $, {UNITE_NOTE})")
    return {"scene_id": scene_id, "n": len(instances), "usd": usd,
            "objets": [{"id": i["id"], "nom": i["nom"], "job": i["source"]["job"], "role": i["role"]}
                       for i in instances]}
