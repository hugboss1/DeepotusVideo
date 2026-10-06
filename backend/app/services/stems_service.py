# -*- coding: utf-8 -*-
"""Séparation en stems par Demucs (fal-ai/demucs) — T100, plan-son-vfx T2 (P1).

Page /api relue le 06/10/2026 : `audio_url`, `model` (défaut htdemucs_6s), `stems` (liste), `output_format`
(wav|mp3) ; la réponse porte un champ PAR stem ({url, content_type, file_name, file_size}), guitar/piano pour les
modèles 6s seulement. Chaque stem devient un fichier ordinaire du dossier audio de la Bibliothèque (sidecar kind
« stem », parent = la piste d'origine ; ligne library_assets sonvfx, mère, relation « stem ») : le tiroir Sons et le
Montage les voient sans une ligne de plus. Un stem absent de la réponse est DIT (`missing`), jamais fatal.
Les appels réseau passent par trois seams de module que le banc remplace. La garde des plafonds est sur la ROUTE
(POST /audio/stems), avant tout appel : ce module ne dépense que si on l'appelle."""
from __future__ import annotations

import asyncio
import os
from datetime import datetime
from pathlib import Path

import httpx
from loguru import logger

from app.config import settings, SSL_VERIFY
from app.services import sfx_service, library_index as LI
from app.services.sfx_service import SfxError

ENDPOINT = "fal-ai/demucs"
STEMS_MODELS = {
    "htdemucs_6s": {"label": "Demucs 6 stems", "stems": ("vocals", "drums", "bass", "other", "guitar", "piano")},
    "htdemucs_ft": {"label": "Demucs 4 stems (affiné)", "stems": ("vocals", "drums", "bass", "other")},
}
DEFAULT_MODEL = "htdemucs_6s"


async def _upload(path: Path) -> str:              # seam
    import fal_client
    return await fal_client.upload_file_async(str(path))


async def _fal_subscribe(endpoint: str, arguments: dict) -> dict:   # seam
    import fal_client
    return await fal_client.subscribe_async(endpoint, arguments=arguments, with_logs=False)


async def _download(url: str, dest: Path) -> None:  # seam
    async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=300) as c:
        r = await c.get(url)
        r.raise_for_status()
        tmp = dest.with_name(dest.name + ".part")
        tmp.write_bytes(r.content)
        os.replace(tmp, dest)


def _unique(folder: Path, name: str) -> Path:
    p = folder / name
    i = 2
    while p.exists():
        p = folder / f"{Path(name).stem}_{i}{Path(name).suffix}"
        i += 1
    return p


def source(filename: str) -> Path:
    """Le fichier du dossier audio (NOM seul : un chemin ne sort pas du dossier) ; 404 sinon."""
    p = sfx_service._audio_dir() / Path(str(filename or "")).name
    if not Path(str(filename or "")).name or not p.is_file():
        raise SfxError(404, f"audio introuvable : {filename}")
    return p


def valider(stems, model: str) -> list[str]:
    """La liste des stems demandés, vérifiée contre le registre (400 sinon) ; vide = tous ceux du modèle."""
    m = STEMS_MODELS.get(model)
    if m is None:
        raise SfxError(400, f"modèle de stems inconnu : {model!r} ({', '.join(STEMS_MODELS)})")
    want = [str(s).lower() for s in (stems or m["stems"])]
    bad = [s for s in want if s not in m["stems"]]
    if bad:
        raise SfxError(400, f"stems inconnus pour {m['label']} : {', '.join(bad)}")
    return want


async def separer_stems(filename: str, stems: list[str] | None = None, model: str = DEFAULT_MODEL) -> dict:
    if not (settings.FAL_KEY or "").strip():
        raise SfxError(400, "fal.ai: aucune clé configurée (Réglages → clés API) — les stems passent par fal.")
    want = valider(stems, model)
    src = source(filename)
    folder = src.parent
    loop = asyncio.get_running_loop()
    dur = await loop.run_in_executor(None, sfx_service._probe_duration, src)
    try:
        url = await _upload(src)
        result = await _fal_subscribe(ENDPOINT, {"audio_url": url, "model": model, "stems": want,
                                                 "output_format": "mp3"})
    except Exception as e:
        raise SfxError(502, f"fal.ai: {str(e)[:300]}") from e
    items, missing = [], []
    for s in want:
        f = (result or {}).get(s)
        u = f.get("url") if isinstance(f, dict) else (f if isinstance(f, str) else None)
        if not u:
            missing.append(s)
            continue
        dest = _unique(folder, f"stem_{src.stem[:40]}_{s}.mp3")
        try:
            await _download(u, dest)
        except Exception as e:
            raise SfxError(502, f"fal.ai: téléchargement du stem {s} impossible ({str(e)[:200]})") from e
        sdur = await loop.run_in_executor(None, sfx_service._probe_duration, dest)
        sfx_service.record_meta(dest.name, {"kind": "stem", "stem": s, "parent": src.name, "model": model,
                                            "provider": "fal", "dur": sdur,
                                            "created": datetime.now().isoformat(timespec="seconds")})
        items.append({"filename": dest.name, "url": f"/api/audio/{dest.name}", "name": dest.stem,
                      "stem": s, "dur": round(sdur, 2), "size_kb": dest.stat().st_size // 1024})
    if items:
        await LI.noter([it["filename"] for it in items], "sonvfx", kind="audio", parent=src.name, relation="stem")
    from app.services import pricing
    usd = round(dur * float(pricing.load().get("demucs_usd_per_s", 0.0007)), 4)
    logger.info(f"stems: {src.name} → {len(items)} stems ({missing or 'complet'}) ~{usd} $")
    return {"ok": True, "parent": src.name, "items": items, "missing": missing, "usd": usd, "model": model}
