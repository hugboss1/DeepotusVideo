# -*- coding: utf-8 -*-
"""t331 (A1 du lot Scenario, 29/10/2026) — /api/blender : le pont « Scène Blender » (service : services/blender_mcp.py,
gabarits : services/blender_gabarits.py). LOCAL SEULEMENT, chaque route, LECTURES COMPRISES : `_require_localhost` refuse
le compagnon mobile même appairé (sa garde de jeton n'ouvre que des GET ; ici aucun ne l'est), et la garde des
écritures de main.py refuse déjà tout POST/PUT hors boucle locale.

  GET  /etat                         {exe, reglage, provenance (n)} — ne lance rien
  POST /sonder                       {serveur, outils, connecte, entete} — lance mcp-for-blender, lit, ne modifie rien
  GET  /scene?q=&n=                  {texte, objets}                      (get_scene_info)
  POST /regarder {mode, shading}     {id, url, legende, licences}          (look → outputs/blender/regards/<id>.png)
  GET  /regard/{id}                  l'image ; GET /regard/{id}/meta
  POST /regard/{id}/garder           → Bibliothèque (source « blender », recette + licences des assets importés)
  POST /plan/{shot}/envoyer {elements}  les GABARITS (caméra + focale, 3 points, blocking, clés) depuis la scène du
                                     Plateau du plan — aucun code dans le corps, seulement des éléments à cocher
  POST /nettoyer                     retire la collection DZ_Deepotus (les objets posés par l'app, rien d'autre)
  POST /assets/chercher {source, query…}   search_assets (licences gardées)
  POST /assets/importer {source, id…}      import_asset (provenance notée : licence, auteur, attribution, objets)
  GET  /provenance                   le journal des imports
  POST /generer {prompt, fournisseur, confirme_cout}   generate_3d PAYANT : 503 exe → 400 → 409 sans confirme_cout
                                     (devis) → plafonds (402, « moteurs3d ») → appel ; {job} reprend sans repayer
  PUT  /reglages {exe}               le chemin de mcp-for-blender (Origin local exigé : un geste de l'écran)
Exe absent ou Blender fermé : 503 traduit (blender.exe_absent / blender.ferme).
"""
from __future__ import annotations

import asyncio
import re
import shutil
import urllib.parse

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from app import i18n
from app.api.routes import _require_localhost
from app.config import settings
from app.services import blender_mcp as BM

router = APIRouter()
CATEGORIE = "moteurs3d"
_HOTES_ECRAN = {"127.0.0.1", "localhost", "::1"}
_ID_PLAN = re.compile(r"^[0-9A-Za-z-]{1,40}$")


def _lang(request: Request) -> str:
    return i18n.langue_requete(request)


def _refus(request: Request, e: BM.RefusBlender) -> HTTPException:
    return HTTPException(e.statut, i18n.msg(e.cle, _lang(request), **e.valeurs))


def _ecran(request: Request) -> None:
    """Un réglage qui choisit un exécutable vient du navigateur de l'app (Origin local), jamais d'un client natif."""
    from app.config import APP_HOSTNAME
    o = request.headers.get("origin") or ""
    try:
        h = (urllib.parse.urlparse(o).hostname or "").lower() if o else ""
    except ValueError:
        h = ""
    if not h or h not in (_HOTES_ECRAN | {APP_HOSTNAME}):
        raise HTTPException(403, i18n.msg("blender.ecran_requis", _lang(request)))


async def _fil(request: Request, fn, *a):
    try:
        return await asyncio.to_thread(fn, *a)
    except BM.RefusBlender as e:
        raise _refus(request, e)


def _regard_public(m: dict) -> dict:
    return {**m, "url": f"/api/blender/regard/{m['id']}"}


@router.get("/etat")
async def etat(request: Request):
    _require_localhost(request)
    return {"exe": BM.etat_exe(), "provenance": len(BM.provenance()),
            "installer": i18n.msg("blender.installer", _lang(request))}


