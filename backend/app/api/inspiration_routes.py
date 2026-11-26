# -*- coding: utf-8 -*-
"""t313 (28/10/2026) (C3 Inspiration, tâche 3) — /api/inspiration : d'une inspiration à un contenu NEUF (spec §7.4).

Boucle locale SEULEMENT (`routes._require_localhost`) ; les deux routes payantes ont aussi `routes._require_local_depense`.
- `GET  /`                        {espace, projet, inspirations} : l'espace de la requête (pour qui), son projet actif et
                                  ses canaux, ses inspirations récentes avec leur source.
- `POST /capter`                  multipart `image?` (une image ≤ 20 Mo), `texte?`, `source_libelle?`, `source_lien?`,
                                  `langue` (fr | en | auto) -> l'inspiration (lecture locale gratuite).
- `GET  /{id}`                    l'inspiration.
- `GET  /{id}/devis-analyse`      `?image=0|1` : le devis GRATUIT de la matière et des angles.
- `POST /{id}/analyse`            {max_usd, avec_image?, langue?, nouvelle?} : PAYANTE (Claude).
- `POST /{id}/devis`              {angle, image?} : la carte de devis du contenu neuf (gratuit).
- `POST /{id}/redaction`          {angle, max_usd, langue?, nouvelle?} : PAYANTE (Claude).
- `POST /{id}/brouillon`          {titre, accroche?, legende?, visuel?} : le brouillon au Planificateur, après les gardes.
- `POST /video`                   t511 (RV1) : multipart `video` (≤ 300 Mo, ≤ 10 min), `source_libelle?`, `source_lien?`
                                  -> l'inspiration « vidéo » avec sa FICHE (étages 0 et 1, gratuits, locaux).
- `GET  /{id}/planches/{nom}`     t511 : une planche d'images (JPEG) tant que la source n'est pas effacée (R4).
- `GET  /{id}/devis-lecture`      t512 (RV2) : le devis GRATUIT de la lecture (transcription + Claude sur les planches).
- `POST /{id}/lecture`            t512 : {max_usd, langue?, nouvelle?} : PAYANTE ; la RECETTE (rangée dans l'espace).
Codes : 400 corps ou refus de forme, 404 inconnue, 409 {message, code, …} (coût changé `cout` + usd, `en_cours`,
gardes `copie` / `interdits` / `visuel_capte`, `angle`, `sans_analyse`, `espace`), 413, 415, 402 (plafond), 502/504
(appel peut-être facturé), 503 (Claude non configuré ou sans vision). Messages fixes : L10.
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from loguru import logger

from app.services import inspiration as I
from app.services import scan_pages as SP

router = APIRouter()

MAX_CORPS = 64 * 1024
CODES_400 = ("vide", "texte", "format", "sans_image", "titre", "visuel", "illisible", "longue", "matiere")


def _local(request: Request) -> None:
    from app.api.routes import _require_localhost
    _require_localhost(request)


def _depense_locale(request: Request) -> None:
    from app.api.routes import _require_local_depense
    _require_local_depense(request)


def _langue(request: Request, corps: dict | None = None) -> str:
    v = (corps or {}).get("langue")
    if v in ("fr", "en"):
        return v
    from app.i18n import erreurs as _ERR
    return "en" if _ERR.langue(request) == "en" else "fr"


def _traduire(texte: str, request: Request) -> str:
    from app.i18n import erreurs as _ERR
    return _ERR.texte(texte, _ERR.langue(request)) if texte else texte


async def _corps(request: Request) -> dict:
    try:
        taille = int(request.headers.get("content-length") or 0)
    except ValueError:
        taille = 0
    if taille > MAX_CORPS:
        raise HTTPException(413, "Demande trop lourde.")
    brut = b""
    async for m in request.stream():
        brut += m
        if len(brut) > MAX_CORPS:
            raise HTTPException(413, "Demande trop lourde.")
    import json
    try:
        c = json.loads(brut or b"null")
    except ValueError:
        raise HTTPException(400, "Corps JSON attendu.") from None
    return c if isinstance(c, dict) else {}


def _http(e: Exception) -> HTTPException:
    """L'exception du service -> la réponse HTTP (les autres remontent telles quelles)."""
    if isinstance(e, I.Inconnue):
        return HTTPException(404, I.M_INCONNUE)
    if isinstance(e, I.CoutChange):
        return HTTPException(409, {"message": str(e), "code": "cout", "usd": e.usd})
    if isinstance(e, I.EnCours):
        return HTTPException(409, {"message": str(e), "code": "en_cours"})
    if isinstance(e, I.Refus):
        if e.code == "lourde":
            return HTTPException(413, {"message": str(e), "code": e.code})
        if e.code == "purgee":
            return HTTPException(410, {"message": str(e), "code": e.code})
        if e.code in CODES_400:
            return HTTPException(400, {"message": str(e), "code": e.code})
        d = {"message": str(e), "code": e.code}
        if e.garde:
            d.update(e.garde)
        return HTTPException(409, d)
    if isinstance(e, I.AppelEchoue):
        return HTTPException(e.statut, str(e))
    if isinstance(e, SP.RefusPages):
        return HTTPException(e.statut, str(e))
    if isinstance(e, ValueError):
        return HTTPException(400, str(e))
    from app.services import inspiration_video as IV
    if isinstance(e, IV.MesureImpossible):
        return HTTPException(503 if str(e) == IV.M_FFMPEG else 415, str(e))
    if isinstance(e, RuntimeError):
        sans_cle = str(e) in I.RAISONS.values() or str(e).startswith("Aucune clé de transcription")
        return HTTPException(503 if sans_cle else 502, str(e))
    raise e


