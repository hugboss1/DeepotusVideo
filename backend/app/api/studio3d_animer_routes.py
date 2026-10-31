# -*- coding: utf-8 -*-
"""t398 + t399 (31/10/2026) — /api/studio3d/animer : l'écran ANIMER du 3D Studio à écrans.

Boucle locale SEULEMENT (`routes._require_localhost`) ; les deux routes qui dépensent ont aussi
`_require_local_depense`.
- `GET    /catalogue`             q, categorie, sous_categorie, page, par_page, vue (tous | favoris | collection),
                                  collection : une page du catalogue Meshy (680 entrées) ; gratuit.
- `GET    /favoris`, `POST /favoris` {id, favori}                        : les favoris de l'utilisateur.
- `GET    /collections`, `POST /collections` {nom, ids} (création) ou {id, nom?, ajouter?, retirer?},
  `DELETE /collections/{cid}`                                           : les collections de l'utilisateur.
- `GET    /etat`                  job : rig Meshy présent, clé Meshy, modes et bornes du texte → mouvement ; gratuit.
- `GET    /appliquer/devis`       job, action_id : la voie (animation seule sur le rig Meshy, ou rig + action par
                                  `POST /assets/3d/{job}/rig`) et son devis ; gratuit.
- `POST   /appliquer`             {job, action_id, confirme_cout} : PAYANT (3 crédits). Ordre des refus, tous AVANT la
                                  dépense : clé Meshy (503) → job, rig Meshy, identifiant (400/404) → `confirme_cout`
                                  absent (409, avec le devis) → plafonds (402, « moteurs3d »). Tâche de fond.
- `POST   /texte`                 {job, version, prompt, duree, mode, nom, confirme_cout} : PAYANT (swift : 3 crédits).
                                  Clé (503) → saisie (400 : prompt vide ou trop long, durée hors de 2 à 10 s ou hors
                                  pas de 0,5, mode prime = FBX illisible, version sans squelette) → `confirme_cout`
                                  (409 + devis) → plafonds (402) → tâche de fond : BVH rangé, reciblé, version de plus.
                                  t405 : `modele` « hy-motion » | « hy-motion-fast » (fal, 0,08 / 0,06 $) : modèle
                                  (400) → `licence_acceptee: true` (400) → clé fal (503) → saisie (400 : durée 0,5 à
                                  12 s, guidance 1 à 10) → job, squelette (400/404) → `confirme_cout` (409 + devis) →
                                  plafonds (402) → tâche de fond : dict → BVH → reciblé, version de plus.
- `GET    /licence`, `POST /licence` {acceptee} : la case « J'ai lu la licence HY-Motion » de l'utilisateur (t405).
- `GET    /tache`                 job, tache : l'état d'une tâche de fond (prepare → genere → recible → fini | echec).
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger

from app.config import settings
from app.services import animations_catalogue as CAT
from app.services import studio3d_animer as SA

router = APIRouter()
CATEGORIE = "moteurs3d"
_TACHES: dict[str, asyncio.Task] = {}


def _local(request: Request) -> None:
    from app.api.routes import _require_localhost
    _require_localhost(request)


def _depense_locale(request: Request) -> None:
    from app.api.routes import _require_local_depense
    _require_local_depense(request)


def _cle_meshy() -> bool:
    from app.services import meshy_service as MS
    return MS.mock_enabled() or bool((settings.MESHY_API_KEY or "").strip())


def _cle_fal() -> bool:
    return bool((settings.FAL_KEY or "").strip())


def _job_nu(job) -> str:
    j = str(job or "")
    if not j or Path(j).name != j or j in (".", ".."):
        raise HTTPException(400, "job : le nom du dossier du job 3D est attendu")
    from app.services import mesh_report
    if not mesh_report.job_dir(j).is_dir():
        raise HTTPException(404, f"job 3D introuvable : {j}")
    return j


# ───────────────────────────── catalogue, favoris, collections ─────────────────────────────

@router.get("/catalogue", dependencies=[Depends(_local)])
async def catalogue(q: str = "", categorie: str = "", sous_categorie: str = "", page: int = 1,
                    par_page: int = CAT.PAR_PAGE, vue: str = "tous", collection: str = ""):
    fav = SA.favoris()
    ids = None
    if vue == "favoris":
        ids = list(reversed(fav))                   # le dernier marqué en tête
    elif vue == "collection":
        c = next((x for x in SA.collections() if x.get("id") == collection), None)
        if c is None:
            raise HTTPException(404, "collection inconnue")
        ids = c.get("ids") or []
    elif vue != "tous":
        raise HTTPException(400, "vue : « tous », « favoris » ou « collection »")
    r = CAT.chercher(q, categorie, sous_categorie, page, par_page, ids=ids)
    lot = set(fav)
    for e in r["entrees"]:
        e["favori"] = e["id"] in lot
    return {**r, "categories": CAT.categories(), "favoris": len(fav), "nombre": len(CAT.charger())}


@router.get("/favoris", dependencies=[Depends(_local)])
async def lire_favoris():
    return {"favoris": SA.favoris()}


@router.post("/favoris", dependencies=[Depends(_local)])
async def poser_favori(body: dict):
    body = body or {}
    try:
        return {"favoris": SA.marquer_favori(body.get("id"), body.get("favori", True) is not False)}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/collections", dependencies=[Depends(_local)])
async def lire_collections():
    return {"collections": SA.collections()}


@router.post("/collections", dependencies=[Depends(_local)])
async def ecrire_collection(body: dict):
    """Sans `id` : crée {nom, ids?}. Avec `id` : renomme, ajoute, retire."""
    body = body or {}
    for k in ("ids", "ajouter", "retirer"):
        if body.get(k) is not None and not isinstance(body.get(k), list):
            raise HTTPException(400, f"{k} : une liste d'identifiants est attendue")
    try:
        if body.get("id"):
            c = SA.modifier_collection(str(body["id"]), nom=body.get("nom"), ajouter=body.get("ajouter") or [],
                                       retirer=body.get("retirer") or [])
        else:
            c = SA.creer_collection(body.get("nom"), body.get("ids") or [])
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"collection": c, "collections": SA.collections()}


@router.delete("/collections/{cid}", dependencies=[Depends(_local)])
async def supprimer_collection(cid: str):
    try:
        SA.supprimer_collection(cid)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    return {"collections": SA.collections()}


# ───────────────────────────── état de l'écran ─────────────────────────────

@router.get("/etat", dependencies=[Depends(_local)])
async def etat(job: str = ""):
    out = {"meshy": _cle_meshy(), "fal": _cle_fal(), "texte": SA.etat_texte(), "rig_meshy": False,
           "devis_animation": SA.devis_credits(SA.CREDITS_ANIMATION)}
    if job:
        j = _job_nu(job)
        out["rig_meshy"] = bool(SA.rig_meshy(j))
    return out


@router.get("/licence", dependencies=[Depends(_local)])
async def lire_licence():
    return {"licence": SA.etat_hy()["licence"]}


@router.post("/licence", dependencies=[Depends(_local)])
async def poser_licence(body: dict):
    """La case « J'ai lu la licence et je l'accepte pour mon usage » de HY-Motion : {acceptee: true | false}."""
    v = (body or {}).get("acceptee")
    if not isinstance(v, bool):
        raise HTTPException(400, "acceptee : true ou false attendu")
    SA.accepter_licence_hy(v)
    return {"licence": SA.etat_hy()["licence"]}


@router.post("/physique/{job}", dependencies=[Depends(_local)])
async def garder_physique(job: str, body: dict):
    """t405 : les réglages physiques de l'aperçu (os à ressort) gardés AVEC le modèle (`physics-config.json` du job) ;
    l'Exporter les embarque dans le paquet three.js. Gratuit. 400 corps invalide, 404 job inconnu."""
    import json as _json
    from app.services import mesh_sources
    nom = Path(str(job)).name
    if not nom or nom != job:
        raise HTTPException(400, f"job « {job} » : nom de dossier invalide")
    d = mesh_sources._jobs_dir() / nom
    if not d.is_dir():
        raise HTTPException(404, f"modèle 3D inconnu : {nom}")
    if not isinstance(body, dict) or not isinstance(body.get("reglages"), dict):
        raise HTTPException(400, "physique : un objet avec « reglages » est attendu")
    texte = _json.dumps(body, ensure_ascii=False, indent=1)
    if len(texte) > 64 * 1024:
        raise HTTPException(400, "physique : 64 Ko au plus")
    (d / "physics-config.json").write_text(texte, encoding="utf-8")
    return {"job": nom, "fichier": "physics-config.json", "octets": len(texte)}