@router.put("/reglages")
async def poser_reglages(request: Request, body: dict):
    _require_localhost(request)
    _ecran(request)
    try:
        return {"exe": BM.poser_exe((body or {}).get("exe"))}
    except BM.RefusBlender as e:
        raise _refus(request, e)


@router.post("/sonder")
async def sonder(request: Request):
    _require_localhost(request)
    return await _fil(request, BM.sonder)


@router.get("/scene")
async def scene(request: Request, q: str = "", n: int = 60):
    _require_localhost(request)
    return await _fil(request, BM.scene, str(q or "")[:120], max(1, min(int(n), 200)))


@router.post("/regarder")
async def regarder(request: Request, body: dict | None = None):
    _require_localhost(request)
    b = body if isinstance(body, dict) else {}
    mode = b.get("mode") or "camera"
    shading = b.get("shading") or None
    if mode not in BM.MODES_LOOK or (shading is not None and shading not in BM.OMBRAGES):
        raise HTTPException(400, i18n.msg("blender.argument", _lang(request), nom="mode"))
    return _regard_public(await _fil(request, BM.regarder, mode, shading))


@router.get("/regard/{rid}")
async def regard(rid: str, request: Request):
    _require_localhost(request)
    if not BM.regard_valide(rid) or not (BM.dossier_regards() / f"{rid}.png").is_file():
        raise HTTPException(404, i18n.msg("blender.regard_introuvable", _lang(request)))
    return FileResponse(BM.dossier_regards() / f"{rid}.png", media_type="image/png",
                        headers={"Cache-Control": "no-store"})


@router.get("/regard/{rid}/meta")
async def regard_meta(rid: str, request: Request):
    _require_localhost(request)
    m = BM.lire_regard(rid)
    if not m:
        raise HTTPException(404, i18n.msg("blender.regard_introuvable", _lang(request)))
    return _regard_public(m)


@router.post("/regard/{rid}/garder")
async def regard_garder(rid: str, request: Request, body: dict | None = None):
    """La capture entre dans la Bibliothèque (source « blender ») ; sa LICENCE dit les assets importés encore dans la
    scène (CC0, CC-BY avec l'attribution, licence Sketchfab…), et la recette les détaille."""
    _require_localhost(request)
    m = BM.lire_regard(rid)
    src = BM.dossier_regards() / f"{rid}.png"
    if not m or not src.is_file():
        raise HTTPException(404, i18n.msg("blender.regard_introuvable", _lang(request)))
    from app.services import library_index as LI
    plan = str(((body or {}) if isinstance(body, dict) else {}).get("plan") or "")
    nom = f"blender_{rid}.png"
    settings.images_path.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, settings.images_path / nom)
    recette = {"outil": "blender_mcp", "mode": m.get("mode"), "shading": m.get("shading"),
               "legende": m.get("legende"), "licences": m.get("licences") or []}
    if _ID_PLAN.match(plan):
        recette["plan"] = plan
    await LI.noter([nom], "blender", recette=recette, relation="blender")
    licence = BM.licence_resumee(m.get("licences") or [])
    if licence:
        from app.services.storage import LibraryAsset, async_session_factory
        async with async_session_factory() as s:
            row = await s.get(LibraryAsset, nom)
            if row is not None:
                row.licence = licence
                await s.commit()
    return {"nom": nom, "licence": licence or LI.licence_defaut(nom, "blender"), "licences": recette["licences"]}


async def _scene_du_plan(shot_id: str, request: Request) -> dict:
    from sqlalchemy import select
    from app.services.scene3d_routes import _dict
    from app.services.storage import Scene3D, Shot, async_session_factory
    if not _ID_PLAN.match(shot_id or ""):
        raise HTTPException(404, i18n.msg("blender.plan_introuvable", _lang(request)))
    async with async_session_factory() as s:
        if await s.get(Shot, shot_id) is None:
            raise HTTPException(404, i18n.msg("blender.plan_introuvable", _lang(request)))
        r = (await s.execute(select(Scene3D).where(Scene3D.shot_id == shot_id)
                             .order_by(Scene3D.updated_at.desc()).limit(1))).scalars().first()
    if r is None:
        raise HTTPException(409, i18n.msg("blender.sans_scene", _lang(request)))
    return _dict(r)


