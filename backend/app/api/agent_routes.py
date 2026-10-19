# -*- coding: utf-8 -*-
"""Assistant « Demander à Deepotus » (spec 2026-10-19-agent-aide-design.md, 19/10/2026) — /api/agent.

Boucle locale SEULEMENT, comme les Réglages : la question part vers le moteur de texte de l'utilisateur, sous le
plafond « aide » (le 402 `dz_plafond` remonte tel quel jusqu'au dialogue de /shared/dz-plafonds.js).
A5 : `/estimer` donne le devis GRATUIT d'un appel avec capture ; `/demander` porte alors `image` et `max_usd` (409 si
le coût recalculé dépasse le montant accepté).
"""
import asyncio
import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from app.services import agent_aide as A

router = APIRouter()

_HOTES_LOCAUX = ("127.0.0.1", "::1", "localhost", "testclient")
MAX_CORPS = 8_000_000           # une capture JPEG de 1 280 px tient très en dessous


def _local(request: Request) -> None:
    host = (request.client.host if request.client else "") or ""
    if host not in _HOTES_LOCAUX:
        raise HTTPException(403, "L'assistant n'est accessible que depuis ce PC.")


async def _corps(request: Request):
    try:
        taille = int(request.headers.get("content-length") or 0)
    except ValueError:
        taille = 0
    if taille > MAX_CORPS:
        raise HTTPException(413, "Demande trop lourde.")        # refus AVANT de lire
    morceaux, total = [], 0
    async for morceau in request.stream():                       # lecture en flux, coupée à MAX_CORPS + 1 octets
        total += len(morceau)
        if total > MAX_CORPS:
            raise HTTPException(413, "Demande trop lourde.")
        morceaux.append(morceau)
    brut = b"".join(morceaux)
    try:
        return json.loads(brut or b"null")
    except ValueError:
        raise HTTPException(400, "Corps JSON attendu.") from None


@router.get("/etat")
async def etat(request: Request):
    _local(request)
    return await asyncio.to_thread(A.etat)      # la vision d'Ollama et la voix interrogent des serveurs locaux


@router.post("/estimer")
async def estimer(request: Request):
    _local(request)
    corps = await _corps(request)
    from app.i18n import langue_requete
    try:
        return await asyncio.to_thread(A.estimer_vue, corps, langue_requete(request))
    except ValueError as e:
        raise HTTPException(400, str(e)) from None


@router.post("/demander")
async def demander(request: Request):
    _local(request)
    corps = await _corps(request)
    from app.i18n import langue_requete
    try:
        return await A.demander(corps, langue_requete(request))
    except A.CoutChange:
        raise HTTPException(409, "Le coût a changé depuis ton accord : rien n'a été envoyé. Redemande.") from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from None
    except RuntimeError as e:
        raise HTTPException(502, str(e)) from None


@router.post("/lire")
async def lire(request: Request):
    """A6 : lit une réponse de l'assistant avec la voix des Réglages. Voicebox (local) est gratuit ; ElevenLabs passe
    par le plafond « aide ». Le MP3 va dans un cache à part, jamais dans la Bibliothèque ; une réponse déjà lue repart
    du cache sans rien dépenser."""
    _local(request)
    corps = await _corps(request)
    texte = A.texte_a_lire(corps.get("texte") if isinstance(corps, dict) else None)
    if not texte:
        raise HTTPException(400, "Rien à lire.")
    lang = "en" if isinstance(corps, dict) and corps.get("lang") == "en" else "fr"
    loop = asyncio.get_running_loop()
    from app.services import voice_providers as VP
    prov = await loop.run_in_executor(None, VP.resolve_provider)
    if not prov:
        raise HTTPException(503, "Aucune voix disponible : ajoute la clé ElevenLabs ou lance Voicebox (Réglages).")
    dest = A.chemin_lecture(prov, lang, texte)
    if not dest.is_file():
        op = A.op_lecture(prov, texte)
        if op:
            from app.services import plafonds as _PLAF
            await _PLAF.verifier(op, "aide")
        from app.services.elevenlabs_service import VoiceoverService
        tmp = dest.with_name(dest.stem + ".part.mp3")
        try:
            await loop.run_in_executor(None, lambda: VoiceoverService().generate_long(
                text=texte, output_path=tmp, language=lang, provider=prov))
            tmp.replace(dest)
        except Exception as e:  # noqa: BLE001 — la cause est rendue à l'écran, la clé n'y figure jamais
            tmp.unlink(missing_ok=True)
            raise HTTPException(502, f"Lecture impossible : {e}") from None
        await loop.run_in_executor(None, A.elaguer_lectures)
    return FileResponse(str(dest), media_type="audio/mpeg")