async def _pour_qui(eid: str) -> dict:
    """{espace, projet} : l'espace (nom, type, couleur, mode du client), le projet actif de CET espace et ses canaux."""
    from app.services import comptes, espaces, library_projects as LP, regles_client
    e = espaces.lire()["espaces"].get(eid) or {}
    try:
        ex = regles_client.exigences(eid, [])
    except Exception:  # noqa: BLE001 — l'en-tête « pour qui » ne bloque jamais
        ex = None
    with espaces.sous_espace(eid):
        projet = await LP.actif()
    ids = await LP.canaux_par_defaut(eid)
    libelles = {c["id"]: c for c in comptes.lister(eid)} if ids else {}
    canaux = [{"id": i, "plateforme": libelles[i].get("plateforme"), "libelle": libelles[i].get("libelle")}
              for i in ids if i in libelles]
    return {"espace": {"id": eid, "nom": e.get("nom") or eid, "type": e.get("type") or "marque",
                       "couleur": e.get("couleur"), "mode": (ex or {}).get("mode")},
            "projet": {"id": projet.get("id") or "", "nom": projet.get("nom") or "", "canaux": canaux}}


@router.get("", dependencies=[Depends(_local)])
@router.get("/", dependencies=[Depends(_local)])
async def liste(request: Request):
    from app.services import espaces
    from app.services import inspiration_video as IV
    eid = espaces.espace_courant()
    await asyncio.to_thread(IV.purger)          # t511 (R4) : sources vidéo effacées à 7 jours, la fiche reste
    return {**await _pour_qui(eid), "inspirations": await asyncio.to_thread(I.lister, eid)}


@router.post("/capter", dependencies=[Depends(_local)])
async def capter(request: Request, image: UploadFile | None = File(None), texte: str = Form(""),
                 source_libelle: str = Form(""), source_lien: str = Form(""), langue: str = Form("fr")):
    from app.services import espaces
    if langue not in ("fr", "en", "auto"):
        raise HTTPException(400, "Langue de lecture inconnue : fr, en ou auto.")
    octets = await image.read(SP.MAX_OCTETS + 1) if image is not None else None
    try:
        rec = await asyncio.to_thread(lambda: I.capter(image=octets or None, texte=texte, source_libelle=source_libelle,
                                                       source_lien=source_lien, langue=langue,
                                                       espace_id=espaces.espace_courant()))
    except Exception as e:  # noqa: BLE001
        raise _http(e) from None
    v = I.vue(rec)
    if v.get("ocr", {}).get("raison"):
        v["ocr"] = {**v["ocr"], "raison": _traduire(v["ocr"]["raison"], request)}
    return {**v, **await _pour_qui(rec["espace_id"])}


@router.post("/video", dependencies=[Depends(_local)])
async def deposer_video(request: Request, video: UploadFile = File(...), source_libelle: str = Form(""),
                        source_lien: str = Form(""), langue: str = Form("fr")):
    """t511 (RV1) : le fichier est écrit par morceaux dans le dossier de l'inspiration (jamais en mémoire entier),
    refusé au-delà de 300 Mo, puis mesuré dans un fil (ffmpeg, gratuit)."""
    from app.services import espaces
    from app.services import inspiration_video as IV
    eid = espaces.espace_courant()
    try:
        iid, chemin = IV.nouvelle(nom=video.filename or "", espace_id=eid)
    except Exception as e:  # noqa: BLE001
        raise _http(e) from None
    taille = 0
    try:
        with open(chemin, "wb") as f:
            while True:
                bloc = await video.read(1024 * 1024)
                if not bloc:
                    break
                taille += len(bloc)
                if taille > IV.OCTETS_MAX:
                    raise I.Refus(IV.M_LOURDE, "lourde")
                f.write(bloc)
        rec = await asyncio.to_thread(lambda: IV.mesurer(iid, chemin=chemin, espace_id=eid,
                                                         source_libelle=source_libelle, source_lien=source_lien,
                                                         langue=langue))
    except Exception as e:  # noqa: BLE001
        IV.abandonner(iid)
        raise _http(e) from None
    return {**I.vue(rec), **await _pour_qui(eid)}


