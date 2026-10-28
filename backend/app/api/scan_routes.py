# -*- coding: utf-8 -*-
"""t312 (28/10/2026) (C1 Scan, tâche 4) — /api/scan : une page (image ou PDF) -> texte, pour l'Atelier et les Chapitres.

Décision 6 du plan. Boucle locale SEULEMENT (`routes._require_localhost`) ; la route payante a aussi
`routes._require_local_depense`.
- `POST /lire`                     multipart `pages` (1 à 10 fichiers) + `langue` (fr | en | auto) :
                                   {scan_id, moteur, langue, pages, texte, incertains, stats, duree_ms}.
- `GET  /{scan_id}/devis-vision`   le devis GRATUIT du secours Claude : {usd, moteur, nom, disponible, raison, pages}.
- `POST /{scan_id}/vision`         {max_usd, langue?, nouvelle?} : la lecture PAYANTE par Claude (402 plafond, 409 coût
                                   changé, 503 Claude non configuré ou sans vision ; rendu partiel en 200 si un lot
                                   suivant échoue : partiel, pages_lues, premiere_page_non_lue, erreur).
- `GET  /{scan_id}/vision`         la transcription PAYÉE gardée pour ce scan (gratuit) : 200 {…, deja_payee: true},
                                   409 `vision_en_cours` si la lecture tourne encore, 404 s'il n'y en a pas.
- `POST /decoupage`                {texte} (≤ 2 Mo) -> {chapitres: [{titre, texte, caracteres, debut}]} par
                                   `manuscript_agent.segment_chapters` (pur, gratuit) ; `texte` = le texte EXACT du
                                   chapitre (celui du chemin /atelier/manuscript), à utiliser tel quel.

Revue finale t312 (argent, Important 1) : un seul POST /vision à la fois par scan (drapeau `scan_pages.vision_debut` ;
le second reçoit 409 {code: "vision_en_cours"} sans aucun appel) ; la transcription payée est gardée
(`scan_pages.garder_vision`) et un nouveau POST la REND sans payer (`deja_payee: true`) sauf `nouvelle: true` ; le
devis porte `delai_s` (somme des délais des lots) que l'écran attend (+ 30 s). Une erreur réseau au premier lot -> 502,
un délai -> 504, message fixe qui dit que la lecture a peut-être été facturée.
Lecture locale (m1) : échéance globale de ECHEANCE_LIRE s ; passée, les pages restantes ne sont pas lues et le texte
déjà lu est rendu avec `partiel: true` et `pages_lues` (rien de lu : 504).

Lecture locale (Décision 2) : `fr`/`en` = une passe par page image ; `auto` = deux passes fr-FR et en-US par page
(celles qui sont installées dans Windows), `scan_nettoyage.nettoyer(…, autre=)` garde la meilleure.
Pages mixtes (un PDF avec des pages texte et des pages scannées, ou plusieurs fichiers) : les pages sont prises DANS
L'ORDRE ; chaque suite de pages image consécutives est lue puis nettoyée d'un bloc (colonnes, césures, folios et titres
courants se jugent dans la suite), chaque page texte est reprise telle que pypdf la lit ; les morceaux sont joints
par une ligne vide (paragraphe) et les positions des mots incertains décalées sur le texte final. Les stats numériques
des suites s'additionnent (+ `pages_texte`). `moteur` = "windows" dès qu'une page a été lue, "texte" si aucune.
Secours Claude : il relit TOUTES les pages image d'un coup (un seul devis) ; ses lots ne se découpent pas par page,
donc les pages texte placées avant la première image restent devant, les autres viennent après la transcription.
OCR indisponible : 503 {message, code: "ocr_indisponible", secours_vision: devis, scan_id} — le scan est gardé pour
que le secours payant puisse le relire sans nouveau dépôt.
Cache plein (revue t312) : un scan plus lourd que le budget du cache (256 Mo) n'est pas gardé : `scan_id` null et
`en_cache` false (le texte lu est rendu quand même ; le secours Claude demandera un nouveau dépôt).
Journaux : nombres, tailles et durées seulement, jamais le texte lu.
"""
from __future__ import annotations

