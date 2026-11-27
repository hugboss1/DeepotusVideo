# -*- coding: utf-8 -*-
"""t495 (lot G5, 26/11/2026) + t497 (G7) — /api/croissance : le fil des gagnants de la niche et « pourquoi ça marche »
(services/croissance_gagnants.py). Boucle locale SEULEMENT (`routes._require_localhost`) ; la route payante a aussi
`routes._require_local_depense`. `espace_id` absent = l'espace courant.
- `GET    /gagnants`                       ?espace_id=&jours=&seuil=&tous=0|1 : le fil (lecture seule, aucun relevé)
- `GET    /niche`                          ?espace_id= : tous les fils suivis, ceux de la niche marqués, et la niche
- `PUT    /niche`                          {espace_id?, fils: [id]} : pose la niche
- `GET    /enregistres`                    ?espace_id= : les gagnants enregistrés (métadonnées seulement)
- `POST   /enregistres`                    {espace_id?, item_id} : enregistre un gagnant
- `DELETE /enregistres/{item_id}`          ?espace_id= : le retire
- `POST   /gagnants/{item_id}/devis`       {espace_id?, transcription?, langue?} : le devis GRATUIT (aucun appel)
- `POST   /gagnants/{item_id}/analyse`     {espace_id?, max_usd, transcription?, langue?, nouvelle?} : PAYANTE (Claude,
                                           garde « campagnes » dans CG.analyser_gagnant)
- `POST   /note`                           {job_id | post_id, mots?, soustitres?, zone_sure?} : t497, étage 1 GRATUIT
                                           (ffmpeg) ; avec un post, la note va dans `brief.note_rendu`
- `GET    /note/devis`                     ?job_id=|post_id= : le devis GRATUIT de l'étage 2
- `POST   /note/affiner`                   {job_id | post_id, max_usd, langue?, mots?} : étage 2, PAYANT (Claude sur
                                           quatre images clés)
- t500 (G10) : X, la même boucle (services/croissance_x.py ; API X payante à l'usage, plafond du moteur « x ») :
  `GET  /x/devis` (gratuit : les posts X dus à leur jalon, le coût), `POST /x/releve` {max_usd} (PAYANT : accord, garde
  « x », fetcher X), `GET|PUT /x/accord` {auto, plafond_usd} (le relevé automatique et le plafond X),
  `GET /x/devis-publication` ?post_id= (le coût de mise en ligne, lien compris), `POST /x/controle-fil` {messages}
  (contrôles gratuits du fil).
Codes : 400 (forme, accord manquant, transcription trop longue), 404 (espace ou élément inconnu), 409 {message, code}
(`cout` + usd, `en_cours`, `trop`), 402 (plafond), 502/504 (appel peut-être facturé), 503 (Claude non configuré).
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger

from app.services import croissance_gagnants as CG
from app.services import note_rendu as NR
from app.services import inspiration as I

router = APIRouter()

MAX_CORPS = 64 * 1024


def _local(request: Request) -> None:
    from app.api.routes import _require_localhost
    _require_localhost(request)


def _depense_locale(request: Request) -> None:
    from app.api.routes import _require_local_depense
    _require_local_depense(request)


def _eid(v) -> str:
    from app.services import espaces
    return v.strip()[:40] if isinstance(v, str) and v.strip() else espaces.espace_courant()


def _langue(request: Request, v=None) -> str:
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
    if isinstance(e, CG.RefusGagnant):
        if e.statut == 409:
            return HTTPException(409, {"message": str(e), "code": e.code})
        return HTTPException(e.statut, str(e))
    if isinstance(e, I.CoutChange):
        return HTTPException(409, {"message": str(e), "code": "cout", "usd": e.usd})
    if isinstance(e, I.AppelEchoue):
        return HTTPException(e.statut, str(e))
    if isinstance(e, ValueError):
        return HTTPException(400, str(e))
    if isinstance(e, RuntimeError):
        return HTTPException(503 if str(e) in I.RAISONS.values() else 502, str(e))
    raise e


@router.get("/gagnants", dependencies=[Depends(_local)])
async def gagnants(espace_id: str = "", jours: int = CG.FENETRE_JOURS, seuil: float = CG.SEUIL_GAGNANT, tous: int = 0,
                   plateforme: str = ""):
    try:
        return await asyncio.to_thread(CG.lire_gagnants, _eid(espace_id), jours, seuil, bool(tous), None,
                                       plateforme.strip()[:20] or None)
    except Exception as e:  # noqa: BLE001
        raise _http(e) from None


@router.get("/niche", dependencies=[Depends(_local)])
async def niche(espace_id: str = ""):
    from app.services import news_fils as NF
    try:
        eid = _eid(espace_id)
        n = CG.niche(eid)
    except Exception as e:  # noqa: BLE001
        raise _http(e) from None
    dedans = {f["id"] for f in n}
    fils = [dict(CG._vue_fil(f), dans_niche=f["id"] in dedans) for f in NF.lister()["fils"]]
    return {"espace_id": eid, "niche": n, "fils": fils}


@router.put("/niche", dependencies=[Depends(_local)])
async def poser_niche(request: Request):
    c = await _corps(request)
    try:
        eid = _eid(c.get("espace_id"))
        return {"espace_id": eid, "niche": CG.regler_niche(eid, c.get("fils"))}
    except Exception as e:  # noqa: BLE001
        raise _http(e) from None


@router.get("/enregistres", dependencies=[Depends(_local)])
async def enregistres(espace_id: str = ""):
    try:
        eid = _eid(espace_id)
        return {"espace_id": eid, "gagnants": CG.gagnants_enregistres(eid)}
    except Exception as e:  # noqa: BLE001
        raise _http(e) from None


@router.post("/enregistres", dependencies=[Depends(_local)])
async def enregistrer(request: Request):
    c = await _corps(request)
    try:
        return await asyncio.to_thread(CG.enregistrer_gagnant, _eid(c.get("espace_id")), c.get("item_id"))
    except Exception as e:  # noqa: BLE001
        raise _http(e) from None


@router.delete("/enregistres/{item_id}", dependencies=[Depends(_local)])
async def retirer(item_id: str, espace_id: str = ""):
    try:
        fait = CG.retirer_enregistre(_eid(espace_id), item_id)
    except Exception as e:  # noqa: BLE001
        raise _http(e) from None
    if not fait:
        raise HTTPException(404, "Gagnant non enregistré.")
    return {"ok": True}


@router.post("/gagnants/{item_id}/devis", dependencies=[Depends(_local)])
async def devis_analyse(item_id: str, request: Request):
    c = await _corps(request)
    try:
        d = await CG.devis_analyse(_eid(c.get("espace_id")), item_id, c.get("transcription") or "",
                                   _langue(request, c.get("langue")))
    except Exception as e:  # noqa: BLE001
        raise _http(e) from None
    return {**d, "raison": _traduire(d.get("raison") or "", request)}


@router.post("/gagnants/{item_id}/analyse", dependencies=[Depends(_local), Depends(_depense_locale)])
async def analyse(item_id: str, request: Request):
    c = await _corps(request)
    try:
        return await CG.analyser_gagnant(_eid(c.get("espace_id")), item_id, max_usd=c.get("max_usd"),
                                         transcription=c.get("transcription") or "",
                                         langue=_langue(request, c.get("langue")), nouvelle=c.get("nouvelle") is True)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.warning(f"croissance : analyse d'un gagnant refusée ou en échec ({type(e).__name__})")
        raise _http(e) from None


# ── t497 (G7) : la note avant publication d'un rendu ─────────────────────────────────────────────────────────────────
def _cible(c: dict) -> dict:
    j, p = c.get("job_id"), c.get("post_id")
    if not (isinstance(j, str) and j) and not (isinstance(p, str) and p):
        raise HTTPException(400, "job_id ou post_id requis.")
    return {"job_id": j if isinstance(j, str) and j else None, "post_id": p if isinstance(p, str) and p else None}


def _http_note(e: Exception) -> HTTPException:
    from app.api import inspiration_routes as IR
    if isinstance(e, NR.NoteImpossible):
        return HTTPException(404 if "introuvable" in str(e) else 400, str(e))
    return IR._http(e)


@router.post("/note", dependencies=[Depends(_local)])
async def note(request: Request):
    c = await _corps(request)
    try:
        return await NR.estimer(**_cible(c), mots=c.get("mots"), soustitres=c.get("soustitres"), zone_sure=c.get("zone_sure"))
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise _http_note(e) from None


@router.get("/note/devis", dependencies=[Depends(_local)])
async def devis_note(request: Request, job_id: str = "", post_id: str = "", langue: str = ""):
    try:
        d = await NR.devis_affiner(**_cible({"job_id": job_id, "post_id": post_id}),
                                   langue=_langue(request, langue))
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise _http_note(e) from None
    return {**d, "raison": _traduire(d.get("raison") or "", request)}


@router.post("/note/affiner", dependencies=[Depends(_local), Depends(_depense_locale)])
async def affiner(request: Request):
    c = await _corps(request)
    try:
        return await NR.affiner(**_cible(c), max_usd=c.get("max_usd"), langue=_langue(request, c.get("langue")),
                                mots=c.get("mots"))
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise _http_note(e) from None


# ── t500 (G10) : X, la même boucle ───────────────────────────────────────────────────────────────────────────────────
def _http_x(e: Exception) -> HTTPException:
    from app.services import croissance_x as CX
    if isinstance(e, CX.CoutChange):
        return HTTPException(409, {"message": str(e), "code": "cout", "usd": e.usd})
    if isinstance(e, LookupError):
        return HTTPException(404, str(e))
    if isinstance(e, ValueError):
        return HTTPException(400, str(e))
    if isinstance(e, RuntimeError):
        return HTTPException(503, str(e))
    raise e


@router.get("/x/devis", dependencies=[Depends(_local)])
async def x_devis():
    from app.services import croissance_x as CX
    return await CX.devis_releve()


@router.post("/x/releve", dependencies=[Depends(_local), Depends(_depense_locale)])
async def x_releve(request: Request):
    from app.services import croissance_x as CX
    c = await _corps(request)
    try:
        return await CX.relever(c.get("max_usd"))
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.warning(f"croissance x : relevé refusé ou en échec ({type(e).__name__})")
        raise _http_x(e) from None


@router.get("/x/accord", dependencies=[Depends(_local)])
async def x_accord():
    from app.services import croissance_x as CX
    return CX.lire_accord()


@router.put("/x/accord", dependencies=[Depends(_local)])
async def x_poser_accord(request: Request):
    from app.services import croissance_x as CX
    c = await _corps(request)
    try:
        return CX.regler_accord(c.get("auto"), c.get("plafond_usd"))
    except Exception as e:  # noqa: BLE001
        raise _http_x(e) from None


@router.get("/x/devis-publication", dependencies=[Depends(_local)])
async def x_devis_publication(post_id: str = ""):
    from app.services import croissance_x as CX
    try:
        return await CX.devis_publication_post(post_id)
    except Exception as e:  # noqa: BLE001
        raise _http_x(e) from None


@router.post("/x/controle-fil", dependencies=[Depends(_local)])
async def x_controle_fil(request: Request):
    from app.services import script_court as SC
    c = await _corps(request)
    m = c.get("messages")
    if not isinstance(m, list) or len(m) > 25 or not all(isinstance(x, str) for x in m):
        raise HTTPException(400, "Liste de messages attendue (25 au plus).")
    return SC.controler_fil(m, langue=_langue(request, c.get("langue")))
