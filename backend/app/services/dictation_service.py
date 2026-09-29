"""Dictée des champs IA (H serveur, retours du 26/09, tâche 7 du plan du 27/09).

Deux routes, montées sous `/api` par `app.main` :

  POST /api/dictation/estimate  multipart {file}
       -> {duration_s, provider, label?, usd, available, reason?}
  POST /api/dictation           multipart {file, max_usd, language?}
       -> {text, usd, provider}

Voie 2 du micro des champs IA (T10) : le navigateur n'a pas de
reconnaissance vocale utilisable, il enregistre (MediaRecorder, webm/opus ou
ogg) ; l'app ANNONCE le coût (`/estimate`), l'utilisateur accepte, puis la
prise est transcrite avec un plafond `max_usd` égal au montant affiché.

Règles (convention de l'app : coût annoncé d'abord, jamais de dépense
surprise) :
- garde locale `routes._require_localhost` (comme /audio/recording et toutes
  les routes qui dépensent) ;
- prise ≤ 25 Mo (413 au-delà) — le plafond de Whisper-1 ; vide ou illisible
  → 415 {detail} ; durée transcodée < 0,1 s → 415, > 10 min → 413 ;
  ffmpeg absent ou impossible à lancer → 503 ; `max_usd` NaN, infini ou
  négatif → 422 avant tout transcodage ;
- la prise est transcodée par ffmpeg (patron de /audio/recording, en
  thread) en WAV PCM s16 16 kHz MONO dans un dossier temporaire `dzdict_*`
  d'outputs, supprimé dans TOUS les cas ;
- `usd` vient de `transcribe_service.estimate_transcription` sur la durée
  du WAV transcodé, RECALCULÉ côté serveur à la transcription : si
  usd > max_usd → 402, rien n'est envoyé ;
- aucune clé (ELEVENLABS_API_KEY puis OPENAI_API_KEY) → `/estimate` rend
  available:false + reason, `/dictation` rend 503 {detail} ;
- l'appel payant passe par `transcribe_service.transcribe` (attribut du
  module, lu à l'appel : un banc peut l'espionner).
"""
from __future__ import annotations

import asyncio
import math
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from loguru import logger

from app.services import transcribe_service as TS

router = APIRouter()

DICTATION_MAX_BYTES = 25 * 1024 * 1024
DICTATION_MIN_S = 0.1
DICTATION_MAX_S = 600.0
_EPS_USD = 1e-9
# Raison PROPRE à la dictée (clôture T11, revue T10) : celle de
# transcribe_service propose « le calage d'un texte connu », un chemin que le
# micro des champs IA n'offre pas. Le client la montre dans le title du micro.
SANS_CLE = ("Aucune clé de transcription configurée (Réglages : ElevenLabs ou "
            "OpenAI) : la dictée enregistrée ne peut pas être transcrite.")


def _garde(request: Request) -> None:
    # Import paresseux (comme montage_service) : routes importe beaucoup.
    from app.api import routes as R
    R._require_localhost(request)


async def _lire(request: Request, file: UploadFile) -> bytes:
    """Octets de la prise, bornés : 413 au-delà de 25 Mo, 415 si vide."""
    try:
        cl = int(request.headers.get("content-length") or 0)
    except ValueError:
        cl = 0
    if cl > DICTATION_MAX_BYTES + 65536:
        raise HTTPException(413, "Prise trop lourde (25 Mo max).")
    contents = await file.read(DICTATION_MAX_BYTES + 1)
    if len(contents) > DICTATION_MAX_BYTES:
        raise HTTPException(413, "Prise trop lourde (25 Mo max).")
    if not contents:
        raise HTTPException(415, "Prise vide : aucun son reçu.")
    return contents


def _transcoder(contents: bytes, tmpd: Path) -> Path:
    """ffmpeg → WAV s16 16 kHz mono dans `tmpd` ; lève HTTPException 415/413/504."""
    src, out = tmpd / "prise.bin", tmpd / "prise.wav"
    src.write_bytes(contents)
    try:
        r = subprocess.run(
            [TS._bin("ffmpeg"), "-nostdin", "-y", "-hide_banner",
             "-loglevel", "error", "-i", str(src), "-vn", "-map", "0:a:0",
             "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
             "-t", str(DICTATION_MAX_S + 1), "-f", "wav", str(out)],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", stdin=subprocess.DEVNULL, timeout=120)
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "Transcodage trop long (120 s) : prise abandonnée.")
    except Exception as e:                               # noqa: BLE001
        # Binaire absent ou impossible à lancer : panne du serveur, pas de
        # la prise → 503 (revue T7).
        raise HTTPException(503, f"ffmpeg injoignable : {e}")
    if r.returncode != 0 or not out.is_file():
        raise HTTPException(415, "Format de prise illisible : "
                                 f"{(r.stderr or '').strip()[-200:]}")
    try:
        with wave.open(str(out), "rb") as w:
            dur = w.getnframes() / float(w.getframerate() or 1)
    except Exception as e:                               # noqa: BLE001
        raise HTTPException(415, f"WAV illisible : {e}")
    if dur < DICTATION_MIN_S:
        raise HTTPException(415, f"Prise trop courte ({dur:.2f} s).")
    if dur > DICTATION_MAX_S:
        raise HTTPException(413, f"Dictée trop longue (plus de "
                                 f"{int(DICTATION_MAX_S // 60)} min).")
    return out