# ───────────────────────────── appliquer une animation du catalogue ─────────────────────────────

def _action(v) -> int:
    if isinstance(v, bool) or not isinstance(v, int):
        raise HTTPException(400, "action_id : un entier du catalogue Meshy est attendu")
    e = CAT.par_id(v)
    if e is None:
        raise HTTPException(400, f"animation {v} absente du catalogue Meshy")
    if not e["applicable"]:
        raise HTTPException(400, f"« {e['nom']} » est livrée avec le rig : elle ne s'applique pas (0 à 696)")
    return v


@router.get("/appliquer/devis", dependencies=[Depends(_local)])
async def appliquer_devis(job: str, action_id: int):
    j = _job_nu(job)
    a = _action(action_id)
    if SA.rig_meshy(j):
        return {"voie": "animation", "credits": SA.CREDITS_ANIMATION, "devis": SA.devis_credits(SA.CREDITS_ANIMATION),
                "action": CAT.par_id(a), "meshy": _cle_meshy()}
    # pas de rig Meshy : la seule voie est la route du rig (re-rig + l'action), son devis à elle
    from app.services import asset3d_rig as RIG
    try:
        d = RIG.devis(j, [a])
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    return {"voie": "rig", "devis": d, "action": CAT.par_id(a), "meshy": _cle_meshy()}