import asyncio
import json
import time

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from loguru import logger

from app.services import scan_ocr as O
from app.services import scan_pages as SP
from app.services import scan_vision as SV
from app.services.scan_lecture import _indisponible, _joindre, _langues, _lire_ocr, _page_texte  # noqa: F401

router = APIRouter()

LANGUES = ("fr", "en", "auto")
MAX_TEXTE = 2 * 1024 * 1024                 # octets UTF-8 du texte à découper
MAX_CORPS_DECOUPAGE = 13 * 1024 * 1024      # le JSON d'un texte de 2 Mo, échappements \uXXXX compris
MAX_CORPS_VISION = 64 * 1024
_DELAI_OCR = "La lecture de texte de Windows a dépassé le délai d'une minute."
_DELAI_TOTAL = "La lecture de texte de Windows a dépassé deux minutes : réessaie avec moins de pages."
ECHEANCE_LIRE = 120.0                       # secondes, toute la lecture locale (l'écran attend 135 s)


def _local(request: Request) -> None:
    from app.api.routes import _require_localhost
    _require_localhost(request)


def _depense_locale(request: Request) -> None:
    from app.api.routes import _require_local_depense
    _require_local_depense(request)


def _lang(request: Request):
    from app.i18n import erreurs as _ERR
    return _ERR.langue(request)


def _traduire(texte: str, request: Request) -> str:
    """Un message fixe (L10) dans la langue de la requête, pour un champ d'une réponse 200 ou d'un detail imbriqué."""
    from app.i18n import erreurs as _ERR
    return _ERR.texte(texte, _lang(request)) if texte else texte


async def _corps(request: Request, limite: int):
    try:
        taille = int(request.headers.get("content-length") or 0)
    except ValueError:
        taille = 0
    if taille > limite:
        raise HTTPException(413, "Demande trop lourde.")
    morceaux, total = [], 0
    async for morceau in request.stream():
        total += len(morceau)
        if total > limite:
            raise HTTPException(413, "Demande trop lourde.")
        morceaux.append(morceau)
    try:
        corps = json.loads(b"".join(morceaux) or b"null")
    except ValueError:
        raise HTTPException(400, "Corps JSON attendu.") from None
    return corps if isinstance(corps, dict) else {}


def _scan(scan_id: str) -> dict:
    try:
        return SP.obtenir(scan_id)
    except KeyError:
        raise HTTPException(404, "Scan inconnu ou expiré (gardé une heure) : relance la lecture.") from None


def _secours(n_images: int, request: Request) -> dict | None:
    """Le devis du secours Claude proposé avec un 503 (raison traduite), ou None s'il n'y a rien à relire."""
    if not n_images:
        return None
    try:
        d = SV.devis(n_images)
    except Exception:  # noqa: BLE001 — un devis impossible ne masque pas le refus de l'OCR
        return None
    return {**d, "raison": _traduire(d.get("raison") or "", request), "pages": n_images}


