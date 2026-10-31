# -*- coding: utf-8 -*-
"""Routes de l'écran Texture du 3D Studio — t393 (31/10/2026). Préfixe /api/studio3d/texture.

Gratuit : la liste des modèles d'image et leurs prix, les devis, les références d'un job (liste, fichier), le dépôt
d'une planche de style. PAYANT, deux routes, chacune avec le même ordre de refus, tout AVANT la dépense :
clé (503, la clé nommée) → entrées (400 ; 404 job ou référence inconnus) → `confirme_cout` absent (409, avec le devis)
→ `max_usd` dépassé (409, avec le prix) → plafonds (402 `dz_plafond`, catégorie « moteurs3d ») → dépense.

- `POST /{job}/generer`    {capture (PNG en data URL), modele, resolution, ratio, prompt?, vue, eclairage, style?,
                            confirme_cout, max_usd} : la capture part chez le modèle d'image, l'image rendue devient
                            une référence du job. Synchrone (une image).
- `POST /{job}/retexturer` {reference?, prompt?, resolution, confirme_cout, max_usd, approuver} : retexture Meshy
                            (`asset3d_service.texturer_asset3d`, la passe de POST /api/assets/3d/{job}/texturer) avec la
                            référence choisie et/ou un texte de style ; écrit une NOUVELLE version. Rend un job_id à
                            suivre par GET /api/jobs/{id}. La géométrie non approuvée est refusée (409 `approbation`)
                            sauf `approuver: true`, posé par l'écran dans le dialogue du devis — l'approbation n'est
                            écrite qu'après la garde des plafonds.
- `POST /{job}/generer-lot` (t394, TEXTURE AUTO) {captures: [{capture, pose}], disposition, modele, resolution,
                            prompt?, eclairage, confirme_cout, max_usd} : même ordre de refus, UN devis pour les N
                            vues, UNE garde des plafonds sur ce total, puis N appels ; rend N références avec leur pose.
Gratuit et local (t394) : `POST /{job}/projection` {version, atlas (PNG), disposition?, vues?} — l'atlas peint dans le
navigateur devient la couleur de base d'une NOUVELLE version du GLB (operation « texture_projection »).
Le service : `app.services.studio3d_texture`.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from loguru import logger

from app.config import settings

router = APIRouter()


def _max_usd(body: dict, usd: float) -> None:
    """Le prix accepté à l'écran : un devis qui a bougé depuis (grille éditée) est refusé, rien ne part."""
    m = body.get("max_usd")
    if m is None:
        return
    try:
        m = float(m)
    except (TypeError, ValueError):
        raise HTTPException(400, "max_usd doit être un nombre") from None
    if usd > m + 1e-9:
        raise HTTPException(409, {"code": "max_usd", "message": f"Le devis ({usd:.3f} $) dépasse le prix accepté "
                                                                f"({m:.3f} $) : relis le devis.", "usd": usd})


@router.get("/modeles")
async def texture_modeles():
    """Les modèles d'image de la colonne de gauche (prix, clé, résolutions), les ratios, le prompt par défaut et les
    devis de la retexture Meshy par résolution."""
    from app.services import studio3d_texture as ST
    return ST.modeles()


@router.post("/devis")
async def texture_devis(body: dict = None):
    """Le devis d'une action, gratuit : rien n'est écrit, rien n'est réservé."""
    from app.services import studio3d_texture as ST
    body = body or {}
    action = str(body.get("action") or "")
    if action == "generer":
        modele = str(body.get("modele") or "")
        if modele not in ST.ids_modeles():
            raise HTTPException(400, f"modèle d'image inconnu : {modele[:40]}")
        res = str(body.get("resolution") or "1K").upper()
        if res not in ST.resolutions(modele):
            raise HTTPException(400, f"{modele} ne prend pas la résolution {res}")
        return ST.devis_image(modele, res)
    if action == "retexturer":
        res = str(body.get("resolution") or "2k").lower()
        if res not in ST.RESOLUTIONS_MESHY:
            raise HTTPException(400, f"resolution doit être {', '.join(ST.RESOLUTIONS_MESHY)}")
        return ST.devis_retexture(res)
    if action == "lot":
        modele = str(body.get("modele") or "")
        if modele not in ST.ids_modeles():
            raise HTTPException(400, f"modèle d'image inconnu : {modele[:40]}")
        res = str(body.get("resolution") or "1K").upper()
        if res not in ST.resolutions(modele):
            raise HTTPException(400, f"{modele} ne prend pas la résolution {res}")
        if body.get("vues") not in ST.DISPOSITIONS:
            raise HTTPException(400, f"vues doit être {', '.join(map(str, ST.DISPOSITIONS))}")
        return ST.devis_lot(modele, res, body["vues"])
    raise HTTPException(400, "action doit être « generer », « lot » ou « retexturer »")


