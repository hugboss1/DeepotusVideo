# -*- coding: utf-8 -*-
"""T103 (plan-son-vfx T9, D2a) — le matte vidéo : BiRefNet v2 (fal) détoure le
sujet d'un rendu et le rend en ProRes 4444 (avec alpha), rangé sous
outputs/mattes/ ; le Montage compose ensuite les effets ENTRE le fond et lui.

Schéma relu le 06/10/2026 sur l'openapi « queue » de fal
(`fal-ai/birefnet/v2/video`) : `video_url` seul requis ; `video_output_type`
∈ {X264 (.mp4), VP9 (.webm), PRORES4444 (.mov), GIF (.gif)} ; `model` ∈ six
libellés ; `operating_resolution` ∈ {1024x1024, 2048x2048, 2304x2304} ;
`refine_foreground` (défaut vrai) ; sortie `video` (+ `mask_video`).

LE PRIX N'EST PAS CONNU, ET ON LE DIT. La page du modèle n'affiche que
« $0 per compute second » (relu le 06/10, comme le 03/09) — un chiffre qui ne
peut pas être vrai. Le devis vaut donc 0 $ AVEC une ligne qui le nomme « à
mesurer », la note suit le travail jusqu'à l'écran, et le vrai montant se lit
sur le tableau de bord fal après le premier tir (à écrire alors dans
pricing.DEFAULTS["birefnet_video_usd_per_s"], daté).

Travaux suivis EN MÉMOIRE (un détourage dure de quelques secondes à quelques
dizaines ; le panneau interroge aussitôt) : un redémarrage les oublie, les
fichiers restent. Les appels réseau passent par trois seams de module
(`_upload`, `_fal_subscribe`, `_download`) que les bancs remplacent."""
from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path
from uuid import uuid4

import httpx
from loguru import logger

from app.config import settings, SSL_VERIFY

ENDPOINT = "fal-ai/birefnet/v2/video"
MATTE_MODELS = {
    "general": {"label": "Général (léger)", "fal": "General Use (Light)"},
    "matting": {"label": "Matting — cheveux, transparences", "fal": "Matting"},
    "portrait": {"label": "Portrait", "fal": "Portrait"},
}
ARGS_FIXED = {"video_output_type": "PRORES4444 (.mov)", "refine_foreground": True,
              "operating_resolution": "1024x1024", "video_quality": "high"}
USD_NOTE = ("prix à mesurer : fal n'affiche que « $0 per compute second » (06/10/2026) — "
            "lire le montant sur le tableau de bord fal après ce tir, puis l'écrire dans "
            "pricing.birefnet_video_usd_per_s")
_JOBS: dict[str, dict] = {}
_JOBS_MAX = 40
_SAFE = re.compile(r"^[A-Za-z0-9_-]+\.mov$")


def mattes_dir() -> Path:
    p = Path(settings.outputs_path) / "mattes"
    p.mkdir(parents=True, exist_ok=True)
    return p


def matte_path(name: str) -> Path:
    """Le chemin d'un matte, CONFINÉ : un nom simple en .mov, dans le dossier
    des mattes et nulle part ailleurs — ValueError sinon (les routes en font
    un 404, le Montage un « pas de matte »)."""
    n = str(name or "")
    if not _SAFE.match(n):
        raise ValueError(f"nom de matte refusé : {n[:40]!r}")
    p = (mattes_dir() / n).resolve()
    if p.parent != mattes_dir().resolve():
        raise ValueError("matte hors dossier")
    return p


async def _upload(path: Path) -> str:                               # seam
    import fal_client
    return await fal_client.upload_file_async(str(path))


async def _fal_subscribe(endpoint: str, arguments: dict) -> dict:   # seam
    import fal_client
    return await fal_client.subscribe_async(endpoint, arguments=arguments,
                                            with_logs=False)


async def _download(url: str, dest: Path) -> None:                  # seam
    async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=600) as c:
        r = await c.get(url)
        r.raise_for_status()
        tmp = dest.with_name(dest.name + ".part")
        tmp.write_bytes(r.content)
        os.replace(tmp, dest)


def status(mid: str) -> dict:
    return dict(_JOBS.get(str(mid)) or {"status": "unknown"})


async def _run(mid: str, src: Path, model_key: str) -> None:
    j = _JOBS[mid]
    try:
        j.update(status="upload", pct=10)
        url = await _upload(src)
        j.update(status="fal", pct=30)
        args = dict(ARGS_FIXED, video_url=url, model=MATTE_MODELS[model_key]["fal"])
        res = await _fal_subscribe(ENDPOINT, args)
        vurl = ((res or {}).get("video") or {}).get("url") if isinstance(res, dict) else None
        if not vurl:
            keys = ", ".join(map(str, res or {})) if isinstance(res, dict) else type(res).__name__
            raise RuntimeError(f"fal.ai : aucune vidéo dans la réponse (clés : {keys})")
        j.update(status="download", pct=80)
        dest = mattes_dir() / f"{j['label']}_{mid[:8]}.mov"
        await _download(vurl, dest)
        j.update(status="done", pct=100, file=dest.name,
                 url=f"/api/matte/file/{dest.name}")
        logger.info(f"matte {mid} : {dest.name} ({dest.stat().st_size // 1024} Ko) — {USD_NOTE}")
    except Exception as e:  # noqa: BLE001 — le travail échoue NOMMÉMENT, rien ne fuit
        logger.warning(f"matte {mid} en échec : {e}")
        j.update(status="failed", error=str(e)[:300])


def detourer(src: Path, model_key: str = "general", label: str = "clip") -> str:
    """Lance un détourage (tâche de fond sur la boucle COURANTE) et rend son
    id. ValueError nommée : clé absente, modèle inconnu, source introuvable.
    PAYANT (fal) : la route passe la garde des plafonds AVANT d'appeler ceci."""
    if not (settings.FAL_KEY or "").strip():
        raise ValueError("fal.ai : aucune clé configurée (Réglages → clés API).")
    if model_key not in MATTE_MODELS:
        raise ValueError(f"modèle de détourage inconnu : {model_key!r} "
                         f"(connus : {', '.join(MATTE_MODELS)})")
    if not Path(src).is_file():
        raise ValueError("source vidéo introuvable")
    while len(_JOBS) >= _JOBS_MAX:
        _JOBS.pop(next(iter(_JOBS)))
    mid = uuid4().hex
    _JOBS[mid] = {"status": "queued", "pct": 0, "file": None, "url": None,
                  "error": None, "model": model_key,
                  "label": re.sub(r"[^A-Za-z0-9_-]+", "_", str(label or ""))
                  .strip("_")[:24] or "clip",
                  "usd_note": USD_NOTE}
    asyncio.get_running_loop().create_task(_run(mid, Path(src), model_key))
    return mid
