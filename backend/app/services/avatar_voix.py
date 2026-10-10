# -*- coding: utf-8 -*-
"""Avatar live G2 (t163, 10/10/2026) — la voix du Personnage : clonage instantané ElevenLabs et voix → voix.

Relevé le 10/10 (docs ElevenLabs) :
  - clonage instantané : POST /v1/voices/add, multipart `name` + `files` (+ `remove_background_noise`), réponse
    {voice_id, requires_verification}. Inclus à l'abonnement (aucun crédit par appel) : pas de garde de plafond,
    mais le consentement du Personnage (G0) est EXIGÉ ;
  - voix → voix (Voice Changer) : POST /v1/speech-to-speech/{voice_id}, multipart `audio`, `model_id`
    (eleven_multilingual_sts_v2), `remove_background_noise` ; réponse = l'audio (mp3_44100_128 par défaut).
    Facturé ~1 000 crédits par minute (relevé tiers du 07/2026, même grille que l'isolation déjà chiffrée).
    Le TIMING de la parole est gardé : les lèvres d'une vidéo restent calées, aucun lipsync à refaire.

Une conversion est un JOB (provider recast, video_model « voix ») : la piste de la vidéo source est extraite
(ffmpeg), convertie, puis recollée sur la vidéo copiée telle quelle. Seams : `_poster_clone`, `_poster_sts`."""
from __future__ import annotations

import asyncio
import subprocess
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import httpx
from loguru import logger

from app.config import settings, SSL_VERIFY

BASE = "https://api.elevenlabs.io"
MODELE_STS = "eleven_multilingual_sts_v2"
DUREE_MAX_S = 300.0                 # 5 minutes par conversion
ECHANTILLONS_MAX = 5
ECHANTILLON_MAX_OCTETS = 20 * 1024 * 1024
_TACHES: set = set()


class Refus(Exception):
    def __init__(self, statut: int, message: str):
        super().__init__(message)
        self.statut, self.message = statut, message


def cle() -> str:
    return (getattr(settings, "ELEVENLABS_API_KEY", "") or "").strip()


def _bin(n):
    from app.services.fal_video_tools import _bin as b
    return b(n)


async def _poster_clone(nom: str, fichiers: list[tuple[str, bytes]], debruiter: bool) -> tuple[int, dict]:   # seam
    async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=120) as c:
        r = await c.post(f"{BASE}/v1/voices/add", headers={"xi-api-key": cle()},
                         data={"name": nom, "remove_background_noise": "true" if debruiter else "false"},
                         files=[("files", (n, b)) for n, b in fichiers])
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, {"detail": r.text[:200]}


async def _poster_sts(voice_id: str, audio: bytes, debruiter: bool) -> tuple[int, bytes]:   # seam
    async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=600) as c:
        r = await c.post(f"{BASE}/v1/speech-to-speech/{voice_id}", headers={"xi-api-key": cle()},
                         data={"model_id": MODELE_STS, "remove_background_noise": "true" if debruiter else "false"},
                         files={"audio": ("voix.mp3", audio, "audio/mpeg")})
    return r.status_code, r.content


async def cloner(personnage_id: str, fichiers: list[tuple[str, bytes]], debruiter: bool = False) -> dict:
    """Clone la voix depuis 1 à 5 échantillons et la RATTACHE au Personnage (fiche.json, voix.clonee = vrai)."""
    from app.services import avatar_live as AL
    if not cle():
        raise Refus(409, "Clé ElevenLabs absente (Réglages → clés API) — rien n'a été envoyé.")
    f = AL.lire_personnage(personnage_id)
    if f is None:
        raise Refus(404, "Personnage inconnu.")
    if not fichiers or len(fichiers) > ECHANTILLONS_MAX:
        raise Refus(400, f"De 1 à {ECHANTILLONS_MAX} échantillons de voix (30 s à 3 min au total, voix seule).")
    for n, b in fichiers:
        if len(b) > ECHANTILLON_MAX_OCTETS:
            raise Refus(413, f"« {n} » dépasse 20 Mo.")
    statut, rep = await _poster_clone(f"Deepotus · {f['nom']}"[:60], fichiers, debruiter)
    vid = rep.get("voice_id") if isinstance(rep, dict) else None
    if statut != 200 or not vid:
        det = rep.get("detail") if isinstance(rep, dict) else ""
        raise Refus(502, f"ElevenLabs a refusé le clonage (HTTP {statut}) : {str(det)[:160]}")
    voix = {"fournisseur": "elevenlabs", "voice_id": str(vid)[:80], "clonee": True,
            "le": datetime.now().isoformat(timespec="seconds"),
            "verification": bool(rep.get("requires_verification"))}
    AL.poser_voix(personnage_id, voix)
    logger.info(f"avatar_voix : voix clonée {vid} pour le Personnage {personnage_id}")
    return voix