async def _travail_animation(job: str, tache: str, action_id: int, lignes: list):
    async def suivre(e):
        SA.poser_etat(job, tache, **e)
        if e.get("meshy_task"):
            try:
                from app.services import plafonds as _PLAF
                await _PLAF.rattacher_meshy(lignes, e["meshy_task"])
            except Exception as _e:  # noqa: BLE001 — la comptabilité ne fait jamais échouer le travail
                logger.warning(f"plafonds : réel Meshy de l'animation non rattaché ({_e})")
    try:
        r = await SA.appliquer_animation(job, action_id, on_etat=suivre)
        SA.poser_etat(job, tache, etat="fini", **r)
    except Exception as e:                              # noqa: BLE001 — l'état DIT l'échec
        logger.warning(f"animer {tache} : {type(e).__name__}")
        SA.poser_etat(job, tache, etat="echec", erreur=str(e)[:300])
    finally:
        _TACHES.pop(tache, None)


@router.post("/appliquer", dependencies=[Depends(_local), Depends(_depense_locale)])
async def appliquer(body: dict):
    from app.api import routes as R
    body = body or {}
    if not _cle_meshy():
        raise HTTPException(503, "Clé Meshy absente — Réglages › Clés : l'animation passe par ton compte Meshy.")
    j = _job_nu(body.get("job"))
    a = _action(body.get("action_id"))
    if not SA.rig_meshy(j):
        raise HTTPException(400, "Ce modèle n'a pas de rig Meshy : rigge-le dans l'écran Rig (l'action peut y être "
                                 "jointe), puis reviens.")
    devis = SA.devis_credits(SA.CREDITS_ANIMATION)
    if body.get("confirme_cout") is not True:
        raise HTTPException(409, {"message": "Animation Meshy payante : confirme le coût avant de lancer.",
                                  "devis": devis})
    tache = uuid4().hex[:12]
    plaf = await R._plafond({"kind": "meshy", "credits": SA.CREDITS_ANIMATION}, CATEGORIE, f"meshy-anim:{tache}")
    SA.poser_etat(j, tache, etat="prepare", quoi="animation", action_id=a, devis=devis)
    _TACHES[tache] = asyncio.create_task(_travail_animation(j, tache, a, plaf.get("lignes") or []))
    return {"ok": True, "tache": tache, "devis": devis, "etat": "prepare"}


# ───────────────────────────── texte → mouvement ─────────────────────────────

async def _travail_texte(job: str, tache: str, version: int, entree: dict, lignes: list):
    async def suivre(e):
        SA.poser_etat(job, tache, **e)
        if e.get("etat") == "genere" and e.get("meshy_task"):
            try:
                from app.services import plafonds as _PLAF
                await _PLAF.rattacher_meshy(lignes, e["meshy_task"])
            except Exception as _e:  # noqa: BLE001
                logger.warning(f"plafonds : réel Meshy du mouvement non rattaché ({_e})")
    try:
        r = await SA.texte_vers_mouvement(job, version, entree, on_etat=suivre)
        SA.poser_etat(job, tache, etat="fini", **r)
    except Exception as e:                              # noqa: BLE001
        logger.warning(f"texte → mouvement {tache} : {type(e).__name__}")
        SA.poser_etat(job, tache, etat="echec", erreur=str(e)[:300])
    finally:
        _TACHES.pop(tache, None)


async def _travail_hy(job: str, tache: str, version: int, entree: dict):
    async def suivre(e):
        SA.poser_etat(job, tache, **e)
    try:
        r = await SA.hy_motion_vers_mouvement(job, version, entree, on_etat=suivre)
        SA.poser_etat(job, tache, etat="fini", **r)
    except Exception as e:                              # noqa: BLE001
        logger.warning(f"HY-Motion {tache} : {type(e).__name__}")
        SA.poser_etat(job, tache, etat="echec", erreur=str(e)[:300])
    finally:
        _TACHES.pop(tache, None)