@router.get("/{job}/references")
async def texture_references(job: str):
    from app.services import studio3d_texture as ST
    if not ST.job_existe(job):
        raise HTTPException(404, f"modèle 3D inconnu : {Path(job).name}")
    return {"references": await asyncio.to_thread(ST.references, job)}


@router.get("/{job}/reference/{rid}")
async def texture_reference_fichier(job: str, rid: str):
    from app.services import studio3d_texture as ST
    try:
        return FileResponse(ST.chemin_reference(job, rid))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from None


@router.post("/{job}/style")
async def texture_style(job: str, body: dict = None):
    """Une planche de style téléversée (PNG ou JPEG en data URL) devient une référence du job. Gratuit."""
    from app.services import studio3d_texture as ST
    try:
        return {"reference": await asyncio.to_thread(ST.ajouter_style, job, (body or {}).get("image"))}
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from None


@router.post("/{job}/generer")
async def texture_generer(job: str, body: dict = None):
    """La capture du viewport → le modèle d'image choisi → une référence. Payant (catégorie « moteurs3d »)."""
    from app.api import routes as _R
    from app.services import studio3d_texture as ST
    body = body or {}
    modele = str(body.get("modele") or "")
    if modele not in ST.ids_modeles():
        raise HTTPException(400, f"modèle d'image inconnu : {modele[:40]}")
    manque = ST.cle_manquante_image(modele)
    if manque:
        raise HTTPException(503, f"{manque} non configurée (Réglages › Clés d'API) pour {modele}.")
    try:
        r = await asyncio.to_thread(ST.valider_generation, job, body)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from None
    devis = ST.devis_image(r["modele"], r["resolution"])
    if body.get("confirme_cout") is not True:
        raise HTTPException(409, {"code": "confirme_cout", "message": "Image payante : confirme le devis avant de "
                                                                      "générer.", "devis": devis})
    _max_usd(body, devis["usd"])
    await _R._plafond(ST.op_image(r["modele"], r["resolution"]), "moteurs3d", ref=f"studio3d_texture:{Path(job).name}")
    try:
        ref = await ST.generer_reference(job, r)
    except RuntimeError as e:
        raise HTTPException(502, str(e)) from None
    except Exception as e:  # noqa: BLE001 — httpx / fal_client : le fournisseur se nomme, jamais un 500 muet
        logger.exception(f"studio3d texture {job} : {modele} a échoué")
        raise HTTPException(502, f"{modele} : {str(e)[:300]}") from None
    return {"reference": ref, "devis": devis}