@router.post("/lire", dependencies=[Depends(_local)])
async def lire_pages(request: Request, pages: list[UploadFile] = File(...), langue: str = Form("fr")):
    t0 = time.perf_counter()
    if langue not in LANGUES:
        raise HTTPException(400, "Langue de lecture inconnue : fr, en ou auto.")
    if not 1 <= len(pages) <= SP.MAX_FICHIERS:
        raise HTTPException(400, "Il faut de 1 à 10 pages à lire.")
    fichiers = [(f.filename or "", await f.read(SP.MAX_OCTETS + 1)) for f in pages]
    try:
        plan = await asyncio.to_thread(SP.charger, fichiers)
    except SP.RefusPages as e:
        raise HTTPException(e.statut, str(e)) from None
    n_images = sum(p["genre"] == "image" for p in plan)
    try:
        r = await asyncio.to_thread(_lire_ocr, plan, langue, time.monotonic() + ECHEANCE_LIRE)
    except O.ScanIndisponible as e:
        sid = SP.ranger(None, plan)
        logger.warning(f"scan_routes : lecture locale indisponible, {n_images} page(s) image gardée(s) pour le secours")
        raise HTTPException(503, {"message": str(e), "code": "ocr_indisponible", "scan_id": sid,
                                  "en_cache": sid is not None,
                                  "secours_vision": await asyncio.to_thread(_secours, n_images, request)}) from None
    except O.ScanErreur as e:
        delai = str(e) in (_DELAI_OCR, _DELAI_TOTAL)
        logger.warning(f"scan_routes : lecture locale en échec ({'délai' if delai else 'erreur'})")
        raise HTTPException(504 if delai else 502, str(e)) from None
    except ValueError as e:
        raise HTTPException(422, str(e)) from None
    passes = r.pop("passes")
    sid = SP.ranger(r, plan)
    ms = int((time.perf_counter() - t0) * 1000)
    logger.info(f"scan_routes : lecture de {len(plan)} page(s) ({n_images} image, {len(plan) - n_images} texte), "
                f"{passes} passe(s), {r['stats'].get('mots', 0)} mot(s), {len(r['incertains'])} incertain(s), {ms} ms")
    rep = {"scan_id": sid, "en_cache": sid is not None, "moteur": r["moteur"], "langue": r["langue"], "pages": len(plan),
           "texte": r["texte"], "incertains": r["incertains"], "stats": r["stats"], "duree_ms": ms}
    if r.get("partiel"):
        rep.update(partiel=True, pages_lues=r["pages_lues"])
    return rep


# ------------------------------------------------------------------------------------------------- secours Claude
def _images(scan: dict) -> list[bytes]:
    images = [p["octets"] for p in scan["images"] if p.get("genre") == "image"]
    if not images:
        raise HTTPException(422, "Ce scan n'a aucune page en image à relire : son texte a été lu directement.")
    return images


@router.get("/{scan_id}/devis-vision", dependencies=[Depends(_local)])
async def devis_vision(scan_id: str, request: Request):
    images = _images(_scan(scan_id))
    try:
        d = await asyncio.to_thread(SV.devis, len(images))
    except ValueError as e:
        raise HTTPException(400, str(e)) from None
    return {**d, "raison": _traduire(d.get("raison") or "", request), "pages": len(images)}


@router.get("/{scan_id}/vision", dependencies=[Depends(_local)])
async def vision_gardee(scan_id: str, request: Request):
    """La transcription payée gardée (gratuit) : « Relire » la demande d'abord, après un délai de l'écran."""
    _scan(scan_id)
    try:
        SP.vision_libre(scan_id)
    except SP.VisionEnCours as e:
        raise HTTPException(409, {"message": str(e), "code": "vision_en_cours"}) from None
    try:
        r = SP.vision_gardee(scan_id)
    except KeyError:
        r = None
    if not r:
        raise HTTPException(404, "Aucune lecture par Claude n'est gardée pour ce scan.")
    return {**r, "deja_payee": True}


