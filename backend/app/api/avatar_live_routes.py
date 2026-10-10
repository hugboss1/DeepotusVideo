# -*- coding: utf-8 -*-
"""Avatar live G0 (t161, 10/10/2026) — /api/avatar-live : état du Direct, Personnages, sessions Decart.

Gardes :
  - lectures (état, Personnages, images) : boucle locale, ou appareil appairé (garde de jeton de main.py) ;
  - écritures sur les Personnages : boucle locale SEULEMENT (garde globale des écritures de main.py) ;
  - ouvrir / clore une session : boucle locale ou appareil appairé — les deux seules écritures ouvertes au réseau
    local (main._ECRITURES_OUVERTES). La garde du plafond mensuel est la MÊME pour les deux, et passe AVANT tout
    appel à Decart. Ce n'est pas `_require_local_depense` : le téléphone doit pouvoir lancer son Direct.
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from app.services import avatar_live as AL
from app.services import plafonds as _PLAF

router = APIRouter()

_HOTES_LOCAUX = ("127.0.0.1", "::1", "localhost", "testclient")


async def _appareil(request: Request) -> str | None:
    """None = le PC (boucle locale) ; sinon l'id de l'appareil du JETON (jamais un champ du corps)."""
    host = (request.client.host if request.client else "") or ""
    if host in _HOTES_LOCAUX:
        return None
    from app.services import appairage
    entete = request.headers.get("authorization", "")
    jeton = entete[7:].strip() if entete[:7].lower() == "bearer " else ""
    a = await appairage.appareil_du_jeton(jeton)
    if not a:
        raise HTTPException(401, "Jeton d'appareil requis — appairez le téléphone depuis Réglages → Appareils.")
    return a["id"]


def _pricing_estimate(op: dict) -> dict:
    from app.services import pricing
    return pricing.estimate(op)


def _http(e: AL.Refus) -> HTTPException:
    return HTTPException(e.statut, e.message)


@router.get("/etat")
async def etat():
    return {"cle": AL.cle_presente(), "modele": AL.MODELE, "prix_usd_s": AL.prix_usd_s(False),
            "prix_rapide_usd_s": AL.prix_usd_s(True),
            "duree": {"min": AL.DUREE_MIN_S, "max": AL.DUREE_MAX_S, "defaut": AL.DUREE_DEFAUT_S},
            "consentement": AL.TEXTE_CONSENTEMENT, "images_max": AL.IMAGES_MAX, "cote_min_px": AL.COTE_MIN_PX}


@router.get("/personnages")
async def personnages():
    return {"personnages": AL.lister_personnages()}


@router.get("/personnages/{pid}")
async def personnage(pid: str):
    f = AL.lire_personnage(pid)
    if f is None:
        raise HTTPException(404, "Personnage inconnu.")
    return f


@router.get("/personnages/{pid}/image/{n}")
async def personnage_image(pid: str, n: int):
    p = AL.chemin_image(pid, n)
    if p is None:
        raise HTTPException(404, "Image inconnue.")
    return FileResponse(p, media_type="image/png")


@router.post("/personnages")
async def personnage_creer(body: dict | None = None):
    try:
        return AL.creer_personnage(body or {}, origine="pc")
    except AL.Refus as e:
        raise _http(e)


@router.delete("/personnages/{pid}")
async def personnage_supprimer(pid: str):
    if not AL.supprimer_personnage(pid):
        raise HTTPException(404, "Personnage inconnu.")
    return {"supprime": pid}


@router.post("/sessions")
async def session_ouvrir(request: Request, body: dict | None = None):
    appareil = await _appareil(request)
    b = body if isinstance(body, dict) else {}
    try:
        prep = AL.preparer_session(b.get("personnage_id"), b.get("duree_s"), bool(b.get("rapide")), b.get("voix"))
    except AL.Refus as e:
        raise _http(e)
    garde = await _PLAF.verifier(prep["op"], "direct", ref=f"decart:{prep['session_id']}")
    try:
        return await AL.ouvrir_session_direct(prep, garde["lignes"], appareil)
    except AL.Refus as e:
        raise _http(e)


@router.post("/sessions/fin")
async def session_fin(request: Request, body: dict | None = None):
    appareil = await _appareil(request)
    b = body if isinstance(body, dict) else {}
    try:
        return await AL.terminer_session(b.get("session_id"), b.get("secondes"), appareil)
    except AL.Refus as e:
        raise _http(e)


# ── G1 (t162, 10/10/2026) : le Recast différé, l'équivalent de Genjutsu ────────────────────────────────────────────
# Le catalogue est SERVI (l'écran ne recopie ni libellé ni prix). Le dépôt d'une vidéo source et le lancement sont
# des écritures : boucle locale seulement (le téléphone passera par /sync/depot en G6). Le rendu est un JOB.

@router.get("/recast/modeles")
async def recast_modeles():
    from app.services import recast_service as RS
    return {"modeles": {k: {"label": m["label"], "prix_usd_s": m["prix"], "defaut": m["defaut"],
                            "personnage": m["personnage"], "consigne": m["consigne"],
                            **({"note_prix": m["note_prix"]} if m.get("note_prix") else {})}
                        for k, m in RS.MODELES.items()},
            "prereglages": [{"id": p["id"], "label": p["label"]} for p in RS.PREREGLAGES],
            "duree": {"min": int(RS.DUREE_MIN_S), "max": int(RS.DUREE_MAX_S)},
            # G2 (t163) : voix -> voix (ElevenLabs), servi en $/s comme les modèles
            "voix_usd_s": round(_pricing_estimate({"kind": "voix_sts", "duration_s": 60})["total_usd"] / 60.0, 6)}


_DEPOT_MAX_OCTETS = 300 * 1024 * 1024


@router.post("/recast/source")
async def recast_source(request: Request):
    """Dépose une vidéo source (multipart, champ `fichier`) sous un nom ALÉATOIRE confiné ; ffprobe doit y lire une
    vidéo d'une durée > 0, sinon 415 et rien n'est gardé."""
    import asyncio
    import secrets
    from app.services import recast_service as RS, fal_video_tools as FV
    form = await request.form()
    f = form.get("fichier")
    if f is None or not hasattr(f, "read"):
        raise HTTPException(400, "Champ « fichier » attendu (multipart).")
    ext = (str(getattr(f, "filename", "") or "").rsplit(".", 1)[-1] or "").lower()
    if ext not in ("mp4", "mov", "webm"):
        raise HTTPException(415, "Vidéo attendue : .mp4, .mov ou .webm.")
    dest = RS.sources_dir() / f"{secrets.token_hex(12)}.{ext}"
    total = 0
    with open(dest, "wb") as out:
        while True:
            bloc = await f.read(1024 * 1024)
            if not bloc:
                break
            total += len(bloc)
            if total > _DEPOT_MAX_OCTETS:
                out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(413, "Vidéo trop lourde (300 Mo au plus) : un Recast prend 30 s au plus.")
            out.write(bloc)
    try:
        info = await asyncio.to_thread(FV.probe, dest)
    except Exception:  # noqa: BLE001
        info = {}
    if info.get("width") and not info.get("duration_s"):
        # G4 (relevé en preuve le 10/10) : le webm d'un MediaRecorder est « live » — aucune durée dans l'en-tête.
        # Une réécriture SANS réencodage (-c copy) la pose ; le contenu ne change pas.
        import subprocess
        tmp = dest.with_name(dest.stem + ".remux." + ext)
        r = await asyncio.to_thread(subprocess.run, [FV._bin("ffmpeg"), "-y", "-v", "error", "-i", str(dest), "-c", "copy",
                                                     str(tmp)], capture_output=True, timeout=300)
        if r.returncode == 0 and tmp.is_file():
            tmp.replace(dest)
            try:
                info = await asyncio.to_thread(FV.probe, dest)
            except Exception:  # noqa: BLE001
                info = {}
        else:
            tmp.unlink(missing_ok=True)
    if not info.get("duration_s") or not info.get("width"):
        dest.unlink(missing_ok=True)
        raise HTTPException(415, "Ces octets ne sont pas une vidéo lisible (ffprobe n'y trouve ni durée ni image).")
    return {"depot": dest.name, "duree_s": info["duration_s"], "largeur": info["width"], "hauteur": info["height"],
            "ratio": info.get("ratio")}


@router.post("/recast")
async def recast_lancer(body: dict | None = None):
    """{source: {job_id}|{depot}, personnage_id?, modele, resolution?, consigne?, prereglage?, orientation?}
    -> {job_id, devis_usd}. Tout ce qui ne coûte rien est vérifié, PUIS la garde des plafonds, PUIS fal."""
    import asyncio
    from app.services import recast_service as RS, fal_video_tools as FV
    b = body if isinstance(body, dict) else {}
    src, parent = await _source_video(b.get("source") if isinstance(b.get("source"), dict) else {})
    if src is None:
        raise HTTPException(404, "Vidéo source introuvable (rendu sans vidéo, ou dépôt inconnu).")
    pid = b.get("personnage_id")
    perso = AL.lire_personnage(pid) if pid else None
    if pid and perso is None and RS.MODELES.get(str(b.get("modele") or ""), {}).get("personnage"):
        raise HTTPException(400, "Personnage inconnu : choisissez un Personnage (images de référence avec consentement).")
    try:
        info = await asyncio.to_thread(FV.probe, src)
    except ValueError as e:
        raise HTTPException(404, str(e))
    try:
        prep = RS.preparer(b, src, float(info.get("duration_s") or 0), perso)
    except ValueError as e:
        raise HTTPException(400, str(e))
    garde = await _PLAF.verifier(prep["op"], "studio", ref=f"recast:{src.name}")
    job_id = await RS.lancer_recast(prep, garde["lignes"], parent)
    return {"job_id": job_id, "devis_usd": garde["devis"]["total_usd"], "modele": prep["modele"],
            "resolution": prep["resolution"], "duree_s": prep["duree_s"]}


# ── G2 (t163, 10/10/2026) : la voix du Personnage ──────────────────────────────────────────────────────────────────
# Cloner = écriture sur un Personnage (boucle locale), inclus à l'abonnement ElevenLabs : pas de garde de plafond,
# mais le consentement du Personnage (G0) en est la condition. Convertir = PAYANT (Voice Changer, ~1 000 car./min) :
# garde AVANT ElevenLabs ; le rendu est un JOB comme le Recast.

@router.post("/personnages/{pid}/voix")
async def personnage_voix(pid: str, request: Request):
    from app.services import avatar_voix as AV
    form = await request.form()
    fichiers = []
    for f in form.getlist("echantillons"):
        if hasattr(f, "read"):
            fichiers.append((str(getattr(f, "filename", "") or "echantillon")[:80], await f.read()))
    try:
        return await AV.cloner(pid, fichiers, str(form.get("debruiter") or "").lower() in ("1", "true", "on"))
    except AV.Refus as e:
        raise HTTPException(e.statut, e.message)


async def _source_video(src_b: dict):
    """(chemin, parent_job_id) d'une source {job_id} ou {depot} ; (None, None) si introuvable."""
    from pathlib import Path
    from app.services import recast_service as RS
    from app.services.pipeline import Pipeline
    if src_b.get("job_id"):
        j = await Pipeline.get_job(str(src_b["job_id"]))
        p = Path(j.final_video_path) if j is not None and j.final_video_path else None
        return (p, j.id) if p is not None and p.is_file() else (None, None)
    return RS.chemin_depot(src_b.get("depot")), None


