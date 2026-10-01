"""Plan Quick T7 (tâche #54, D1, 01/10/2026) — la galerie de mouvements et de styles : 11 caméras × 3 styles rendus
UNE fois, LOCALEMENT, par ffmpeg, sur une image fixe.

Ce que ces vignettes sont : un mémo visuel du vocabulaire — ce que « dolly zoom » ou « ugc_raw » veut dire, avant
d'écrire le prompt. Ce qu'elles ne sont PAS : une prédiction du rendu du modèle. Personne n'offre 33 clips gratuits ;
le panneau écrit cette phrase à l'écran, sinon la galerie ment.

Les filtres sont des approximations assumées : `orbit` est un balancement horizontal, `dolly zoom` un zoom sans
correction de perspective, `rack focus` un flou qui se lève. Le nom reste celui de CameraMove, parce que c'est ce
mot-là qui partira dans le prompt. Écart au plan : l'image est d'abord RECADRÉE en 9:16 (une image carrée n'est
plus déformée). Aucun numpy : ffmpeg + Pillow seulement.
"""
import hashlib
import json
import subprocess
from pathlib import Path

from loguru import logger

from app.config import settings
from app.services.effects_preview import ffmpeg_bin

FPS, SECS, W, H = 24, 2.0, 540, 960
_N = int(FPS * SECS) - 1                       # dernier index de trame (47)
_C = "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
_CADRE = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"

#: CameraMove.value -> (expression zoompan, filtre additionnel éventuel)
CAMERAS: dict = {
    "slow push-in":        (f"z='1+0.18*on/{_N}':{_C}", ""),
    "slow pull-out":       (f"z='1.18-0.18*on/{_N}':{_C}", ""),
    "360-degree orbit":    (f"z='1.15':x='iw/2-(iw/zoom/2)+0.06*iw*sin(2*PI*on/{_N})'"
                            ":y='ih/2-(ih/zoom/2)'", ""),
    "tracking shot":       (f"z='1.12':x='(iw-iw/zoom)*on/{_N}'"
                            ":y='ih/2-(ih/zoom/2)'", ""),
    "handheld with subtle shake":
                           (f"z='1.08':x='iw/2-(iw/zoom/2)+0.012*iw*sin(9*on/{_N})'"
                            f":y='ih/2-(ih/zoom/2)+0.012*ih*cos(7*on/{_N})'", ""),
    "static, locked-off":  (f"z='1':{_C}", ""),
    "low angle dramatic":  (f"z='1.20':x='iw/2-(iw/zoom/2)'"
                            f":y='(ih-ih/zoom)*(1-on/{_N})'", ""),
    "rack focus reveal":   (f"z='1.05':{_C}", "boxblur=6:enable='lt(t,0.9)'"),
    "dolly zoom (vertigo effect)":
                           (f"z='1+0.30*on/{_N}':{_C}", ""),
    "whip pan transition": (f"z='1.25':x='(iw-iw/zoom)*min(1,max(0,(on-18)/12))'"
                            ":y='ih/2-(ih/zoom/2)'",
                            "boxblur=8:enable='between(t,0.75,1.25)'"),
    "crane shot descending":
                           (f"z='1.15':x='iw/2-(iw/zoom/2)':y='(ih-ih/zoom)*on/{_N}'", ""),
}

#: StylePreset.value -> étalonnage
GRADES: dict = {
    "cinematic": "eq=contrast=1.12:saturation=1.05",
    "ugc_raw": "eq=contrast=0.98:saturation=1.12:brightness=0.02,noise=alls=8:allf=t",
    "hybrid": "eq=contrast=1.05:saturation=1.08",
}

NOTE = "Vignettes rendues localement par ffmpeg sur une image fixe : elles montrent le mot, pas le rendu du modèle."


def gallery_dir() -> Path:
    d = settings.outputs_path / "_gallery"
    d.mkdir(parents=True, exist_ok=True)
    return d


def tile_id(camera: str, style: str) -> str:
    return hashlib.sha1(f"{camera}|{style}".encode("utf-8")).hexdigest()[:12]


def tile_path(tid: str) -> Path:
    return gallery_dir() / f"{Path(str(tid)).name}.mp4"


def manifest_path() -> Path:
    return gallery_dir() / "manifest.json"


def _render(src: Path, camera: str, style: str) -> Path:
    z, extra = CAMERAS[camera]
    chain = (_CADRE + f"zoompan={z}:d=1:s={W}x{H}:fps={FPS}," + GRADES[style]
             + (("," + extra) if extra else "") + ",setsar=1")
    out = tile_path(tile_id(camera, style))
    r = subprocess.run(
        [ffmpeg_bin(), "-y", "-v", "error", "-loop", "1", "-t", str(SECS),
         "-i", str(src), "-vf", chain, "-r", str(FPS), "-an",
         "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "22", "-movflags", "+faststart", str(out)],
        capture_output=True, timeout=300)
    if r.returncode != 0 or not out.is_file():
        raise RuntimeError(f"Vignette {camera}/{style} : " + r.stderr.decode("utf-8", "replace")[-300:])
    return out


def build(image_path, only: list | None = None) -> dict:
    """Rend les vignettes manquantes et écrit le manifeste. Idempotent : une vignette déjà rendue depuis LA MÊME
    image source n'est pas refaite."""
    src = Path(image_path)
    if not src.is_file():
        raise ValueError(f"Image de marque introuvable : {src.name}")
    sig = hashlib.sha1(src.read_bytes()).hexdigest()[:16]
    ancien = {}
    if manifest_path().is_file():
        try:
            ancien = json.loads(manifest_path().read_text("utf-8"))
        except ValueError:
            ancien = {}
    frais = ancien.get("source_sha1") == sig
    paires = only or [(c, s) for c in CAMERAS for s in GRADES]
    tiles = []
    for camera, style in paires:
        tid = tile_id(camera, style)
        if not (frais and tile_path(tid).is_file()):
            _render(src, camera, style)
        # ?v= : l'empreinte de la source change l'URL quand la galerie est re-rendue sur une autre image — sans
        # elle, le navigateur rejouait l'ANCIENNE vignette depuis son cache (preuve écran du 01/10).
        tiles.append({"id": tid, "camera": camera, "style": style, "url": f"/api/quick/gallery/{tid}?v={sig}"})
    man = {"source": src.name, "source_sha1": sig, "n": len(tiles), "tiles": tiles, "note": NOTE}
    manifest_path().write_text(json.dumps(man, ensure_ascii=False), encoding="utf-8")
    logger.info(f"quick_gallery: {len(tiles)} vignette(s) prêtes ({src.name})")
    return man