@router.post("/{job}/generer-lot")
async def texture_generer_lot(job: str, body: dict = None):
    """t394 — la TEXTURE AUTO : N captures (une par vue d'une disposition) → le modèle d'image → N références qui
    gardent leur pose, que l'écran projette sur l'atlas UV. Payant (catégorie « moteurs3d »), même ordre de refus
    qu'une génération seule, mais UN devis (le total des N vues), UNE garde des plafonds sur ce total, puis les N
    appels (quatre à la fois). Une vue qui échoue n'annule pas les autres : elle revient dans `erreurs` ; toutes
    échouées → 502."""
    from app.api import routes as _R
    from app.services import studio3d_texture as ST
    body = body or {}
    modele = str(body.get("modele") or "")
    if modele not in ST.ids_modeles():
        raise HTTPException(400, f"modèle d'image inconnu : {modele[:40]}")
    manque = ST.cle_manquante_image(modele)
    if manque:
        raise HTTPException(503, f"{manque} non configurée (Réglages › Clés d'API) pour {modele}.")
    try:
        lots = await asyncio.to_thread(ST.valider_lot, job, body)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from None
    devis = ST.devis_lot(modele, lots[0]["resolution"], len(lots))
    if body.get("confirme_cout") is not True:
        raise HTTPException(409, {"code": "confirme_cout", "message": "Texture auto payante : confirme le devis "
                                                                      "(toutes les vues) avant de lancer.",
                                  "devis": devis})
    _max_usd(body, devis["usd"])
    await _R._plafond(ST.op_lot(modele, lots[0]["resolution"], len(lots)), "moteurs3d",
                      ref=f"studio3d_texture:{Path(job).name}")
    porte = asyncio.Semaphore(4)

    async def une(r):
        async with porte:
            try:
                return await ST.generer_reference(job, r)
            except Exception as e:  # noqa: BLE001 — une vue ratée n'emporte pas le lot ; le fournisseur se nomme
                logger.warning(f"studio3d texture auto {job} : vue {r['meta']['index'] + 1} : {e}")
                return {"erreur": f"{modele} : {str(e)[:300]}", "index": r["meta"]["index"]}

    rendus = await asyncio.gather(*(une(r) for r in lots))
    refs = [x for x in rendus if "erreur" not in x]
    erreurs = [x for x in rendus if "erreur" in x]
    if not refs:
        raise HTTPException(502, erreurs[0]["erreur"] if erreurs else f"{modele} n'a rendu aucune image")
    return {"references": refs, "erreurs": erreurs, "devis": devis, "lot": lots[0]["meta"]["lot"]}


@router.post("/{job}/projection")
async def texture_projection(job: str, body: dict = None):
    """t394 — l'atlas peint (PNG en data URL) devient la couleur de base d'une NOUVELLE version du modèle (GLB
    réécrit en Python pur, `mesh_edit.ecrire_version`, operation « texture_projection », `depuis` gardé). Gratuit et
    local. {version, atlas, disposition?, vues?}"""
    from app.services import mesh_edit, mesh_sources, studio3d_ouvert as SO, studio3d_texture as ST
    body = body or {}
    nom = Path(str(job)).name
    if not nom or nom != str(job):
        raise HTTPException(400, f"job « {str(job)[:40]} » : nom de dossier invalide")
    try:
        fiche = await asyncio.to_thread(SO.fiche, nom, body.get("version"))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from None
    except (ValueError, TypeError) as e:
        raise HTTPException(400, str(e)) from None
    try:
        png, lg, ht = ST.decoder_atlas(body.get("atlas"))
    except ValueError as e:
        raise HTTPException(400, str(e)) from None
    etape = next(v for v in fiche["versions"] if v["version"] == fiche["version"])
    data = (mesh_sources._jobs_dir() / nom / etape["file"]).read_bytes()
    try:
        sortie, detail = await asyncio.to_thread(ST.ecrire_texture_projetee, data, png)
    except ValueError as e:
        raise HTTPException(400, str(e)) from None
    vues = body.get("vues") if isinstance(body.get("vues"), int) else None
    fiche_v = await asyncio.to_thread(
        mesh_edit.ecrire_version, nom, sortie, operation="texture_projection",
        detail={"depuis": {"version": fiche["version"], "fichier": etape["file"]}, "atlas": [lg, ht],
                "disposition": str(body.get("disposition") or "")[:40], "vues": vues, **detail})
    return {"job": nom, "version": fiche_v.get("version"), "fichier": fiche_v.get("file"), "atlas": [lg, ht], **detail}


