# -*- coding: utf-8 -*-
"""SV1 (14/11/2026) — /api/studiov : le studio virtuel 3D de la capture et du live (conception
docs/superpowers/specs/2026-11-14-studio-virtuel-3d-design.md).

Boucle locale SEULEMENT (`routes._require_localhost`). L'espace est celui de la requête (X-Dz-Espace, sinon l'actif).
- `GET    /`               {espace, espace_nom, choisi, decors (de l'espace), livres, catalogue}
- `GET    /actif`          {decor | null, contexte} : le décor de l'espace ("" par défaut : pas de studio)
- `PUT    /choix`          {decor_id | ""} -> {choisi}
- `POST   /`               {base?, nom?} -> décor neuf de l'espace (copie d'un livré ou d'un décor de l'espace)
- `GET    /{id}`           {decor, contexte}
- `PUT    /{id}`           recette -> décor (livré : 409)
- `DELETE /{id}`           -> {supprime}
- `GET    /{id}/fabrique`  le GLB fabriqué par Blender, s'il existe (404 sinon)
- `GET    /habillage`      le catalogue du décorateur (lot SVH) : matières réelles, finitions, ambiances, styles
- `GET    /textures/stu/{slug}/{carte}.jpg`      une carte du pack d'intérieur (basecolor, normal, roughness, vignette)
- `GET    /textures/{cat|mat}/{id}/vignette.jpg` la vignette d'une matière de la Forge (catalogue ou utilisateur)
- `POST   /blender/matieres` {blend} -> {matieres} : les matières d'un fichier .blend (Blender sans fenêtre)
- `POST   /blender/cuire`    {blend, matiere?, metres?} -> {materials: [{ref, id, nom}]} : cuites et rangées dans la Forge
- `GET    /objets`           {objets, sources, licences, refusees} : la bibliothèque d'objets importés (lot SVO)
- `POST   /objets`           (multipart : fichier GLB + nom, source, auteur, licence, url) -> la fiche de l'objet
- `GET    /objets/{id}/modele.glb` ; `DELETE /objets/{id}` (409 s'il est posé dans un décor)
- `POST   /blender/objets`   {blend} -> {objets} ; `POST /blender/exporter` {blend, objet, …} -> la fiche (GLB sorti de Blender)
- `GET    /{id}/credits`     les crédits du décor et ce que ses licences permettent (export, partage)
- `GET    /bibliotheque/vignette?f=<fichier>`  la vignette d'une image de la Bibliothèque de l'application (lot SVB)
- `POST   /bibliotheque/image`  {filename} -> la fiche de l'image recopiée dans le studio (référence `img:`)
- `POST   /bibliotheque/modele` {job, fichier?} -> la fiche du modèle 3D généré, recopié dans les objets du studio
- `GET    /images/{id}/fichier` ; `DELETE /images/{id}` (409 si un décor l'emploie)
- `GET    /three/{module}.js` un chargeur three.js embarqué, ses imports réécrits pour la coque (GLTFLoader et ses deux aides)
Aucun réseau, aucune dépense. Journaux : identifiants seulement."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from loguru import logger

from app.services import studiov as S
from app.services import studiov_habillage as H
from app.services import studiov_images as SI
from app.services import studiov_objets as OB

router = APIRouter()


def _local(request: Request) -> None:
    from app.api.routes import _require_localhost
    _require_localhost(request)


def _espace() -> str:
    from app.services import espaces
    return espaces.espace_courant()


async def _json(request: Request, maximum: int = 512 * 1024) -> dict:
    octets = bytearray()
    async for bout in request.stream():
        octets += bout
        if len(octets) > maximum:
            raise HTTPException(413, "Corps de requête trop lourd.")
    try:
        d = json.loads(bytes(octets) or b"{}")
    except ValueError:
        raise HTTPException(400, "Corps JSON illisible.") from None
    if not isinstance(d, dict):
        raise HTTPException(400, "Corps JSON illisible.")
    return d


async def _faire(f, *args):
    try:
        return await asyncio.to_thread(f, *args)
    except S.RefusStudio as e:
        raise HTTPException(e.statut, str(e)) from None


@router.get("")
@router.get("/")
async def lister(request: Request):
    _local(request)
    eid = _espace()
    cx = await _faire(S.contexte, eid)
    return {"espace": eid, "espace_nom": cx["espace"]["nom"], "choisi": await _faire(S.choisi, eid),
            "decors": await _faire(S.lister, eid), "livres": await _faire(S.livres), "catalogue": S.catalogue()}


@router.get("/actif")
async def actif(request: Request):
    _local(request)
    eid = _espace()
    sid = await _faire(S.choisi, eid)
    return {"decor": await _faire(S.lire, sid) if sid else None, "contexte": await _faire(S.contexte, eid)}


@router.put("/choix")
async def choisir(request: Request):
    _local(request)
    d = await _json(request)
    return {"choisi": await _faire(S.choisir, _espace(), d.get("decor_id"))}


@router.post("")
@router.post("/")
async def creer(request: Request):
    _local(request)
    d = await _json(request)
    v = await _faire(S.creer, d.get("base") or None, d.get("nom"), _espace())
    logger.info("studiov: décor créé {} (base {})", v["id"], v["base"])
    return v


@router.get("/habillage")
async def habillage(request: Request):
    _local(request)
    return await asyncio.to_thread(H.habillage)


@router.get("/textures/{source}/{ident}/{carte}.jpg")
async def texture(source: str, ident: str, carte: str, request: Request):
    _local(request)
    try:
        if source == "stu":
            f = await asyncio.to_thread(H.chemin_carte, ident, carte)
            return FileResponse(f, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})
        if carte != "vignette":
            raise H.RefusHabillage("Matière ou carte inconnue.", 404)
        octets = await asyncio.to_thread(H.vignette, source, ident)
    except H.RefusHabillage as e:
        raise HTTPException(e.statut, str(e)) from None
    return Response(content=octets, media_type="image/jpeg", headers={"Cache-Control": "no-cache"})


async def _habiller(f, *args):
    try:
        return await asyncio.to_thread(f, *args)
    except H.RefusHabillage as e:
        raise HTTPException(e.statut, str(e)) from None


async def _objet(f, *args):
    try:
        return await asyncio.to_thread(f, *args)
    except OB.RefusObjet as e:
        raise HTTPException(e.statut, str(e)) from None
    except H.RefusHabillage as e:
        raise HTTPException(e.statut, str(e)) from None


async def _image(f, *args):
    try:
        return await asyncio.to_thread(f, *args)
    except SI.RefusImage as e:
        raise HTTPException(e.statut, str(e)) from None


@router.get("/bibliotheque/vignette")
async def bibliotheque_vignette(request: Request, f: str = ""):
    _local(request)
    octets = await _image(SI.vignette_bibliotheque, f)
    return Response(content=octets, media_type="image/jpeg", headers={"Cache-Control": "no-cache"})


@router.post("/bibliotheque/image")
async def bibliotheque_image(request: Request):
    _local(request)
    d = await _json(request, 8 * 1024)
    connu = {}
    try:                                                    # la licence et l'auteur que la Bibliothèque connaît
        from app.services import library_index as LI
        connu = (await LI.carte()).get(d.get("filename")) or {}
    except Exception:                                       # noqa: BLE001 — index indisponible : l'image entre sans provenance
        connu = {}
    v = await _image(SI.depuis_bibliotheque, d.get("filename"), connu)
    logger.info("studiov: image de la Bibliothèque recopiée {}", v["id"])
    return v


@router.post("/bibliotheque/modele")
async def bibliotheque_modele(request: Request):
    _local(request)
    d = await _json(request, 8 * 1024)
    v = await _objet(OB.depuis_bibliotheque, d.get("job"), d.get("fichier"))
    logger.info("studiov: modèle 3D de la Bibliothèque recopié {}", v["id"])
    return v


@router.get("/images/{iid}/fichier")
async def image_fichier(iid: str, request: Request):
    _local(request)
    f = await _image(SI.chemin, iid)
    return FileResponse(f, media_type="image/png" if f.suffix == ".png" else "image/jpeg", headers={"Cache-Control": "no-cache"})


@router.delete("/images/{iid}")
async def image_supprimer(iid: str, request: Request):
    _local(request)
    await _image(SI.supprimer, iid)
    return {"supprime": iid}


@router.get("/objets")
async def objets(request: Request):
    _local(request)
    return {"objets": await _objet(OB.lister), "sources": list(OB.SOURCES), "licences": {k: OB.droits(k) for k in OB.LICENCES},
            "refusees": OB.REFUSEES, "plafond_triangles": OB.MAX_TRIANGLES}


@router.post("/objets")
async def objet_importer(request: Request, fichier: UploadFile = File(...), nom: str = Form(""), source: str = Form("fichier"),
                         auteur: str = Form(""), licence: str = Form(""), url: str = Form("")):
    _local(request)
    octets = await fichier.read(OB.MAX_OCTETS + 1)
    v = await _objet(OB.importer, octets, {"nom": nom or (fichier.filename or "").rsplit(".", 1)[0], "source": source,
                                           "auteur": auteur, "licence": licence, "url": url})
    logger.info("studiov: objet importé {} ({} triangles, source {})", v["id"], v["triangles"], v["source"])
    return v


@router.get("/objets/{oid}/modele.glb")
async def objet_modele(oid: str, request: Request):
    _local(request)
    f = await _objet(OB.chemin, oid)
    return FileResponse(f, media_type="model/gltf-binary", headers={"Cache-Control": "no-cache"})


@router.delete("/objets/{oid}")
async def objet_supprimer(oid: str, request: Request):
    _local(request)
    await _objet(OB.supprimer, oid)
    logger.info("studiov: objet supprimé {}", oid)
    return {"supprime": oid}


@router.post("/blender/objets")
async def blender_objets(request: Request):
    _local(request)
    d = await _json(request, 8 * 1024)
    return {"objets": await _objet(H.objets_blender, d.get("blend"))}


@router.post("/blender/exporter")
async def blender_exporter(request: Request):
    _local(request)
    d = await _json(request, 8 * 1024)
    v = await _objet(H.exporter_blender, d.get("blend"), d.get("objet"), d)
    logger.info("studiov: objet sorti de Blender {}", v["id"])
    return v


# les chargeurs three.js embarqués importent « three » par son nom nu : la coque n'a pas de carte d'import. On les sert
# donc avec leurs imports réécrits vers les fichiers de l'application (liste FERMÉE de trois modules).
_MODULES_THREE = {"GLTFLoader": "loaders/GLTFLoader.js", "BufferGeometryUtils": "utils/BufferGeometryUtils.js",
                  "SkeletonUtils": "utils/SkeletonUtils.js"}


def _module_three(nom: str) -> str:
    from pathlib import Path
    racine = Path(__file__).resolve().parents[3] / "frontend" / "dist" / "assets" / "three" / "addons"
    src = (racine / _MODULES_THREE[nom]).read_text("utf-8")
    src = src.replace("from 'three'", "from '/assets/three/three.module.min.js'").replace('from "three"', 'from "/assets/three/three.module.min.js"')
    for autre in ("BufferGeometryUtils", "SkeletonUtils"):
        src = src.replace(f"'../utils/{autre}.js'", f"'/api/studiov/three/{autre}.js'").replace(f"'./{autre}.js'", f"'/api/studiov/three/{autre}.js'")
    return src


@router.get("/three/{nom}.js")
async def module_three(nom: str, request: Request):
    _local(request)
    if nom not in _MODULES_THREE:
        raise HTTPException(404, "Module inconnu.")
    try:
        src = await asyncio.to_thread(_module_three, nom)
    except OSError:
        raise HTTPException(404, "Module inconnu.") from None
    return Response(content=src, media_type="text/javascript", headers={"Cache-Control": "no-cache"})


@router.post("/blender/matieres")
async def blender_matieres(request: Request):
    _local(request)
    d = await _json(request, 8 * 1024)
    return {"matieres": await _habiller(H.matieres_blender, d.get("blend"))}


@router.post("/blender/cuire")
async def blender_cuire(request: Request):
    _local(request)
    d = await _json(request, 8 * 1024)
    faits = await _habiller(H.cuire_blender, d.get("blend"), d.get("matiere"), d.get("metres"))
    logger.info("studiov: {} matière(s) cuite(s) depuis Blender", len(faits))
    return {"materials": faits}


@router.get("/{sid}")
async def lire(sid: str, request: Request):
    _local(request)
    eid = _espace()
    return {"decor": await _faire(S.du_meme_espace, sid, eid), "contexte": await _faire(S.contexte, eid)}


@router.put("/{sid}")
async def enregistrer(sid: str, request: Request):
    _local(request)
    d = await _json(request)
    if not S.ID_LIVRE.match(sid):
        await _faire(S.du_meme_espace, sid, _espace())
    return await _faire(S.enregistrer, sid, d)


@router.delete("/{sid}")
async def supprimer(sid: str, request: Request):
    _local(request)
    if not S.ID_LIVRE.match(sid):
        await _faire(S.du_meme_espace, sid, _espace())
    await _faire(S.supprimer, sid)
    logger.info("studiov: décor supprimé {}", sid)
    return {"supprime": sid}


@router.get("/{sid}/credits")
async def credits(sid: str, request: Request):
    _local(request)
    v = await _faire(S.du_meme_espace, sid, _espace())
    return await _objet(OB.credits, v)


@router.get("/{sid}/fabrique")
async def fabrique(sid: str, request: Request):
    _local(request)
    await _faire(S.du_meme_espace, sid, _espace())
    f = S.chemin_fabrique(sid)
    if f is None:
        raise HTTPException(404, "Décor non fabriqué.")
    return FileResponse(f, media_type="model/gltf-binary", headers={"Cache-Control": "no-cache"})
