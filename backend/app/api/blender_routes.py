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
  t332 (A2), l'ALLER-RETOUR Plateau ↔ Blender (détail plus bas, au-dessus de `aller`) :
  POST /plan/{shot}/aller            caméra + focale, clés, maquette GLB de la scène (élément « maquette »)
  POST /plan/{shot}/reprendre {camera?}  lit caméras et objets DZ_, copie .blend, vignette → Bibliothèque ; propose
  GET  /plan/{shot}/retours · GET /retour/{rid}/blend · GET /retour/{rid}/vignette
  POST /plan/{shot}/retour/{rid}/appliquer {camera?, confirmer?}  avant/après ; écrit au Plateau avec confirmer:true
Exe absent ou Blender fermé : 503 traduit (blender.exe_absent / blender.ferme).
"""
from __future__ import annotations

import asyncio
import re
import shutil
import urllib.parse
from pathlib import Path

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
    return await _envoyer(request, shot_id, sc, elements)


async def _envoyer(request: Request, shot_id: str, sc: dict, elements) -> dict:
    from app.services import blender_gabarits as G
    glb = None
    if isinstance(elements, list) and "maquette" in elements:
        glb = await _composer_maquette(request, shot_id, sc)
    try:
        params = G.depuis_scene(sc, elements, glb=glb)
    except (G.GabaritRefuse, ValueError) as e:
        raise HTTPException(409, i18n.msg("blender.gabarit", _lang(request), msg=str(e)[:200]))
    r = await _fil(request, BM.executer_gabarit, params)
    crees = (r["resume"] or {}).get("crees") or []
    return {"elements": params["elements"], "blocking": len(params["blocking"]), "cles": len(params["cles"]),
            "maquette": sum(1 for n in crees if isinstance(n, str) and n.startswith("DZ_Maquette_")),
            "camera": {k: params["camera"][k] for k in ("focale_mm", "largeur", "hauteur")}, "resume": r["resume"],
            "scene": sc["id"]}


# ── t332 (A2) : l'ALLER-RETOUR Plateau ↔ Blender ──────────────────────────────────────────────────────────────────
# Aller   POST /plan/{id}/aller            caméra + focale, clés (si le plan bouge) et la MAQUETTE : le GLB de la scène
#                                          (maillages de la bible et des jobs 3D, proxys ; faisceaux exclus) composé ICI
#                                          dans outputs/blender/plans/<plan>/maquette.glb, importé par le gabarit
# Retour  POST /plan/{id}/reprendre        le gabarit de RETOUR lit les caméras et les objets DZ_, enregistre une COPIE
#                                          .blend (le fichier de l'utilisateur n'est ni renommé ni écrasé), une vignette
#                                          vue caméra entre dans la Bibliothèque (source « blender ») avec la provenance
#                                          (plan, .blend, caméras, licences) ; rien n'est écrit au Plateau
#         GET  /plan/{id}/retours          les retours du plan, le plus récent d'abord (la fiche du plan les montre)
#         GET  /retour/{rid}/blend         le .blend ; GET /retour/{rid}/vignette
#         POST /plan/{id}/retour/{rid}/appliquer {camera?, confirmer?}  avant/après ; écrit la caméra et les keyframes
#                                          au Plateau SEULEMENT avec confirmer:true (comme /scenes3d/{id}/vers-plan)
MAX_RETOURS = 10


def _dossier_plans() -> Path:
    return BM.dossier_plans()


async def _composer_maquette(request: Request, shot_id: str, sc: dict) -> str | None:
    """Le GLB de la scène du plan (sans faisceau) → outputs/blender/plans/<plan>/maquette.glb ; None si rien à poser."""
    from app.services import previs_palette as PP
    from app.services import scene3d_glb as SG
    from app.services.scene3d_routes import _lire_maillage
    solides = [i for i in sc.get("instances") or [] if isinstance(i, dict) and not PP.est_faisceau(i)]
    if not solides:
        return None
    try:
        glb, _rap = await asyncio.to_thread(SG.composer, solides, _lire_maillage)
    except ValueError as e:
        raise HTTPException(409, i18n.msg("blender.gabarit", _lang(request), msg=str(e)[:200]))
    except RuntimeError as e:
        raise HTTPException(503, i18n.msg("blender.gabarit", _lang(request), msg=str(e)[:200]))
    d = _dossier_plans() / shot_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "maquette.glb").write_bytes(glb)
    return str((d / "maquette.glb").resolve())


@router.post("/plan/{shot_id}/aller")
async def aller(shot_id: str, request: Request, body: dict | None = None):
    """« Envoyer le plan vers Blender » : caméra, focale, clés (deux keyframes au moins) et maquette GLB. Gratuit."""
    _require_localhost(request)
    if isinstance(body, dict) and body:
        raise HTTPException(400, i18n.msg("blender.argument", _lang(request), nom=", ".join(sorted(body))[:80]))
    sc = await _scene_du_plan(shot_id, request)
    elements = ["camera"]
    if len(sc.get("keyframes") or []) >= 2:
        elements.append("cles")
    from app.services import previs_palette as PP
    if any(isinstance(i, dict) and not PP.est_faisceau(i) for i in sc.get("instances") or []):
        elements.append("maquette")
    return await _envoyer(request, shot_id, sc, elements)


def _retour_valide(rid: str) -> bool:
    return BM.regard_valide(rid)


def _lire_retour(shot_id: str, rid: str) -> dict | None:
    return BM.lire_retour(shot_id, rid)


def _retour_public(m: dict) -> dict:
    out = {k: m.get(k) for k in ("id", "plan", "scene", "date", "camera_nom", "cameras", "objets", "rendu", "version",
                                 "fichier", "licences", "proposition", "proposition_erreur", "bibliotheque")}
    out["blend_url"] = f"/api/blender/retour/{m['id']}/blend"
    out["blend_nom"] = m.get("blend_nom")
    out["vignette_url"] = f"/api/blender/retour/{m['id']}/vignette" if m.get("vignette") else None
    return out


def _chercher_retour(rid: str) -> tuple[dict, Path] | None:
    if not _retour_valide(rid):
        return None
    for d in _dossier_plans().glob(f"*/{rid}"):
        m = _lire_retour(d.parent.name, rid)
        if m:
            return m, d
    return None


@router.post("/plan/{shot_id}/reprendre")
async def reprendre(shot_id: str, request: Request, body: dict | None = None):
    """« Reprendre depuis Blender » : lit, enregistre une copie .blend et PROPOSE (aucune écriture au Plateau)."""
    _require_localhost(request)
    import json
    import uuid
    from datetime import datetime
    from app.services import blender_gabarits as G
    b = body if isinstance(body, dict) else {}
    if set(b) - {"camera"} or ("camera" in b and not isinstance(b["camera"], str)):
        raise HTTPException(400, i18n.msg("blender.argument", _lang(request), nom="camera"))
    sc = await _scene_du_plan(shot_id, request)
    rid = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
    dossier = _dossier_plans() / shot_id / rid
    dossier.mkdir(parents=True, exist_ok=True)
    blend_nom = f"blender_plan_{rid}.blend"
    blend = dossier / blend_nom
    try:
        r = await _fil(request, BM.reprendre, G.retour(str(blend.resolve())))
        lu = G.lire_retour(r["resume"])
    except G.GabaritRefuse as e:
        shutil.rmtree(dossier, ignore_errors=True)
        raise HTTPException(502, i18n.msg("blender.retour_illisible", _lang(request), msg=str(e)[:200]))
    except HTTPException:
        shutil.rmtree(dossier, ignore_errors=True)
        raise
    tete = blend.read_bytes()[:7] if blend.is_file() else b""
    if not lu["blend"] or (tete[:7] != b"BLENDER" and tete[:4] != b"\x28\xb5\x2f\xfd"):
        shutil.rmtree(dossier, ignore_errors=True)
        raise HTTPException(502, i18n.msg("blender.retour_sans_blend", _lang(request)))
    prop, prop_err = None, None
    try:
        prop = G.vers_plateau(lu, sc, (b.get("camera") or None))
    except (G.GabaritRefuse, ValueError) as e:
        prop_err = str(e)[:200]
    m = {"id": rid, "plan": shot_id, "scene": sc["id"], "date": datetime.now().isoformat(timespec="seconds"),
         "camera_nom": (prop or {}).get("camera_nom"), "cameras": [
             {"nom": c["nom"], "active": c["active"], "perspective": c["perspective"], "lens": c["lens"],
              "cles": len(c["cles"])} for c in lu["cameras"]],
         "objets": lu["objets"], "rendu": lu["rendu"], "version": lu["version"], "fichier": lu["fichier"],
         "licences": r.get("licences") or [], "proposition": prop, "proposition_erreur": prop_err,
         "blend_nom": blend_nom, "vignette": None, "bibliotheque": None}
    (dossier / "retour.json").write_text(json.dumps({**m, "retour": lu}, ensure_ascii=False), encoding="utf-8")
    if r.get("image"):
        (dossier / "vignette.png").write_bytes(r["image"])
        m["vignette"] = "vignette.png"
        m["bibliotheque"] = await _ranger(rid, shot_id, sc["id"], blend_nom, m)
    (dossier / "retour.json").write_text(json.dumps({**m, "retour": lu}, ensure_ascii=False), encoding="utf-8")
    for vieux in sorted((p for p in dossier.parent.iterdir() if p.is_dir() and _retour_valide(p.name)),
                        reverse=True)[MAX_RETOURS:]:
        shutil.rmtree(vieux, ignore_errors=True)
    return _retour_public(m)


async def _ranger(rid: str, shot_id: str, scene_id: str, blend_nom: str, m: dict) -> str | None:
    """La vignette du retour entre dans la Bibliothèque (source « blender ») : sa MÈRE est le .blend, sa recette dit la
    provenance (plan, scène du Plateau, fichier et version de Blender, caméras, objets DZ_, licences des imports)."""
    from app.services import library_index as LI
    nom = f"blender_{rid}.png"
    settings.images_path.mkdir(parents=True, exist_ok=True)
    shutil.copy2(_dossier_plans() / shot_id / rid / "vignette.png", settings.images_path / nom)
    recette = {"outil": "blender_mcp", "operation": "retour_plateau", "plan": shot_id, "scene": scene_id,
               "blend": blend_nom, "blender": m.get("version"), "fichier_blender": m.get("fichier"),
               "cameras": [c["nom"] for c in m["cameras"]], "objets": len(m["objets"]),
               "licences": m.get("licences") or []}
    await LI.noter([nom], "blender", recette=recette, parent=blend_nom, relation="blender")
    licence = BM.licence_resumee(m.get("licences") or [])
    if licence:
        from app.services.storage import LibraryAsset, async_session_factory
        async with async_session_factory() as s:
            row = await s.get(LibraryAsset, nom)
            if row is not None:
                row.licence = licence
                await s.commit()
    return nom


@router.get("/plan/{shot_id}/retours")
async def retours(shot_id: str, request: Request):
    _require_localhost(request)
    if not _ID_PLAN.match(shot_id or ""):
        raise HTTPException(404, i18n.msg("blender.plan_introuvable", _lang(request)))
    d = _dossier_plans() / shot_id
    out = []
    if d.is_dir():
        for p in sorted((p for p in d.iterdir() if p.is_dir() and _retour_valide(p.name)), reverse=True):
            m = _lire_retour(shot_id, p.name)
            if m:
                out.append(_retour_public(m))
    return {"retours": out}


@router.get("/retour/{rid}/blend")
async def retour_blend(rid: str, request: Request):
    _require_localhost(request)
    t = _chercher_retour(rid)
    if t is None or not (t[1] / t[0]["blend_nom"]).is_file():
        raise HTTPException(404, i18n.msg("blender.retour_introuvable", _lang(request)))
    return FileResponse(t[1] / t[0]["blend_nom"], media_type="application/x-blender", filename=t[0]["blend_nom"])


@router.get("/retour/{rid}/vignette")
async def retour_vignette(rid: str, request: Request):
    _require_localhost(request)
    t = _chercher_retour(rid)
    if t is None or not (t[1] / "vignette.png").is_file():
        raise HTTPException(404, i18n.msg("blender.retour_introuvable", _lang(request)))
    return FileResponse(t[1] / "vignette.png", media_type="image/png", headers={"Cache-Control": "no-store"})


@router.post("/plan/{shot_id}/retour/{rid}/appliquer")
async def appliquer(shot_id: str, rid: str, request: Request, body: dict | None = None):
    """La caméra (position, cible, focale) et les keyframes relues dans Blender → la scène du Plateau du plan.
    Sans `confirmer: true` : l'avant/après seulement (la scène du Plateau peut avoir bougé depuis le retour : la
    proposition est RECALCULÉE sur la scène d'aujourd'hui)."""
    _require_localhost(request)
    import json
    from datetime import datetime
    from app.services import blender_gabarits as G
    b = body if isinstance(body, dict) else {}
    if set(b) - {"camera", "confirmer"} or ("camera" in b and not isinstance(b["camera"], str)):
        raise HTTPException(400, i18n.msg("blender.argument", _lang(request), nom="camera, confirmer"))
    m = _lire_retour(shot_id, rid)
    if not m or not isinstance(m.get("retour"), dict):
        raise HTTPException(404, i18n.msg("blender.retour_introuvable", _lang(request)))
    sc = await _scene_du_plan(shot_id, request)
    try:
        prop = G.vers_plateau(m["retour"], sc, b.get("camera") or None)
    except (G.GabaritRefuse, ValueError) as e:
        raise HTTPException(409, i18n.msg("blender.retour_illisible", _lang(request), msg=str(e)[:200]))
    if b.get("confirmer") is not True:
        return {"applique": False, "proposition": prop}
    from app.services.storage import Scene3D, async_session_factory
    async with async_session_factory() as s:
        r = await s.get(Scene3D, sc["id"])
        if r is None:
            raise HTTPException(409, i18n.msg("blender.sans_scene", _lang(request)))
        r.camera = json.dumps(prop["camera"])
        r.keyframes = json.dumps(prop["keyframes"])
        r.updated_at = datetime.utcnow()
        await s.commit()
    return {"applique": True, "proposition": prop, "scene": sc["id"]}


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