@router.post("/voix")
async def voix_convertir(body: dict | None = None):
    """{source: {job_id}|{depot}, personnage_id?, voice_id?, debruiter?} -> {job_id, devis_usd}."""
    import asyncio
    from app.services import avatar_voix as AV, fal_video_tools as FV
    b = body if isinstance(body, dict) else {}
    src, parent = await _source_video(b.get("source") if isinstance(b.get("source"), dict) else {})
    if src is None:
        raise HTTPException(404, "Vidéo source introuvable (rendu sans vidéo, ou dépôt inconnu).")
    perso = AL.lire_personnage(b.get("personnage_id")) if b.get("personnage_id") else None
    if b.get("personnage_id") and perso is None:
        raise HTTPException(404, "Personnage inconnu.")
    info = await asyncio.to_thread(FV.probe, src)
    try:
        prep = AV.preparer(src, float(info.get("duration_s") or 0), perso, b.get("voice_id"))
    except AV.Refus as e:
        raise HTTPException(e.statut, e.message)
    garde = await _PLAF.verifier(prep["op"], "studio", ref=f"voix:{src.name}")
    job_id = await AV.lancer_voix(prep, garde["lignes"], parent, bool(b.get("debruiter")))
    return {"job_id": job_id, "devis_usd": garde["devis"]["total_usd"], "voice_id": prep["voice_id"]}


