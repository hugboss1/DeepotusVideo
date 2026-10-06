# -*- coding: utf-8 -*-
"""Nettoyage de voix — T100, plan-son-vfx T3 (P2). Deux voies, deux prix :
  enhance()      chaîne locale ffmpeg sur le vocabulaire FX de sfx_service — 0 $, hors ligne. `fx_chain` RÉORDONNE la
                 liste selon `_FX_ORDER` : la chaîne rendue est eq3 → débruitage → compresseur → −16 LUFS, quel que
                 soit l'ordre écrit dans ENHANCE_CHAIN (le bac P2 l'annonçait à l'envers) ;
  isoler_voix()  ElevenLabs POST /v1/audio-isolation (multipart `audio`, relu le 06/10/2026) — facturé 1 000
                 caractères par minute (R4) ; la garde des plafonds est sur la ROUTE, avant le POST.
Les deux écrivent dans le dossier audio de la Bibliothèque avec un parent (sidecar). Elles sont BLOQUANTES (ffmpeg,
httpx sync) : la route les appelle par run_in_executor, puis note la ligne library_assets elle-même — `noter_bg`
depuis un thread ne fait RIEN (pas de boucle), la provenance serait perdue."""
from __future__ import annotations

import os
import subprocess
from datetime import datetime
from pathlib import Path

import httpx

from app.config import settings, SSL_VERIFY
from app.services import sfx_service
from app.services.sfx_service import SfxError

ISOLATION_URL = "https://api.elevenlabs.io/v1/audio-isolation"
MAX_ISOLATION_BYTES = 500 * 1024 * 1024
# Préréglage « améliorer » : mêmes types/bornes que le rack (sanitize_fx clampe).
ENHANCE_CHAIN = [
    {"type": "denoise", "params": {"amount": 18}},
    {"type": "eq3", "params": {"bass_db": -2, "mid_db": 1, "treble_db": 2}},
    {"type": "compressor", "params": {"threshold_db": -18, "ratio": 3, "attack_ms": 15, "release_ms": 180}},
    {"type": "normalize", "params": {"target_lufs": -16}},
]


def _src(filename: str) -> Path:
    nom = Path(str(filename or "")).name
    p = sfx_service._audio_dir() / nom
    if not nom or not p.is_file():
        raise SfxError(404, f"audio introuvable : {filename}")
    return p


def _dest(prefix: str, src: Path) -> Path:
    folder = sfx_service._audio_dir()
    p = folder / f"{prefix}{src.stem[:48]}.mp3"
    i = 2
    while p.exists():
        p = folder / f"{prefix}{src.stem[:48]}_{i}.mp3"
        i += 1
    return p


def enhance_command(src: Path, out: Path) -> list[str]:
    af = sfx_service.fx_chain(sfx_service.sanitize_fx(ENHANCE_CHAIN, "ameliorer"))
    return ["ffmpeg", "-y", "-hide_banner", "-i", str(src), "-vn", "-af", af,
            "-ar", "44100", "-ac", "2", "-c:a", "libmp3lame", "-b:a", "192k", "-f", "mp3", str(out)]


def _finish(src: Path, out: Path, chain: str, relation: str, usd: float) -> dict:
    dur = round(sfx_service._probe_duration(out), 2)
    sfx_service.record_meta(out.name, {"kind": "voix", "parent": src.name, "chain": chain, "dur": dur,
                                       "created": datetime.now().isoformat(timespec="seconds")})
    return {"ok": True, "filename": out.name, "url": f"/api/audio/{out.name}", "name": out.stem,
            "dur": dur, "size_kb": out.stat().st_size // 1024, "usd": usd, "parent": src.name,
            "relation": relation}


def enhance(filename: str) -> dict:
    """Bloquant (ffmpeg) — à appeler via run_in_executor."""
    src = _src(filename)
    out = _dest("clean_", src)
    tmp = out.with_name(out.name + ".part")
    r = subprocess.run(enhance_command(src, tmp), capture_output=True, text=True, timeout=600)
    if r.returncode != 0 or not tmp.is_file() or tmp.stat().st_size == 0:
        tmp.unlink(missing_ok=True)
        raise SfxError(502, f"améliorer : ffmpeg a échoué — {(r.stderr or '')[-300:]}")
    os.replace(tmp, out)
    return _finish(src, out, "ameliorer", "ameliore", 0.0)


def _post_isolation(key: str, name: str, data: bytes) -> bytes:   # seam
    with httpx.Client(verify=SSL_VERIFY, timeout=600.0) as c:
        r = c.post(ISOLATION_URL, headers={"xi-api-key": key}, files={"audio": (name, data)})
    if r.status_code != 200:
        st = r.status_code if 400 <= r.status_code < 500 else 502
        raise SfxError(st, f"ElevenLabs: {sfx_service._eleven_detail(r)}")
    return r.content


def isolation_usd(duration_s: float) -> float:
    """Le MÊME chiffre que pricing.estimate({kind: isolate}) — celui que la garde a vérifié."""
    from app.services import pricing
    return round(float(pricing.estimate({"kind": "isolate", "duration_s": duration_s})["total_usd"]), 4)


def verifier_isolation(filename: str) -> tuple[Path, float]:
    """Les refus AVANT la garde et le POST (clé, fichier, taille) → (source, durée)."""
    if not (settings.ELEVENLABS_API_KEY or "").strip():
        raise SfxError(400, "ElevenLabs: aucune clé API — ajoute-la dans Réglages → Clés pour isoler une voix.")
    src = _src(filename)
    if src.stat().st_size > MAX_ISOLATION_BYTES:
        raise SfxError(400, "ElevenLabs: fichier > 500 Mo, refusé par l'API.")
    return src, sfx_service._probe_duration(src)


def isoler_voix(filename: str) -> dict:
    """Bloquant (httpx sync) — à appeler via run_in_executor."""
    src, dur = verifier_isolation(filename)
    data = _post_isolation(settings.ELEVENLABS_API_KEY.strip(), src.name, src.read_bytes())
    if not data:
        raise SfxError(502, "ElevenLabs: isolation sans audio en retour.")
    out = _dest("iso_", src)
    tmp = out.with_name(out.name + ".part")
    tmp.write_bytes(data)
    os.replace(tmp, out)
    return _finish(src, out, "isolation", "isole", isolation_usd(dur))