@router.post("/{scan_id}/vision", dependencies=[Depends(_local), Depends(_depense_locale)])
async def relire_vision(scan_id: str, request: Request):
    t0 = time.perf_counter()
    corps = await _corps(request, MAX_CORPS_VISION)
    scan = _scan(scan_id)
    images = _images(scan)
    if corps.get("nouvelle") is not True:      # déjà payée : rendue, sans nouvel appel
        try:
            garde = SP.vision_gardee(scan_id)
        except KeyError:
            garde = None
        if garde:
            logger.info("scan_routes : secours Claude déjà payé pour ce scan, transcription gardée rendue")
            return {**garde, "deja_payee": True}
    langue = corps.get("langue")
    if langue not in LANGUES:
        langue = (scan.get("resultat") or {}).get("langue") or "auto"
    try:
        SP.vision_debut(scan_id)
    except KeyError:
        raise HTTPException(404, "Scan inconnu ou expiré (gardé une heure) : relance la lecture.") from None
    except SP.VisionEnCours as e:
        raise HTTPException(409, {"message": str(e), "code": "vision_en_cours"}) from None
    try:
        try:
            r = await SV.lire(images, max_usd=corps.get("max_usd"), langue=langue)
        except SV.CoutChange as e:
            raise HTTPException(409, {"message": str(e), "usd": e.usd}) from None
        except SV.AppelEchoue as e:
            logger.warning(f"scan_routes : secours Claude, premier appel en échec réseau ({e.statut})")
            raise HTTPException(e.statut, str(e)) from None
        except ValueError as e:
            raise HTTPException(400, str(e)) from None
        except RuntimeError as e:
            raise HTTPException(503 if str(e) in SV.RAISONS.values() else 502, str(e)) from None
        # les pages texte reprennent leur place autour de la transcription (voir l'en-tête du module)
        plan = scan["images"]
        premiere = next(i for i, p in enumerate(plan) if p.get("genre") == "image")
        avant = [_page_texte(p["texte"]) for p in plan[:premiere] if p.get("genre") == "texte"]
        apres = [_page_texte(p["texte"]) for p in plan[premiere:] if p.get("genre") == "texte"]
        texte, incertains = _joindre([(t, []) for t in avant] + [(r["texte"], r["incertains"])]
                                     + [(t, []) for t in apres])
        stats = dict(r.get("stats") or {})
        stats["pages_texte"] = len(avant) + len(apres)
        stats["mots"] = len(texte.split())
        stats["incertains"] = len(incertains)
        ms = int((time.perf_counter() - t0) * 1000)
        resultat = {"moteur": "claude", "langue": r.get("langue"), "texte": texte, "incertains": incertains,
                    "stats": stats, "usd": r.get("usd", 0.0)}
        for k in ("partiel", "pages_lues", "erreur"):
            if k in r:
                resultat[k] = r[k]
        if r.get("partiel"):                   # m5 : le numéro DANS LE DÉPÔT de la première page image non lue
            idx = [i for i, p in enumerate(plan) if p.get("genre") == "image"]
            k = int(r.get("pages_lues") or 0)
            resultat["premiere_page_non_lue"] = idx[k] + 1 if k < len(idx) else len(plan)
        rep = {"scan_id": scan_id, "pages": len(plan), "duree_ms": ms, **resultat}
        SP.garder_vision(scan_id, rep)         # gardée : « Relire » après un délai de l'écran la reprend sans payer
    finally:
        SP.vision_fin(scan_id)
    logger.info(f"scan_routes : secours Claude, {len(images)} page(s) image, {stats['mots']} mot(s), "
                f"{resultat['usd']:.4f} USD{' (partiel)' if r.get('partiel') else ''}, {ms} ms")
    return rep


# ------------------------------------------------------------------------------------------------- découpage
@router.post("/decoupage", dependencies=[Depends(_local)])
async def decouper(request: Request):
    corps = await _corps(request, MAX_CORPS_DECOUPAGE)
    texte = corps.get("texte")
    if not isinstance(texte, str) or not texte.strip():
        raise HTTPException(400, "Aucun texte à découper.")
    if len(texte.encode("utf-8")) > MAX_TEXTE:
        raise HTTPException(413, "Texte trop long : 2 Mo au plus.")
    from app.services import manuscript_agent as MA
    chapitres = await asyncio.to_thread(MA.segment_chapters, texte)
    out, curseur = [], 0
    for ch in chapitres:
        corps_ch = ch.get("text") or ""
        tete = corps_ch.strip().split("\n", 1)[0][:60]
        pos = texte.find(tete, curseur) if tete else -1     # au mieux : le début du texte du chapitre dans l'entrée
        if pos < 0:
            pos = curseur
        out.append({"titre": ch.get("title") or "", "texte": corps_ch, "caracteres": len(corps_ch), "debut": pos})
        curseur = pos + len(tete)
    logger.info(f"scan_routes : découpage de {len(texte)} caractère(s) en {len(out)} chapitre(s)")
    return {"chapitres": out}