# ── G3 (t164, 10/10/2026) : le décor différé — détourer (BiRefNet, fal) puis composer en local sur un fond ────────

@router.post("/decor")
async def decor_composer(body: dict | None = None):
    """{source: {job_id}|{depot}, fond: {couleur: "#rrggbb"}|{image: nom}|{video: dépôt}} -> {job_id, devis_usd}."""
    import asyncio
    from app.services import decor_service as DS, fal_video_tools as FV
    b = body if isinstance(body, dict) else {}
    fond = b.get("fond") if isinstance(b.get("fond"), dict) else {}
    if not DS.fond_valide(fond):
        raise HTTPException(400, "Fond illisible : une couleur #rrggbb, une image de la Bibliothèque ou une vidéo déposée.")
    src, parent = await _source_video(b.get("source") if isinstance(b.get("source"), dict) else {})
    if src is None:
        raise HTTPException(404, "Vidéo source introuvable (rendu sans vidéo, ou dépôt inconnu).")
    from app.config import settings
    if not (settings.FAL_KEY or "").strip():
        raise HTTPException(400, "fal.ai : aucune clé configurée (Réglages → clés API) — rien n'a été lancé.")
    info = await asyncio.to_thread(FV.probe, src)
    if not info.get("width") or not info.get("duration_s"):
        raise HTTPException(415, "Vidéo source illisible.")
    if float(info["duration_s"]) > 120:
        raise HTTPException(400, f"La prise fait {info['duration_s']:.1f} s : le décor différé prend jusqu'à 120 s.")
    garde = await _PLAF.verifier({"kind": "matte", "duration_s": float(info["duration_s"])}, "studio",
                                 ref=f"decor:{src.name}")
    job_id = await DS.lancer_decor(src, fond, info, garde["lignes"], parent)
    return {"job_id": job_id, "devis_usd": garde["devis"]["total_usd"]}


