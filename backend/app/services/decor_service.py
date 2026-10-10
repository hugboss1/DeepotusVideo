# -*- coding: utf-8 -*-
"""Avatar live G3 (t164, 10/10/2026) — le décor différé : détourer le sujet (BiRefNet vidéo sur fal, le MÊME
endpoint et les mêmes réglages que le matte du Montage, matte_service.ENDPOINT / ARGS_FIXED : ProRes 4444 avec
alpha) puis le COMPOSER en local par ffmpeg sur un fond :
  {"couleur": "#rrggbb"}      fond uni (fond vert pour un incrustateur, couleur de marque…)
  {"image": "<nom>"}          une image de la Bibliothèque (dossier des images, nom NU), recadrée au cadre
  {"video": "<dépôt>"}        une vidéo déposée (/recast/source), bouclée sur la durée de la prise
La sortie garde la taille, la durée et le SON de la source. Un rendu est un JOB (provider recast, modèle « decor »).
Prix : celui du matte (kind « matte », taux « à mesurer » tant que fal n'affiche que $0). L'autre voie du décor —
une consigne Lucy Edit avec les préréglages — est le modèle « objet » du Recast (G1).
Seams : `_upload`, `_fal_subscribe`, `_download`."""
from __future__ import annotations

import asyncio
import re
import subprocess
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from loguru import logger

from app.config import settings

_COULEUR = re.compile(r"^#[0-9a-fA-F]{6}$")
_IMAGES = (".png", ".jpg", ".jpeg", ".webp")
_TACHES: set = set()


async def _upload(path: Path) -> str:                               # seam
    from app.services import matte_service as MT
    return await MT._upload(path)


async def _fal_subscribe(endpoint: str, arguments: dict) -> dict:   # seam
    from app.services import matte_service as MT
    return await MT._fal_subscribe(endpoint, arguments)


async def _download(url: str, dest: Path) -> None:                  # seam
    from app.services import matte_service as MT
    await MT._download(url, dest)


def _bin(n):
    from app.services.fal_video_tools import _bin as b
    return b(n)


def chemin_fond(fond: dict) -> Path | None:
    """Le fichier d'un fond image ou vidéo, CONFINÉ ; None pour une couleur ou un fond introuvable."""
    from app.services import recast_service as RS
    fond = fond if isinstance(fond, dict) else {}
    if fond.get("image"):
        nom = Path(str(fond["image"])).name
        if nom != str(fond["image"]) or Path(nom).suffix.lower() not in _IMAGES:
            return None
        p = settings.images_path / nom
        return p if p.is_file() else None
    if fond.get("video"):
        return RS.chemin_depot(fond["video"])
    return None


def fond_valide(fond: dict) -> bool:
    fond = fond if isinstance(fond, dict) else {}
    if fond.get("couleur") is not None:
        return bool(_COULEUR.match(str(fond["couleur"])))
    return chemin_fond(fond) is not None


def commande(matte: Path, src: Path, fond: dict, w: int, h: int, dest: Path) -> list[str]:
    """Le fond au cadre de la source (recadré, jamais déformé), le sujet par-dessus, le son de la source."""
    ff = [_bin("ffmpeg"), "-y", "-v", "error"]
    cadre = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1"
    if fond.get("couleur"):
        ff += ["-f", "lavfi", "-i", f"color=c=0x{fond['couleur'][1:]}:s={w}x{h}:r=24"]
    elif fond.get("image"):
        ff += ["-loop", "1", "-i", str(chemin_fond(fond))]
    else:
        ff += ["-stream_loop", "-1", "-i", str(chemin_fond(fond))]
    ff += ["-i", str(matte), "-i", str(src),
           "-filter_complex", f"[0:v]{cadre}[bg];[1:v]scale={w}:{h}[fg];[bg][fg]overlay=0:0:shortest=1:format=auto,format=yuv420p[v]",
           "-map", "[v]", "-map", "2:a:0?", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac",
           "-shortest", str(dest)]
    return ff


async def _executer(job_id: str, src: Path, fond: dict, info: dict, lignes: list) -> None:
    from app.models.schemas import JobStatus
    from app.services.storage import JobRecord, async_session_factory
    from app.services import plafonds as _plaf, matte_service as MT

    async def maj(**kw):
        async with async_session_factory() as s:
            j = await s.get(JobRecord, job_id)
            for k, v in kw.items():
                setattr(j, k, v)
            await s.commit()
    matte = Path(settings.outputs_path) / "final" / f"{job_id}.matte.mov"
    try:
        await _plaf.rattacher(lignes, f"decor:{job_id}")
        await maj(status=JobStatus.UPLOADING.value, current_step="Envoi de la prise", progress=10)
        url = await _upload(src)
        await maj(status=JobStatus.GENERATING_VIDEO.value, current_step="Détourage du sujet (BiRefNet)", progress=35)
        res = await _fal_subscribe(MT.ENDPOINT, dict(MT.ARGS_FIXED, video_url=url, model=MT.MATTE_MODELS["portrait"]["fal"]))
        vurl = ((res or {}).get("video") or {}).get("url") if isinstance(res, dict) else None
        if not vurl:
            raise RuntimeError("fal.ai : aucune vidéo détourée dans la réponse")
        matte.parent.mkdir(parents=True, exist_ok=True)
        await _download(vurl, matte)
        await maj(status=JobStatus.MERGING.value, current_step="Composition sur le décor", progress=80)
        dest = Path(settings.outputs_path) / "final" / f"{job_id}.mp4"
        cmd = commande(matte, src, fond, int(info["width"]) // 2 * 2, int(info["height"]) // 2 * 2, dest)
        r = await asyncio.to_thread(subprocess.run, cmd, capture_output=True, timeout=600)
        if r.returncode != 0 or not dest.is_file():
            raise RuntimeError("ffmpeg n'a pas composé le décor : " + r.stderr.decode("utf-8", "replace")[-240:])
        await maj(video_path=str(dest), final_video_path=str(dest), status=JobStatus.DONE.value,
                  current_step="Complete", progress=100, completed_at=datetime.utcnow())
    except Exception as e:  # noqa: BLE001
        logger.warning(f"décor {job_id} en échec : {e}")
        await maj(status=JobStatus.FAILED.value, current_step="Failed", error=str(e)[:500], completed_at=datetime.utcnow())
    finally:
        matte.unlink(missing_ok=True)


async def lancer_decor(src: Path, fond: dict, info: dict, lignes: list, parent_job_id: str | None) -> str:
    """Crée le job « decor » et le lance. PAYANT (fal, BiRefNet) : la garde est passée dans la route."""
    from app.models.schemas import JobStatus, Provider
    from app.services.storage import JobRecord, async_session_factory
    job_id = str(uuid4())
    quoi = fond.get("couleur") or Path(str(fond.get("image") or fond.get("video") or "")).stem
    async with async_session_factory() as s:
        s.add(JobRecord(id=job_id, status=JobStatus.QUEUED.value, image_filename="", provider=Provider.RECAST.value,
                        parent_job_id=parent_job_id, video_model="decor", duration_s=int(round(info["duration_s"])),
                        aspect_ratio=info.get("ratio"), title=f"Décor — {quoi}"[:200], created_at=datetime.utcnow()))
        await s.commit()
    t = asyncio.get_running_loop().create_task(_executer(job_id, src, fond, info, lignes))
    _TACHES.add(t)
    t.add_done_callback(_TACHES.discard)
    return job_id