def extraire_audio(video: Path, dest: Path) -> bool:
    r = subprocess.run([_bin("ffmpeg"), "-y", "-v", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", "44100",
                        "-c:a", "libmp3lame", "-b:a", "128k", str(dest)], capture_output=True, timeout=300)
    return r.returncode == 0 and dest.is_file() and dest.stat().st_size > 0


def recoller(video: Path, audio: Path, dest: Path) -> None:
    r = subprocess.run([_bin("ffmpeg"), "-y", "-v", "error", "-i", str(video), "-i", str(audio), "-map", "0:v:0",
                        "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-shortest", str(dest)],
                       capture_output=True, timeout=300)
    if r.returncode != 0 or not dest.is_file():
        raise RuntimeError("ffmpeg n'a pas recollé la voix : " + r.stderr.decode("utf-8", "replace")[-200:])


async def convertir_fichier(video: Path, voice_id: str, debruiter: bool, dest: Path) -> None:
    """Le cœur, partagé par la route voix → voix et par le Recast « avec la voix du Personnage »."""
    tmp = dest.with_name(dest.stem + ".src.mp3")
    out = dest.with_name(dest.stem + ".sts.mp3")
    try:
        if not await asyncio.to_thread(extraire_audio, video, tmp):
            raise RuntimeError("Cette vidéo n'a pas de piste son à convertir.")
        statut, audio = await _poster_sts(voice_id, tmp.read_bytes(), debruiter)
        if statut != 200 or not audio:
            raise RuntimeError(f"ElevenLabs Voice Changer : HTTP {statut} {audio[:160]!r}")
        out.write_bytes(audio)
        await asyncio.to_thread(recoller, video, out, dest)
    finally:
        tmp.unlink(missing_ok=True)
        out.unlink(missing_ok=True)


def preparer(src: Path, duree_s: float, personnage: dict | None, voice_id: str | None) -> dict:
    if not cle():
        raise Refus(409, "Clé ElevenLabs absente (Réglages → clés API) — rien n'a été lancé.")
    vid = (voice_id or "").strip() or ((personnage or {}).get("voix") or {}).get("voice_id") or ""
    if not vid:
        raise Refus(400, "Aucune voix : clonez la voix du Personnage ou donnez un identifiant de voix ElevenLabs.")
    if not 0 < duree_s <= DUREE_MAX_S:
        raise Refus(400, f"La vidéo fait {duree_s:.1f} s : la conversion de voix prend jusqu'à {DUREE_MAX_S:.0f} s.")
    return {"src": src, "duree_s": float(duree_s), "voice_id": vid[:80], "personnage": personnage,
            "op": {"kind": "voix_sts", "duration_s": float(duree_s)}}


async def _executer(job_id: str, prep: dict, lignes: list, debruiter: bool) -> None:
    from app.models.schemas import JobStatus
    from app.services.storage import JobRecord, async_session_factory
    from app.services import plafonds as _plaf

    async def maj(**kw):
        async with async_session_factory() as s:
            j = await s.get(JobRecord, job_id)
            for k, v in kw.items():
                setattr(j, k, v)
            await s.commit()
    try:
        await _plaf.rattacher(lignes, f"voix:{job_id}")
        await maj(status=JobStatus.GENERATING_VOICEOVER.value, current_step="Conversion de la voix", progress=30)
        dest = Path(settings.outputs_path) / "final" / f"{job_id}.mp4"
        dest.parent.mkdir(parents=True, exist_ok=True)
        await convertir_fichier(Path(prep["src"]), prep["voice_id"], debruiter, dest)
        await maj(video_path=str(dest), final_video_path=str(dest), status=JobStatus.DONE.value,
                  current_step="Complete", progress=100, completed_at=datetime.utcnow())
    except Exception as e:  # noqa: BLE001
        logger.warning(f"voix {job_id} en échec : {e}")
        await maj(status=JobStatus.FAILED.value, current_step="Failed", error=str(e)[:500],
                  completed_at=datetime.utcnow())


async def lancer_voix(prep: dict, lignes: list, parent_job_id: str | None, debruiter: bool = False) -> str:
    """Crée le job « voix » et le lance en tâche de fond. PAYANT (ElevenLabs) : la garde est passée."""
    from app.models.schemas import JobStatus, Provider
    from app.services.storage import JobRecord, async_session_factory
    job_id = str(uuid4())
    nom = (prep["personnage"] or {}).get("nom") or prep["voice_id"]
    async with async_session_factory() as s:
        s.add(JobRecord(id=job_id, status=JobStatus.QUEUED.value, image_filename="", provider=Provider.RECAST.value,
                        parent_job_id=parent_job_id, video_model="voix", duration_s=int(round(prep["duree_s"])),
                        title=f"Voix — {nom}"[:200], created_at=datetime.utcnow()))
        await s.commit()
    t = asyncio.get_running_loop().create_task(_executer(job_id, prep, lignes, debruiter))
    _TACHES.add(t)
    t.add_done_callback(_TACHES.discard)
    return job_id