# ── G4 (t165, 10/10/2026) : l'enregistrement du Direct devient un RENDU de l'application ───────────────────────────
# Le flux vidéo ne passe jamais par ici (WebRTC navigateur <-> Decart). Le navigateur enregistre la sortie
# (MediaRecorder, webm), la dépose par /recast/source, puis demande sa conversion en mp4 (h264 + aac) : un job
# provider recast / modèle « direct ». Local, gratuit. Le dépôt webm est retiré après conversion.

@router.post("/direct/enregistrer")
async def direct_enregistrer(body: dict | None = None):
    import asyncio
    import subprocess
    from datetime import datetime
    from pathlib import Path
    from uuid import uuid4
    from app.config import settings
    from app.models.schemas import JobStatus, Provider
    from app.services import recast_service as RS, fal_video_tools as FV
    from app.services.storage import JobRecord, async_session_factory
    b = body if isinstance(body, dict) else {}
    src = RS.chemin_depot(b.get("depot"))
    if src is None:
        raise HTTPException(404, "Enregistrement introuvable (dépôt inconnu).")
    perso = AL.lire_personnage(b.get("personnage_id")) if b.get("personnage_id") else None
    job_id = str(uuid4())
    dest = Path(settings.outputs_path) / "final" / f"{job_id}.mp4"
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [FV._bin("ffmpeg"), "-y", "-v", "error", "-i", str(src), "-map", "0:v:0", "-map", "0:a:0?",
           "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", str(dest)]
    r = await asyncio.to_thread(subprocess.run, cmd, capture_output=True, timeout=900)
    if r.returncode != 0 or not dest.is_file():
        raise HTTPException(415, "Enregistrement illisible : " + r.stderr.decode("utf-8", "replace")[-200:])
    info = await asyncio.to_thread(FV.probe, dest)
    titre = "Direct — " + (perso["nom"] if perso else "sans Personnage")
    async with async_session_factory() as s:
        s.add(JobRecord(id=job_id, status=JobStatus.DONE.value, progress=100, image_filename="",
                        provider=Provider.RECAST.value, video_model="direct", title=titre[:200],
                        duration_s=int(round(info.get("duration_s") or 0)), aspect_ratio=info.get("ratio"),
                        video_path=str(dest), final_video_path=str(dest), current_step="Complete",
                        created_at=datetime.utcnow(), completed_at=datetime.utcnow()))
        await s.commit()
    src.unlink(missing_ok=True)
    return {"job_id": job_id, "duree_s": info.get("duration_s"), "ratio": info.get("ratio")}


# ── G5 (t166, 10/10/2026) : la voix en direct — un segment PCM 16 kHz mono à la fois ──────────────────────────────
# Écriture ouverte au téléphone appairé comme /sessions (la session est celle de SON jeton). Pas de garde ici : le
# coût est RÉSERVÉ à l'ouverture de la session (/sessions, gardée), chaque segment s'impute sur la réserve et un
# segment au-delà est refusé (409) ; la fin note le réel.

@router.get("/voix-direct/etat")
async def voix_direct_etat():
    from app.services import voix_direct as VD
    return await VD.etat()


@router.post("/sessions/voix")
async def session_voix(request: Request, session_id: str = ""):
    from fastapi.responses import Response
    from app.services import voix_direct as VD
    appareil = await _appareil(request)
    pcm = await request.body()
    try:
        d = VD.valider_pcm(pcm)
        voix = AL.imputer_voix(session_id, appareil, d)
        out, ms = await VD.convertir_segment(voix, pcm)
    except (AL.Refus, VD.Refus) as e:
        raise HTTPException(e.statut, e.message)
    return Response(out, media_type="application/octet-stream", headers={"X-Latence-Ms": str(ms)})
