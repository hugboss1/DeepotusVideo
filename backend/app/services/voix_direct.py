# -*- coding: utf-8 -*-
"""Avatar live G5 (t166, 10/10/2026) — la VOIX EN DIRECT : le micro, découpé en segments d'environ une seconde,
converti dans la voix du Personnage, renvoyé au navigateur qui le pose comme piste audio du flux envoyé à Decart
(la vidéo est retardée d'autant : Decart rend alors image et voix calées).

Deux moteurs (décision de l'utilisateur du 10/10 : « les deux », puis RVC plutôt que Seed-VC, GPL-3.0 et archivé) :
  cloud  ElevenLabs Voice Changer, POST /v1/speech-to-speech/{voice_id}?output_format=pcm_16000 avec
         file_format=pcm_s16le_16 (l'entrée PCM 16 kHz mono évite le décodage : la doc la dit plus rapide).
         Payant (~1 000 caractères par minute) : la durée de voix est RÉSERVÉE à l'ouverture de la session du Direct
         (garde du plafond dans la route /sessions), chaque segment s'impute sur cette réserve, la fin note le réel.
  local  Voixbox (tools/voixbox, RVC sur le GPU de la machine), http://127.0.0.1:17495 par défaut (VOIXBOX_URL).
         Gratuit. Proposé seulement si un GPU NVIDIA est vu et que Voixbox répond.
La clé ElevenLabs ne quitte jamais le serveur : le navigateur (et le téléphone) passent par ici.
Mesures RÉELLES du 10/10 (ElevenLabs, 6 segments chacun) : segments d'1 s -> latence médiane 1 722 ms (max 2 346) ;
segments de 0,5 s -> médiane 1 536 ms (max 1 757). Le navigateur envoie donc des segments de 0,5 s, jusqu'à 4 en vol.
Seams : `_poster_eleven`, `_poster_voixbox`, `_nvidia_smi`."""
from __future__ import annotations

import asyncio
import subprocess
import time

import httpx

from app.config import settings, SSL_VERIFY

SR = 16000
SEGMENT_MAX_S = 10.0
VOIXBOX_DEFAUT = "http://127.0.0.1:17495"
_GPU: dict = {"t": 0.0, "v": None}


class Refus(Exception):
    def __init__(self, statut: int, message: str):
        super().__init__(message)
        self.statut, self.message = statut, message


def voixbox_url() -> str:
    return (getattr(settings, "VOIXBOX_URL", "") or "").strip().rstrip("/") or VOIXBOX_DEFAUT


def _nvidia_smi() -> str | None:                                   # seam
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                           capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.decode("utf-8", "replace").strip().splitlines()[0] if r.returncode == 0 and r.stdout.strip() else None


def gpu() -> dict | None:
    """{nom, memoire_go} du premier GPU NVIDIA, ou None. Mis en cache 10 minutes (nvidia-smi coûte ~200 ms)."""
    if time.time() - _GPU["t"] < 600:
        return _GPU["v"]
    ligne = _nvidia_smi()
    v = None
    if ligne:
        nom, _, mo = ligne.rpartition(",")
        try:
            v = {"nom": nom.strip(), "memoire_go": round(float(mo) / 1024, 1)}
        except ValueError:
            v = {"nom": ligne.strip(), "memoire_go": None}
    _GPU.update(t=time.time(), v=v)
    return v


async def _poster_voixbox(chemin: str, params: dict | None = None, corps: bytes | None = None) -> tuple[int, bytes, dict]:   # seam
    async with httpx.AsyncClient(timeout=30) as c:
        if corps is None:
            r = await c.get(voixbox_url() + chemin)
        else:
            r = await c.post(voixbox_url() + chemin, params=params, content=corps,
                             headers={"Content-Type": "application/octet-stream"})
    return r.status_code, r.content, dict(r.headers)


async def _poster_eleven(voice_id: str, pcm: bytes) -> tuple[int, bytes]:   # seam
    async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=30) as c:
        r = await c.post(f"https://api.elevenlabs.io/v1/speech-to-speech/{voice_id}",
                         params={"output_format": "pcm_16000"},
                         headers={"xi-api-key": (settings.ELEVENLABS_API_KEY or "").strip()},
                         data={"model_id": "eleven_multilingual_sts_v2", "file_format": "pcm_s16le_16"},
                         files={"audio": ("segment.pcm", pcm, "application/octet-stream")})
    return r.status_code, r.content


async def voixbox_sante() -> dict | None:
    try:
        statut, corps, _ = await _poster_voixbox("/health")
    except (httpx.HTTPError, OSError):
        return None
    if statut != 200:
        return None
    try:
        import json
        d = json.loads(corps.decode("utf-8"))
    except ValueError:
        return None
    return d if isinstance(d, dict) and d.get("ok") else None


async def etat() -> dict:
    g = await asyncio.to_thread(gpu)
    vb = await voixbox_sante() if g else None
    return {"cloud": {"disponible": bool((settings.ELEVENLABS_API_KEY or "").strip()),
                      "moteur": "ElevenLabs Voice Changer"},
            "local": {"gpu": g, "voixbox": bool(vb), "url": voixbox_url(),
                      "modeles": (vb or {}).get("modeles", []), "disponible": bool(g and vb and (vb or {}).get("modeles"))},
            "sr": SR, "segment_max_s": SEGMENT_MAX_S}


def valider_pcm(pcm: bytes) -> float:
    if not pcm or len(pcm) % 2:
        raise Refus(400, "PCM 16 bits mono 16 kHz attendu (longueur paire, non vide).")
    d = len(pcm) / (2 * SR)
    if d > SEGMENT_MAX_S:
        raise Refus(413, f"Segment trop long ({d:.1f} s) : {SEGMENT_MAX_S:.0f} s au plus.")
    return d


async def convertir_segment(voix: dict, pcm: bytes) -> tuple[bytes, int]:
    """Convertit UN segment selon la voix de la session ; rend (pcm 16 kHz, latence ms). L'imputation sur la réserve
    est faite par l'appelant (avatar_live), AVANT l'appel."""
    t0 = time.perf_counter()
    if voix.get("moteur") == "cloud":
        statut, out = await _poster_eleven(voix["voice_id"], pcm)
        if statut != 200 or not out:
            raise Refus(502, f"ElevenLabs Voice Changer : HTTP {statut} {out[:120]!r}")
    else:
        try:
            statut, out, _ = await _poster_voixbox("/convertir", {"modele": voix["modele"], "transpose": voix.get("transpose", 0)}, pcm)
        except (httpx.HTTPError, OSError):
            raise Refus(503, f"Voixbox ne répond pas sur {voixbox_url()} — lancez-le (tools/voixbox/README.md).")
        if statut != 200:
            raise Refus(502 if statut >= 500 else statut, f"Voixbox : HTTP {statut} {out[:160]!r}")
    # Mesuré le 10/10 sur le vrai Voice Changer : 1 s de PCM rend 1,02 s (32 694 octets pour 32 000). Laissé tel
    # quel, l'écart s'empile en DÉRIVE (1,2 s par minute). La sortie est donc recalée à la longueur de l'entrée.
    out = out[:len(pcm)] if len(out) >= len(pcm) else out + b"\x00" * (len(pcm) - len(out))
    return out, int((time.perf_counter() - t0) * 1000)