@router.post("/{job}/retexturer")
async def texture_retexturer(job: str, background_tasks: BackgroundTasks, body: dict = None):
    """Retexture IA chez Meshy avec la référence choisie et/ou un texte de style ; écrit une nouvelle version."""
    from datetime import datetime as _dt
    from sqlalchemy import select as _select
    from app.api import routes as _R
    from app.models.schemas import JobStatus
    from app.services import asset3d_service as A3, studio3d_texture as ST
    from app.services.storage import JobRecord, async_session_factory
    body = body or {}
    manque = ST.cle_manquante_meshy()
    if manque:
        raise HTTPException(503, f"{manque} non configurée (Réglages › Clés d'API) : la retexture passe par ton compte "
                                 "Meshy, le maillage voyage par le stockage fal.")
    try:
        r = await asyncio.to_thread(ST.valider_retexture, job, body)
        await asyncio.to_thread(A3.read_manifest, job)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from None
    short = Path(job).name
    async with async_session_factory() as s:
        en_cours = (await s.execute(_select(JobRecord).where(
            JobRecord.provider == "asset3d", JobRecord.image_filename == f"asset3d_{short}",
            JobRecord.status.notin_(["done", "failed"])))).scalars().first()
    if en_cours is not None:
        raise HTTPException(409, {"code": "en_cours", "message": "Une passe de finition de ce maillage est déjà en "
                                                                 "cours : attends qu'elle finisse."})
    devis = ST.devis_retexture(r["resolution"])
    if body.get("confirme_cout") is not True:
        raise HTTPException(409, {"code": "confirme_cout", "message": "Retexture payante (crédits Meshy) : confirme "
                                                                      "le devis avant de lancer.", "devis": devis})
    approuve = bool(A3.approval(job).get("approved"))
    if not approuve and body.get("approuver") is not True:
        raise HTTPException(409, {"code": "approbation", "message": "Géométrie non approuvée : la retexture la "
                                                                    "valide (approuver: true).", "devis": devis})
    _max_usd(body, devis["usd"])
    plaf = await _R._plafond(ST.op_retexture(r["resolution"]), "moteurs3d", ref=f"asset3d:{short}")
    if not approuve:
        await asyncio.to_thread(A3.approve, job, True, "3D Studio › Texture : approuvée avec le devis de retexture")
    job_id = str(uuid4())
    async with async_session_factory() as s:
        s.add(JobRecord(id=job_id, status=JobStatus.GENERATING_VIDEO.value, progress=10,
                        title=f"3D · retexture Meshy {r['resolution']} (Texture)", image_filename=f"asset3d_{short}",
                        provider="asset3d", current_step="Texturage Meshy"))
        await s.commit()

    async def on_step(label, pct):
        async with async_session_factory() as s2:
            jr2 = await s2.get(JobRecord, job_id)
            if jr2 is not None:
                jr2.current_step, jr2.progress = label, int(pct)
                await s2.commit()

    async def _run():
        try:
            res = await A3.texturer_asset3d(job, resolution=r["resolution"], pbr=True, style_prompt=r["prompt"] or None,
                                            vues_style=[r["chemin"]] if r["chemin"] else None, on_step=on_step)
            try:
                from app.services import plafonds as _PLAF
                await _PLAF.rattacher_meshy(plaf["lignes"], res.get("meshy_task"))
            except Exception as _e:  # noqa: BLE001 — la comptabilité ne fait jamais échouer une retexture réussie
                logger.warning(f"plafonds : réel Meshy non rattaché ({_e})")
            async with async_session_factory() as s:
                jr = await s.get(JobRecord, job_id)
                if jr is not None:
                    jr.status, jr.progress, jr.current_step = JobStatus.DONE.value, 100, "Complete"
                    jr.final_video_path = str(settings.outputs_path / "assets3d" / short / res["file"])
                    jr.completed_at = _dt.utcnow()
                    jr.cost_meta = json.dumps({"job": short, "texturier": "meshy", "meshy_task": res.get("meshy_task"),
                                               "version": res["version"], "texture_mode": res["texture_mode"],
                                               "reference": r["reference"], "ecran": "texture"})
                    await s.commit()
        except Exception as e:  # noqa: BLE001
            logger.exception(f"studio3d texture : retexture {job_id} échouée : {e}")
            async with async_session_factory() as s:
                jr = await s.get(JobRecord, job_id)
                if jr is not None:
                    jr.status, jr.error, jr.current_step = JobStatus.FAILED.value, str(e), "Failed"
                    await s.commit()

    background_tasks.add_task(_run)
    return {"job_id": job_id, "status": "queued", "source_job": short, "devis": devis}
