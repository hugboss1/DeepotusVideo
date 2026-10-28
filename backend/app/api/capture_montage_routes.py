# -*- coding: utf-8 -*-
"""t317 (28/10/2026) (lot D3) — /api/capture-montage : le montage après coup des captures (plan
docs/superpowers/plans/2026-10-28-t317-montage-capture.md, tâche 3 ; spec boîte à outils §8.4).

Boucle locale SEULEMENT (`routes._require_localhost`), comme /api/capture.
- `GET  /captures`          les captures closes, les plus récentes d'abord : {captures: [{id, cree_utc, duree_ms,
                            clics, montage}]}.
- `GET  /{id}`              {capture, evenements, montage, propose} : le montage enregistré, sinon proposé d'après la
                            piste des clics (niveau de zoom du skin actif de l'espace).
- `GET  /{id}/video`        la piste `scene` remuxée (durée et index : l'aperçu de l'éditeur peut se déplacer).
- `PUT  /{id}`              {montage} -> le montage validé par le serveur, enregistré.
- `POST /{id}/proposer`     une proposition neuve (rien n'est écrit).
- `POST /{id}/rendre`       {montage?, titre?, confirme_cout?, max_usd?, fournisseur?} : rendu ffmpeg, sous-titres
                            (texte connu calé, gratuit ; transcription PAYANTE : devis rendu tant qu'elle n'est pas
                            confirmée, plafonds vérifiés), job `capture` (Bibliothèque, étape « Montage »), index
                            `capture` (parent : la scène, relation `montage`, recette) -> {ok, job_id, fichier, duree_s,
                            chapitres_texte, sous_titres}. Un rendu à la fois par capture (409).
Le Planificateur reçoit le rendu par POST /api/schedule (brouillon sans canaux : ceux du projet actif, t307)."""
from __future__ import annotations

import asyncio
import math
import subprocess
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from loguru import logger

from app.services import capture as C
from app.services import capture_montage as M

router = APIRouter()

_EN_COURS: set[str] = set()
_USD_TOL = 0.0005
MAX_CORPS = 2 * 1024 * 1024


def _local(request: Request) -> None:
    from app.api.routes import _require_localhost
    _require_localhost(request)


async def _json(request: Request) -> dict:
    corps = await request.body()
    if len(corps) > MAX_CORPS:
        raise HTTPException(413, "Corps de requête trop lourd.")
    import json
    try:
        d = json.loads(corps or b"{}")
    except ValueError:
        raise HTTPException(400, "Corps JSON illisible.") from None
    if not isinstance(d, dict):
        raise HTTPException(400, "Corps JSON illisible.")
    return d


def _close(cid: str) -> dict:
    """La session et sa piste ; seulement une capture terminée."""
    r = C.lire(cid)
    if r["session"].get("etat") != "terminee" or r["clics"] is None:
        raise C.RefusCapture("Cette capture n'est pas terminée.", 409)
    return r


def _duree(r: dict) -> int:
    return int(r["clics"].get("duree_ms") or r["session"].get("duree_ms") or 0)


def _k_skin():
    try:
        from app.services import espaces, skins
        s = skins.actif(espaces.espace_courant()) or {}
        return (s.get("zoom") or {}).get("niveau")
    except Exception:  # noqa: BLE001 — sans skin lisible : le niveau par défaut
        return None


def _refus(e):
    return HTTPException(e.statut, str(e))


@router.get("/captures")
async def lister(request: Request):
    _local(request)

    def _lister():
        out = []
        if not M.racine().is_dir():
            return out
        for d in M.racine().iterdir():
            if not C.ID.match(d.name):
                continue
            try:
                r = C.lire(d.name)
            except (C.RefusCapture, ValueError, OSError):
                continue
            s = r["session"]
            if s.get("etat") != "terminee" or r["clics"] is None:
                continue
            out.append({"id": s["id"], "cree_utc": s.get("cree_utc"), "duree_ms": _duree(r),
                        "clics": sum(1 for e in r["clics"].get("evenements") or [] if e.get("type") == "clic"),
                        "montage": (d / "montage.json").is_file()})
        out.sort(key=lambda x: x["cree_utc"] or "", reverse=True)
        return out[:100]
    return {"captures": await asyncio.to_thread(_lister)}