@router.get("/{iid}/planches/{nom}", dependencies=[Depends(_local)])
async def planche(iid: str, nom: str):
    from fastapi.responses import FileResponse
    from app.services import inspiration_video as IV
    try:
        f = IV.chemin_planche(iid, nom)
    except Exception as e:  # noqa: BLE001
        raise _http(e) from None
    if not f.is_file():
        raise HTTPException(404, I.M_INCONNUE)
    return FileResponse(f, media_type="image/jpeg")


@router.get("/{iid}/devis-lecture", dependencies=[Depends(_local)])
async def devis_lecture(iid: str, request: Request, langue: str = ""):
    from app.services import inspiration_recette as IR
    try:
        d = await IR.devis_lecture(iid, _langue(request, {"langue": langue}))
    except Exception as e:  # noqa: BLE001
        raise _http(e) from None
    return {**d, "raison": _traduire(d.get("raison") or "", request)}


@router.post("/{iid}/lecture", dependencies=[Depends(_local), Depends(_depense_locale)])
async def lecture(iid: str, request: Request):
    from app.services import inspiration_recette as IR
    c = await _corps(request)
    try:
        return await IR.lire_reference(iid, max_usd=c.get("max_usd"), langue=_langue(request, c),
                                       nouvelle=c.get("nouvelle") is True)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.warning(f"inspiration : lecture refusée ou en échec ({type(e).__name__})")
        raise _http(e) from None


@router.get("/{iid}", dependencies=[Depends(_local)])
async def obtenir(iid: str):
    try:
        rec = I.lire(iid)
    except Exception as e:  # noqa: BLE001
        raise _http(e) from None
    return {**I.vue(rec), **await _pour_qui(rec["espace_id"])}


@router.get("/{iid}/devis-analyse", dependencies=[Depends(_local)])
async def devis_analyse(iid: str, request: Request, image: int = 0, langue: str = ""):
    try:
        d = await I.devis_analyse(iid, bool(image), _langue(request, {"langue": langue}))
    except Exception as e:  # noqa: BLE001
        raise _http(e) from None
    return {**d, "raison": _traduire(d.get("raison") or "", request)}


@router.post("/{iid}/analyse", dependencies=[Depends(_local), Depends(_depense_locale)])
async def analyse(iid: str, request: Request):
    c = await _corps(request)
    try:
        return await I.analyser(iid, max_usd=c.get("max_usd"), avec_image=c.get("avec_image") is True,
                                langue=_langue(request, c), nouvelle=c.get("nouvelle") is True)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.warning(f"inspiration : analyse refusée ou en échec ({type(e).__name__})")
        raise _http(e) from None


@router.post("/{iid}/devis", dependencies=[Depends(_local)])
async def devis(iid: str, request: Request):
    c = await _corps(request)
    try:
        carte = await I.devis_contenu(iid, c.get("angle"), c.get("image") is not False, _langue(request, c))
    except Exception as e:  # noqa: BLE001
        raise _http(e) from None
    t = carte["arguments"]["texte"]
    t["raison"] = _traduire(t.get("raison") or "", request)
    return carte


@router.post("/{iid}/redaction", dependencies=[Depends(_local), Depends(_depense_locale)])
async def redaction(iid: str, request: Request):
    c = await _corps(request)
    try:
        return await I.rediger(iid, angle=c.get("angle"), max_usd=c.get("max_usd"), langue=_langue(request, c),
                               nouvelle=c.get("nouvelle") is True)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.warning(f"inspiration : rédaction refusée ou en échec ({type(e).__name__})")
        raise _http(e) from None


@router.post("/{iid}/brouillon", dependencies=[Depends(_local)])
async def brouillon(iid: str, request: Request):
    c = await _corps(request)
    try:
        return await I.brouillon(iid, titre=c.get("titre"), accroche=c.get("accroche") or "",
                                 legende=c.get("legende") or "", visuel=c.get("visuel"))
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise _http(e) from None
