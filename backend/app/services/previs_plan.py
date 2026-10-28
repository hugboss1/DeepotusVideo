# -*- coding: utf-8 -*-
"""t335 (A5 du lot Scenario, 28/10/2026) — « Previs → plan » : le clip de previs d'un plan (@Video1) et ses style
frames (@Image1…) deviennent la vidéo du plan par Seedance 2.5 reference-to-video (fal), ou ses style frames seules
par Veo 3.1 reference-to-video. Spec : docs/superpowers/specs/2026-10-27-scenario-explorations-design.md, ligne A5.

Partage des rôles :
  - `video_refs` (PUR) : le registre, l'argument fal, le prix, les bornes du clip ;
  - ce module : la sonde du clip (ffprobe), le PROMPT par défaut, le calcul du devis (même chiffre pour le devis
    gratuit, la garde des plafonds et l'usd rendu), le POINT D'ACCROCHE du conform (`conformer_clip`, que t336 / A6
    remplira : étirer puis ré-accélérer, compléter au noir puis couper, transcoder) et le tir ;
  - la route (api/routes.py, /shots/{id}/previs…) : le plan, les fichiers confinés, 503 clé, 409 sans `confirme_cout`,
    plafonds « chapitres », job, Bibliothèque (provenance + recette).
AUCUN appel réseau hors des trois coutures `_upload`, `_fal_subscribe`, `_download` (celles de sfx_service, que les
bancs remplacent). Le tir `tirer_previs` est PAYANT : la route a passé la clé, la confirmation et la garde AVANT."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from uuid import uuid4

from loguru import logger

from app.config import settings
from app.services import video_refs as VR

PROMPT_MAX = 2000
EXT_IMAGE = (".png", ".jpg", ".jpeg", ".webp")
EXT_CLIP = (".mp4", ".mov", ".m4v", ".mkv", ".webm")   # acceptés en ENTRÉE de la route ; le registre filtre ensuite


def infos_clip(path: Path) -> dict:
    """{secondes, largeur, hauteur, fps, octets} du clip (ffprobe) ; des None quand la sonde échoue."""
    out = {"secondes": None, "largeur": None, "hauteur": None, "fps": None, "octets": None}
    try:
        out["octets"] = Path(path).stat().st_size
    except OSError:
        return out
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(path)],
                           capture_output=True, text=True, timeout=30)
        d = json.loads(r.stdout or "{}")
        st = (d.get("streams") or [{}])[0]
        out["largeur"], out["hauteur"] = int(st.get("width") or 0) or None, int(st.get("height") or 0) or None
        num, _, den = str(st.get("r_frame_rate") or "0/1").partition("/")
        out["fps"] = round(float(num) / float(den or 1), 3) if float(den or 1) else None
        out["secondes"] = round(float((d.get("format") or {}).get("duration") or 0), 3) or None
    except (ValueError, TypeError, OSError, subprocess.TimeoutExpired, ZeroDivisionError):
        pass
    return out


def conformer_clip(path: Path, infos: dict, modele: str, duree_plan: float) -> tuple[Path, dict, list[str]]:
    """POINT D'ACCROCHE de t336 (A6, « durée mini des modèles ») : rend (clip à envoyer, ses infos, notes). Aujourd'hui
    l'identité — le clip part tel quel et `video_refs.clip_refuse` dit pourquoi il est hors bornes. t336 y posera le
    conform ffmpeg AVANT l'envoi (et son recalage APRÈS le rendu, la dérive en images affichée) ; le devis suivra
    tout seul, puisqu'il est calculé sur les infos RENDUES ici."""
    return Path(path), dict(infos), []


def prompt_defaut(modele: str, action: str, n_frames: int, style: str = "") -> str:
    """Le prompt proposé (modifiable dans la fiche) : il NOMME chaque référence, comme les recettes de scenario.com
    (« le prompt nomme chaque forme ») — @Video1 pour le mouvement, @ImageN pour le look."""
    action = " ".join(str(action or "").split())
    style = " ".join(str(style or "").split())
    images = ", ".join(f"@Image{i}" for i in range(1, max(1, n_frames) + 1))
    if VR.REGISTRE_REFS[modele]["grammaire"] == "video":
        p = (f"Render @Video1 as the final shot with the look of {images}: keep the exact motion, camera and timing "
             f"of @Video1; take colours, light, materials and characters from {images}.")
    else:
        p = "A cinematic shot in the look of the reference images."
    if action:
        p += f" Action: {action}"
    if style:
        p += f" Style: {style}"
    return p[:PROMPT_MAX]