@router.get("/{cid}")
async def lire(cid: str, request: Request):
    _local(request)
    try:
        r = await asyncio.to_thread(_close, cid)
        m = await asyncio.to_thread(M.lire_montage, cid)
    except C.RefusCapture as e:
        raise _refus(e) from None
    propose = m is None
    try:
        # revue finale (I4) : un montage enregistré est relu par le serveur avant d'aller à l'écran
        m = M.valider(M.proposer(r["clics"], k=_k_skin()) if propose else m, _duree(r), cid)
    except M.RefusMontage:
        propose, m = True, M.valider(M.proposer(r["clics"], k=_k_skin()), _duree(r), cid)
    s = r["session"]
    return {"capture": {"id": cid, "cree_utc": s.get("cree_utc"), "duree_ms": _duree(r), "cadre": r["clics"].get("cadre"),
                        "pistes": sorted(s.get("pistes") or {})},
            "evenements": r["clics"].get("evenements") or [], "montage": m, "propose": propose}


@router.get("/{cid}/video")
async def video(cid: str, request: Request):
    _local(request)
    try:
        await asyncio.to_thread(_close, cid)
        f = await asyncio.to_thread(M.remuxer, cid, "scene")
    except (C.RefusCapture, M.RefusMontage) as e:
        raise _refus(e) from None
    return FileResponse(str(f), media_type="video/webm" if f.suffix == ".webm" else "video/mp4")


@router.put("/{cid}")
async def enregistrer(cid: str, request: Request):
    _local(request)
    d = await _json(request)
    try:
        r = await asyncio.to_thread(_close, cid)
        m = M.valider(d.get("montage"), _duree(r), cid)
        await asyncio.to_thread(M.ecrire_montage, cid, m)
    except (C.RefusCapture, M.RefusMontage) as e:
        raise _refus(e) from None
    return {"montage": m}


@router.post("/{cid}/proposer")
async def proposer(cid: str, request: Request):
    _local(request)
    try:
        r = await asyncio.to_thread(_close, cid)
    except C.RefusCapture as e:
        raise _refus(e) from None
    return {"montage": M.valider(M.proposer(r["clics"], k=_k_skin()), _duree(r), cid)}


def _scene_biblio(cid: str) -> str | None:
    from app.config import settings
    d = settings.outputs_path / "captures"
    for f in sorted(d.glob(f"capture_*_{cid}.*")) if d.is_dir() else []:
        return f.name
    return None


def _audio_seul(fichier) -> Path | None:
    """La voix du rendu seule (AAC mono 64 kb/s, .m4a) : ce qu'on transcrit ou cale, jamais la vidéo 1080p entière
    (revue finale I3 : plafond de taille des fournisseurs). None si le rendu n'a pas de son lisible."""
    from app.services import capture_montage as _M
    out = Path(fichier).with_suffix(".voix.m4a")
    try:
        r = subprocess.run([_M._ffmpeg(), "-y", "-v", "error", "-i", str(fichier), "-vn", "-ac", "1", "-c:a", "aac",
                            "-b:a", "64k", str(out)], capture_output=True, timeout=1800)
    except subprocess.TimeoutExpired:
        r = None
    if r is None or r.returncode != 0 or not out.is_file() or out.stat().st_size == 0:
        out.unlink(missing_ok=True)
        return None
    return out


def _sous_titres(fichier, audio: Path, m: dict, fournisseur: str) -> dict:
    """Grave les sous-titres sur le rendu (quick_finish, le chemin de Quick) d'après la voix seule `audio` (effacée à la
    fin). Ne lève jamais : {etat, repliques}."""
    from app.services import quick_finish as Q
    st = m["sous_titres"]
    try:
        return _graver(Q, fichier, audio, st, m, fournisseur)
    finally:
        Path(audio).unlink(missing_ok=True)


def _graver(Q, fichier, audio, st: dict, m: dict, fournisseur: str) -> dict:
    try:
        segs = Q.segments_for(audio, st["texte"], lang=st["langue"],
                              source="transcribe" if st["source"] == "transcrire" else "align", provider=fournisseur)
        if not segs:
            return {"etat": "sans_voix"}
        ass = Q.burn(fichier, segs, ratio=m["format"])
        ass.unlink(missing_ok=True)
        return {"etat": "graves", "repliques": len(segs)}
    except Exception as e:  # noqa: BLE001 — un sous-titre raté ne coûte pas le rendu
        logger.warning(f"montage : sous-titres non gravés ({type(e).__name__})")
        return {"etat": "echec"}