@router.post("/plan/{shot_id}/envoyer")
async def envoyer_plan(shot_id: str, request: Request, body: dict | None = None):
    """Les GABARITS du serveur, nourris par la scène du Plateau du plan : le corps ne choisit que des éléments."""
    _require_localhost(request)
    from app.services import blender_gabarits as G
    b = body if isinstance(body, dict) else {}
    if set(b) - {"elements"}:
        raise HTTPException(400, i18n.msg("blender.argument", _lang(request), nom=", ".join(sorted(set(b) - {"elements"}))[:80]))
    elements = b.get("elements") or ["camera", "eclairage", "blocking"]
    sc = await _scene_du_plan(shot_id, request)
    try:
        params = G.depuis_scene(sc, elements)
    except (G.GabaritRefuse, ValueError) as e:
        raise HTTPException(409, i18n.msg("blender.gabarit", _lang(request), msg=str(e)[:200]))
    r = await _fil(request, BM.executer_gabarit, params)
    return {"elements": params["elements"], "blocking": len(params["blocking"]), "cles": len(params["cles"]),
            "camera": {k: params["camera"][k] for k in ("focale_mm", "largeur", "hauteur")}, "resume": r["resume"],
            "scene": sc["id"]}


@router.post("/nettoyer")
async def nettoyer(request: Request):
    _require_localhost(request)
    from app.services import blender_gabarits as G
    r = await _fil(request, BM.executer_gabarit, G.nettoyage())
    return {"resume": r["resume"]}


@router.post("/assets/chercher")
async def assets_chercher(request: Request, body: dict):
    _require_localhost(request)
    return await _fil(request, BM.chercher, body if isinstance(body, dict) else {})


@router.post("/assets/importer")
async def assets_importer(request: Request, body: dict):
    _require_localhost(request)
    return await _fil(request, BM.importer, body if isinstance(body, dict) else {})


@router.get("/provenance")
async def provenance(request: Request):
    _require_localhost(request)
    return {"imports": list(reversed(BM.provenance()))}


def devis_3d(fournisseur: str) -> dict:
    from app.services import pricing
    return pricing.estimate({"kind": "blender_3d", "engine": fournisseur})


@router.post("/generer")
async def generer(request: Request, body: dict):
    """generate_3d — PAYANT (les clés ou l'abonnement de l'add-on). Tous les refus arrivent AVANT la dépense ; la garde
    des plafonds juste avant l'appel. `job` reprend une génération déjà lancée (le serveur ne repaie pas)."""
    _require_localhost(request)
    from app.api import routes as R
    b = body if isinstance(body, dict) else {}
    if not BM.etat_exe()["trouve"]:
        raise HTTPException(503, i18n.msg("blender.exe_absent", _lang(request), chemin=BM.etat_exe()["chemin"]))
    fournisseur = b.get("fournisseur") or "auto"
    job = str(b.get("job") or "").strip()
    prompt = str(b.get("prompt") or "").strip()
    if fournisseur not in BM.FOURNISSEURS_3D or (not job and not prompt) or len(prompt) > 300:
        raise HTTPException(400, i18n.msg("blender.argument", _lang(request), nom="prompt, fournisseur"))
    if job:
        return await _fil(request, BM.generer_3d, "", fournisseur, str(b.get("nom") or ""), job)
    devis = devis_3d(fournisseur)
    if b.get("confirme_cout") is not True:
        raise HTTPException(409, {"message": i18n.msg("blender.confirme_cout", _lang(request)), "devis": devis})
    await R._plafond({"kind": "blender_3d", "engine": fournisseur}, CATEGORIE, f"blender3d:{fournisseur}")
    r = await _fil(request, BM.generer_3d, prompt, fournisseur, str(b.get("nom") or ""), "")
    return {**r, "devis": devis}