def _dossier_tmp() -> Path:
    from app.config import settings
    base = Path(settings.outputs_path)
    base.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="dzdict_", dir=str(base)))


def _langue(language: str | None) -> str | None:
    """« fr-FR » → « fr » (code ISO attendu par Scribe comme par Whisper)."""
    s = (language or "").strip()
    if not s:
        return None
    return s.replace("_", "-").split("-")[0].lower()[:3] or None


def _estimer_sync(contents: bytes) -> dict:
    tmpd = _dossier_tmp()
    try:
        wav = _transcoder(contents, tmpd)
        with wave.open(str(wav), "rb") as w:
            dur = w.getnframes() / float(w.getframerate() or 1)
        return TS.estimate_transcription(dur)
    finally:
        shutil.rmtree(tmpd, ignore_errors=True)


@router.post("/dictation/estimate")
async def dictation_estimate(request: Request, file: UploadFile = File(...)):
    """Durée et coût de transcription d'une prise, AVANT tout envoi payant.
    → {duration_s, provider, label?, usd, available, reason?}"""
    _garde(request)
    contents = await _lire(request, file)
    est = await asyncio.to_thread(_estimer_sync, contents)
    out = {"duration_s": est.get("duration_s", 0.0),
           "provider": est.get("provider"),
           "usd": est.get("usd", 0.0),
           "available": bool(est.get("ok"))}
    if est.get("ok"):
        out["label"] = est.get("label")
        out["eta_s"] = est.get("eta_s")
    else:
        out["reason"] = SANS_CLE
    return out


@router.post("/dictation")
async def dictation(request: Request, file: UploadFile = File(...),
                    max_usd: float = Form(...),
                    language: str | None = Form(None)):
    """Transcrit une prise si son coût RECALCULÉ ne dépasse pas `max_usd`.
    → {text, usd, provider} ; 402 au-delà du plafond, 503 sans clé."""
    _garde(request)
    # NaN/inf passent `float` et rendent toute comparaison fausse (nan) ou
    # vraie (inf) : plafond refusé AVANT tout transcodage (revue T7).
    if not math.isfinite(max_usd) or max_usd < 0:
        raise HTTPException(422, "Plafond max_usd invalide.")
    contents = await _lire(request, file)
    if not TS.resolve_provider():
        raise HTTPException(503, SANS_CLE)
    lang = _langue(language)

    def _mesurer(tmpd) -> tuple:
        wav = _transcoder(contents, tmpd)
        with wave.open(str(wav), "rb") as w:
            dur = w.getnframes() / float(w.getframerate() or 1)
        est = TS.estimate_transcription(dur)
        if not est.get("ok"):
            raise HTTPException(503, SANS_CLE)
        usd = float(est.get("usd") or 0.0)
        if usd > float(max_usd) + _EPS_USD:
            raise HTTPException(
                402, f"Coût recalculé {usd:.4f} $ supérieur au plafond "
                     f"accepté {float(max_usd):.4f} $ : rien n'a été envoyé.")
        return wav, dur, est.get("provider"), usd

    def _transcrire(wav, dur, pid, usd) -> dict:
        logger.info(f"dictation: {dur:.1f}s via {pid} ≈ {usd:.4f} $ "
                    f"(plafond {float(max_usd):.4f} $)")
        try:
            res = TS.transcribe(wav, provider=pid, language=lang)
        except ValueError as e:
            raise HTTPException(413, str(e))
        except (RuntimeError, OSError) as e:
            raise HTTPException(502, f"Transcription échouée : {e}")
        except Exception as e:                       # noqa: BLE001
            raise HTTPException(502, f"Transcription échouée : {e}")
        return {"text": str((res or {}).get("text") or "").strip(),
                "usd": usd, "provider": pid}

    tmpd = await asyncio.to_thread(_dossier_tmp)
    try:
        wav, dur, pid, usd = await asyncio.to_thread(_mesurer, tmpd)
        # tâche #16 : la garde MENSUELLE, entre la mesure (gratuite) et l'envoi (payant)
        from app.services import plafonds as _PLAF
        await _PLAF.verifier({"kind": "transcribe", "provider": pid, "duration_s": dur}, "dictee")
        return await asyncio.to_thread(_transcrire, wav, dur, pid, usd)
    finally:
        shutil.rmtree(tmpd, ignore_errors=True)