@router.post("/{cid}/rendre")
async def rendre(cid: str, request: Request):
    _local(request)
    d = await _json(request)
    from app.api import routes as R
    from app.config import settings
    from app.services import library_index as LI
    try:
        r = await asyncio.to_thread(_close, cid)
        brut = d.get("montage") if d.get("montage") is not None else (await asyncio.to_thread(M.lire_montage, cid)
                                                                       or M.proposer(r["clics"], k=_k_skin()))
        m = M.valider(brut, _duree(r), cid)
    except (C.RefusCapture, M.RefusMontage) as e:
        raise _refus(e) from None
    if cid in _EN_COURS:
        raise HTTPException(409, "Un rendu de cette capture est déjà en cours.")
    # revue finale (I1) : réservé AVANT tout await, devis compris : deux confirmations simultanées ne paient pas deux fois
    _EN_COURS.add(cid)
    try:
        fournisseur = str(d.get("fournisseur") or "")[:20]
        op = None
        if m["sous_titres"]["source"] == "transcrire":
            from app.services import transcribe_service as T
            segs = M.segments(m, _duree(r))
            dur = sum((b - a) / v for a, b, v in segs) / 1000
            try:
                est = T.estimate_transcription(dur, fournisseur or None)
            except ValueError as e:
                raise HTTPException(400, str(e)) from None
            if d.get("confirme_cout") is not True or not est.get("ok"):
                return {"ok": False, "devis": est}
            max_usd = d.get("max_usd")
            if (isinstance(max_usd, bool) or not isinstance(max_usd, (int, float)) or not math.isfinite(max_usd)
                    or max_usd < 0):
                raise HTTPException(400, "La confirmation exige le coût accepté (max_usd).")
            if float(est.get("usd") or 0) > float(max_usd) + _USD_TOL:
                return JSONResponse(status_code=409, content={
                    "detail": "Le coût de la transcription a changé : confirmez le nouveau devis.", "devis": est})
            fournisseur = str(est.get("provider") or fournisseur)
            op = {"kind": "transcribe", "provider": est.get("provider"), "duration_s": dur}
        await asyncio.to_thread(M.ecrire_montage, cid, m)
        try:
            rendu = await asyncio.to_thread(M.rendre, cid, m, settings.outputs_path / "captures")
        except M.RefusMontage as e:
            raise _refus(e) from None
        # revue finale (I2, I3) : la dépense n'est inscrite qu'APRÈS un rendu réussi et une piste audio extraite,
        # juste avant l'appel payant ; un plafond atteint garde le rendu, sans sous-titres
        sst = m["sous_titres"]
        st = ({"etat": "aucun"} if sst["source"] == "aucun"
              else {"etat": "sans_texte"} if sst["source"] == "texte" and not sst["texte"].strip() else None)
        audio = await asyncio.to_thread(_audio_seul, rendu["fichier"]) if st is None else None
        if st is None and audio is None:
            st = {"etat": "echec"}
        if st is None and op is not None:
            from app.services import plafonds
            try:
                await plafonds.verifier(op, "montage", ref=f"capture_montage:{cid}")
            except HTTPException:
                audio.unlink(missing_ok=True)
                st = {"etat": "plafond"}
        if st is None:
            st = await asyncio.to_thread(_sous_titres, rendu["fichier"], audio, m, fournisseur)
    finally:
        _EN_COURS.discard(cid)
    dest = rendu["fichier"]
    titre = C._texte(d.get("titre"), 120) or f"Montage {datetime.now().strftime('%d/%m %H:%M')} ({m['format']})"
    job_id = await R._sfx_video_job(dest, titre, provider="capture", etape="Montage")
    await LI.noter([dest.name], "capture", kind="video", job_id=job_id, parent=_scene_biblio(cid), relation="montage",
                   recette={"capture_id": cid, "format": m["format"], "zooms": len(m["zooms"]),
                            "coupes": len(m["coupes"]), "chapitres": len(rendu["chapitres"]),
                            "sous_titres": m["sous_titres"]["source"]})
    logger.info(f"montage {cid} : rendu {m['format']}, {len(m['zooms'])} zooms, {len(m['coupes'])} coupes")
    return {"ok": True, "job_id": job_id, "fichier": dest.name, "duree_s": round(rendu["duree_ms"] / 1000, 2),
            "chapitres_texte": rendu["texte"], "sous_titres": st}