def calculer(modele: str, *, clip: dict | None, n_frames: int, tache: str | None, resolution: str | None,
             duree_plan: float) -> dict:
    """Le DEVIS (sans E/S) : {secondes_entree, secondes_sortie, resolution, tache, op, usd}. Seedance « editing » :
    la sortie suit le clip ; « reference » : la durée du plan, bornée 4-30 s. Veo références : 8 s natifs."""
    from app.services import pricing as _pr
    m = VR.REGISTRE_REFS[modele]
    if m["grammaire"] == "video":
        t = tache if tache in m["taches"] else m["taches"][0]
        res = resolution if resolution in m["resolutions"] else "720p"
        entree = float((clip or {}).get("secondes") or 0)
        if t == "editing":
            sortie = entree
        else:
            d = max(1, int(round(float(duree_plan or 4))))
            sortie = float(d if d in m["durees"] else min(m["durees"], key=lambda x: (abs(x - d), x)))
    else:
        t, entree = None, 0.0
        res = resolution if resolution in (m["resolutions"] or ()) else "720p"
        sortie = float(m["durees"][0])
    op = VR.op_devis(modele, sortie, secondes_entree=entree, resolution=res)
    return {"secondes_entree": round(entree, 3), "secondes_sortie": round(sortie, 3), "resolution": res,
            "tache": t, "op": op, "usd": _pr.estimate(op)["total_usd"]}


# ─────────────────────────────────── tir ──────────────────────────────────

async def _upload(path: Path) -> str:                               # couture (celle de sfx_service)
    from app.services import sfx_service as _S
    return await _S._upload(path)


async def _fal_subscribe(endpoint: str, arguments: dict) -> dict:   # couture (celle de sfx_service)
    from app.services import sfx_service as _S
    return await _S._fal_subscribe(endpoint, arguments)


async def _download(url: str, dest: Path) -> None:                  # couture (celle de sfx_service)
    from app.services import sfx_service as _S
    await _S._download(url, dest)


def _url_video(res) -> str | None:
    if not isinstance(res, dict):
        return None
    v = res.get("video")
    if isinstance(v, dict) and v.get("url"):
        return str(v["url"])
    if isinstance(v, str) and v.startswith("http"):
        return v
    u = res.get("video_url") or res.get("url")
    return str(u) if u else None


async def tirer_previs(modele: str, *, clip: Path | None, frames: list[Path], prompt: str, tache: str | None,
                       resolution: str | None, duree: int, dossier: Path | None = None) -> dict:
    """Tire UN rendu du registre et range la vidéo. PAYANT : la route a passé la clé (503), la confirmation (409) et
    la garde des plafonds AVANT. Le clip et les style frames partent par `_upload` ; la vidéo rendue -> `dossier`
    (outputs/uploads par défaut, où « video_filename » la retrouve) sous `previs_<hex8>.mp4`.
    Rend {video: Path, seed, endpoint, arguments (sans URL), notes}. ValueError : requête invalide ; RuntimeError :
    réponse fal sans vidéo."""
    m = VR.REGISTRE_REFS[modele]
    entites = [{"nom": f.name, "face": f"http://a-blanc/{i}"} for i, f in enumerate(frames)]
    VR.construire(modele, prompt, entites, video_url="http://a-blanc/v" if clip else None, tache=tache,
                  duree=duree, resolution=resolution, aspect_ratio="9:16")      # refus AVANT tout envoi
    url_clip = await _upload(Path(clip)) if clip is not None else None
    urls = [await _upload(Path(f)) for f in frames]
    endpoint, args, notes = VR.construire(modele, prompt, [{"nom": f.name, "face": u} for f, u in zip(frames, urls)],
                                          video_url=url_clip, tache=tache, duree=duree, resolution=resolution,
                                          aspect_ratio="9:16")
    sans_url = {k: v for k, v in args.items() if k not in ("video_urls", "image_urls")}
    logger.info("previs → plan [{}] -> {} · {} · notes={}", modele, endpoint, sans_url, notes)
    res = await _fal_subscribe(endpoint, args)
    u = _url_video(res)
    if not u:
        cles = ", ".join(map(str, res)) if isinstance(res, dict) else type(res).__name__
        raise RuntimeError(f"fal.ai ({m['label']}) : aucune vidéo dans la réponse (clés : {cles})")
    d = Path(dossier or (settings.outputs_path / "uploads"))
    d.mkdir(parents=True, exist_ok=True)
    dest = d / f"previs_{uuid4().hex[:8]}.mp4"
    while dest.exists():
        dest = d / f"previs_{uuid4().hex[:8]}_{os.urandom(2).hex()}.mp4"
    await _download(u, dest)
    seed = res.get("seed") if isinstance(res, dict) else None
    return {"video": dest, "seed": seed if isinstance(seed, int) else None, "endpoint": endpoint,
            "arguments": sans_url, "notes": notes}