def _version_squelettee(body: dict, quoi: str):
    """(job, version) d'une version qui porte un squelette, ou 400/404 — AVANT toute dépense."""
    from app.api import routes as R
    from app.services import mesh_edit
    version = body.get("version", 1)
    # le nom NU d'abord : `_etabli_glb_cible` aplatit « ../perso » en « perso » — ici un chemin est une saisie fausse
    j, data, _depuis = R._etabli_glb_cible(_job_nu(body.get("job")), version, quoi)
    try:
        doc, _ = mesh_edit.lire_glb(data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not doc.get("skins"):
        raise HTTPException(400, "Ce modèle n'a pas de squelette : rigge-le d'abord dans l'écran Rig.")
    return j, version


@router.post("/texte", dependencies=[Depends(_local), Depends(_depense_locale)])
async def texte(body: dict):
    """La voie PAYANTE du texte → mouvement (Meshy, ou HY-Motion par fal). Tous les refus arrivent AVANT la dépense ;
    la garde des plafonds juste avant la tâche de fond."""
    from app.api import routes as R
    body = body or {}
    try:
        modele = SA.modele_texte(body)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if modele in SA.HY_MODELES:
        return await _texte_hy(body, modele)
    if not _cle_meshy():
        raise HTTPException(503, "Clé Meshy absente — Réglages › Clés : le texte → mouvement passe par ton compte "
                                 "Meshy.")
    try:
        entree = SA.valider_texte(body)
    except ValueError as e:
        raise HTTPException(400, str(e))
    j, version = _version_squelettee(body, "texte → mouvement")
    devis = SA.devis_credits(SA.MODES[entree["mode"]]["credits"])
    if body.get("confirme_cout") is not True:
        raise HTTPException(409, {"message": "Texte → mouvement payant : confirme le coût avant de lancer.",
                                  "devis": devis})
    tache = uuid4().hex[:12]
    plaf = await R._plafond({"kind": "meshy", "credits": SA.MODES[entree["mode"]]["credits"]}, CATEGORIE,
                            f"meshy-motion:{tache}")
    SA.poser_etat(j, tache, etat="prepare", quoi="texte", devis=devis, **entree)
    _TACHES[tache] = asyncio.create_task(_travail_texte(j, tache, int(version), entree, plaf.get("lignes") or []))
    return {"ok": True, "tache": tache, "devis": devis, "etat": "prepare", "nom": entree["nom"]}


async def _texte_hy(body: dict, modele: str):
    """HY-Motion : licence (400) → clé fal (503) → saisie (400) → version squelettée → devis (409) → plafonds (402)."""
    from app.api import routes as R
    if body.get("licence_acceptee") is not True:
        raise HTTPException(400, "Licence HY-Motion non acceptée : lis la « Tencent HY-MOTION 1.0 Community "
                                 "License » (elle exclut l'Union européenne, le Royaume-Uni et la Corée du Sud) et "
                                 "coche la case pour ton usage.")
    if not _cle_fal():
        raise HTTPException(503, "Clé fal absente — Réglages › Clés : HY-Motion passe par ton compte fal.")
    try:
        entree = SA.valider_hy(body)
    except ValueError as e:
        raise HTTPException(400, str(e))
    j, version = _version_squelettee(body, "HY-Motion")
    devis = SA.devis_hy(modele)
    if body.get("confirme_cout") is not True:
        raise HTTPException(409, {"message": "HY-Motion payant : confirme le coût avant de lancer.", "devis": devis})
    tache = uuid4().hex[:12]
    await R._plafond({"kind": "hy_motion", "modele": modele}, CATEGORIE, f"hy-motion:{tache}")
    SA.poser_etat(j, tache, etat="prepare", quoi="texte", devis=devis, **entree)
    _TACHES[tache] = asyncio.create_task(_travail_hy(j, tache, int(version), entree))
    return {"ok": True, "tache": tache, "devis": devis, "etat": "prepare", "nom": entree["nom"], "modele": modele}


@router.get("/tache", dependencies=[Depends(_local)])
async def tache(job: str, tache: str):
    j = _job_nu(job)
    if not re.fullmatch(r"[0-9a-f]{12}", str(tache or "")):
        raise HTTPException(400, "tâche : identifiant de 12 caractères hexadécimaux attendu")
    e = SA.lire_etat(j, tache)
    if e is None:
        raise HTTPException(404, "tâche inconnue pour ce job")
    if e.get("etat") not in ("fini", "echec") and tache not in _TACHES:
        e["etat"] = "interrompu"                        # le serveur a redémarré pendant le travail
    return e
