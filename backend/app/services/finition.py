"""Finition — spec Magnific §13 phase D, les deux derniers points.

  « Tester upscale seulement après verrouillage du plan ; mesurer gain
    visuel vs coût et dérive. »
  « Générer des exports de montage avec audio séparé, puis comparer au son
    natif du clip. »

Doctrine du module : on MESURE, on ne décrète pas. Aucune fonction ici ne
déclare un gagnant — elles rendent des chiffres comparables et laissent
l'arbitrage à l'humain, comme `asset3d_qc.comparer`.

Deux honnêtetés à garder en tête, écrites aussi dans les réponses :
  1. un upscale n'a PAS de vérité terrain : « meilleur » ne se prouve pas.
     On rend donc deux mesures orthogonales — l'énergie de contours (le
     détail produit) et la dérive au retour (la fidélité à la source) ;
  2. le stem audio est un DÉCODAGE du livrable (l'AAC du mp4), pas un
     master pré-encodage. C'est exactement ce que le spectateur entend,
     donc la bonne référence pour comparer au son natif d'un rush ; ce
     n'est pas un master de mastering.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from loguru import logger

from app.config import settings

TIMEOUT_FFMPEG = 600


def _bin(nom: str) -> str:
    """ffmpeg/ffprobe du PATH, sinon celui embarqué (même règle que
    `effects_preview.ffmpeg_bin`, étendue à ffprobe)."""
    import os
    import shutil
    exe = shutil.which(nom)
    if exe:
        return exe
    cand = os.path.expandvars(
        rf"%LOCALAPPDATA%\DeepotusVideoGen\bin\{nom}.exe")
    return cand if os.path.isfile(cand) else nom


def _run(cmd: list[str], attendu: Path | None = None, timeout: int = TIMEOUT_FFMPEG):
    """Dialecte `montage_service._run_ffmpeg` : check=False, succès jugé sur
    le code ET sur le fichier réellement écrit, queue de stderr en cas d'échec."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"{cmd[0]} a dépassé {timeout} s")
    except (FileNotFoundError, OSError) as e:
        raise RuntimeError(f"{cmd[0]} indisponible : {e}")
    if r.returncode != 0 or (attendu is not None and
                             (not attendu.exists() or attendu.stat().st_size == 0)):
        raise RuntimeError(f"{Path(cmd[0]).stem} a échoué ({r.returncode}) : "
                           f"{(r.stderr or '')[-600:]}")
    return r


# ── piste audio séparée + comparaison de loudness ────────────────────────────

def a_une_piste_audio(path: Path) -> bool:
    """ffprobe : le fichier porte-t-il un flux audio ?"""
    try:
        r = subprocess.run(
            [_bin("ffprobe"), "-v", "error", "-select_streams", "a",
             "-show_entries", "stream=index", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=30)
        return bool((r.stdout or "").strip())
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False


def loudness(path: Path, timeout: int = 300) -> dict:
    """LUFS intégré / true peak / LRA d'un fichier, par le filtre ebur128 —
    le MÊME que POST /api/montage/measure, donc des chiffres comparables.

    Une mesure PAR FICHIER : `parse_ebur128` lit la dernière occurrence du
    résumé dans stderr, deux instances dans une même commande se
    mélangeraient silencieusement.
    """
    from app.services import sfx_service
    if not a_une_piste_audio(path):
        return {"lufs_i": None, "tp": None, "lra": None,
                "note": "aucune piste audio"}
    r = _run([_bin("ffmpeg"), "-hide_banner", "-nostats", "-i", str(path),
              "-map", "0:a:0", "-af", "ebur128=peak=true:framelog=verbose",
              "-f", "null", "-"], timeout=timeout)
    return dict(sfx_service.parse_ebur128(r.stderr))


def separer(video: Path, out_dir: Path, stem: str | None = None) -> dict:
    """Un montage → une vidéo MUETTE + un stem audio WAV.

    La vidéo muette est produite en `-c:v copy` : les octets vidéo du
    livrable, à l'identique, aucun réencodage. Le WAV est le DÉCODAGE de la
    piste livrée (PCM 48 kHz stéréo) — voir l'avertissement du module.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    base = stem or video.stem
    muet = out_dir / f"{base}_muet.mp4"
    wav = out_dir / f"{base}_stem.wav"

    _run([_bin("ffmpeg"), "-y", "-i", str(video), "-an", "-c:v", "copy",
          "-movflags", "+faststart", str(muet)], attendu=muet)

    out = {"video_muette": muet.name, "video_muette_bytes": muet.stat().st_size,
           "fidelite": "decode_du_livrable"}
    if a_une_piste_audio(video):
        _run([_bin("ffmpeg"), "-y", "-i", str(video), "-vn",
              "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", str(wav)],
             attendu=wav)
        out["stem_audio"] = wav.name
        out["stem_bytes"] = wav.stat().st_size
        out["stem_loudness"] = loudness(wav)
    else:
        out["stem_audio"] = None
        out["note"] = "le montage n'a pas de piste audio — aucun stem produit"
    return out


def comparer_audio(montage: Path, natif: Path) -> dict:
    """Compare le son du montage à celui d'un rush — la question exacte de la
    phase D : « comparer au son natif du clip ».

    Rend les deux mesures et leurs écarts. Un écart de LUFS dit de combien le
    mixage a poussé ou retenu la source ; un true peak au-dessus de -1 dBFS
    annonce un écrêtage à l'encodage de diffusion.
    """
    a, b = loudness(montage), loudness(natif)

    def _d(k):
        if a.get(k) is None or b.get(k) is None:
            return None
        return round(float(a[k]) - float(b[k]), 2)

    return {
        "montage": {"file": montage.name, **a},
        "natif": {"file": natif.name, **b},
        "deltas": {"lufs_i": _d("lufs_i"), "tp": _d("tp"), "lra": _d("lra")},
        "alertes": [m for m in (
            ("true peak du montage au-dessus de -1 dBFS — risque d'écrêtage"
             if (a.get("tp") is not None and float(a["tp"]) > -1.0) else None),
            ("le montage est plus de 6 LUFS sous le rush — le mixage écrase "
             "peut-être la source"
             if (_d("lufs_i") is not None and _d("lufs_i") < -6) else None),
            ("le montage est plus de 6 LUFS au-dessus du rush — gain agressif"
             if (_d("lufs_i") is not None and _d("lufs_i") > 6) else None),
        ) if m],
    }


# ── upscale : gain visuel, dérive, coût ──────────────────────────────────────

def nettete(path: Path, cote: int = 1024) -> float:
    """Densité d'énergie de contours (0-100). Filtre FIND_EDGES puis
    écart-type — le même esprit que `pixel_ops.seam_score`, en PIL pur.

    Portée exacte de la normalisation, et ce n'est pas une nuance : au-dessus
    de `cote`, l'image est RÉDUITE avant mesure, ce qui évite qu'une très
    grande image gagne mécaniquement. En dessous, `thumbnail` ne fait rien —
    la mesure reste donc dépendante de la taille. C'est pourquoi
    `mesurer_variante` ne compare `nettete` qu'ENTRE variantes, qui sortent
    toutes à la même taille cible : là, la comparaison est légitime. Comparer
    la valeur d'une image à celle d'une image d'une autre taille ne l'est pas.
    """
    from PIL import Image, ImageFilter, ImageStat
    im = Image.open(path).convert("L")
    if max(im.size) > cote:
        im.thumbnail((cote, cote), Image.LANCZOS)
    st = ImageStat.Stat(im.filter(ImageFilter.FIND_EDGES))
    return round(min(100.0, st.stddev[0] * 100.0 / 128.0), 2)


def derive(source: Path, agrandie: Path) -> float:
    """Dérive au retour (0-100, 0 = fidèle).

    L'image agrandie est ramenée à la taille de la source et comparée pixel à
    pixel. Un agrandisseur fidèle revient près de la source ; un agrandisseur
    qui INVENTE du détail s'en écarte. Ce n'est pas un verdict de qualité —
    une dérive élevée peut être un beau détail inventé comme un artefact —
    c'est la mesure de ce qui a été ajouté.
    """
    from PIL import Image, ImageChops, ImageStat
    a = Image.open(source).convert("RGB")
    b = Image.open(agrandie).convert("RGB").resize(a.size, Image.LANCZOS)
    st = ImageStat.Stat(ImageChops.difference(a, b))
    return round(min(100.0, sum(st.mean) / 3.0 * 100.0 / 255.0), 2)


def fiche_image(path: Path) -> dict:
    from PIL import Image
    with Image.open(path) as im:
        w, h = im.size
    return {"file": path.name, "w": w, "h": h, "px": w * h,
            "bytes": path.stat().st_size}


def mesurer_variante(source: Path, produite: Path, *, mode: str,
                     scale: int, usd) -> dict:
    """Une variante d'agrandissement, mesurée face à sa source.

    Deux niveaux de lecture, et il faut les distinguer :
      • `nettete` se compare ENTRE VARIANTES — elles sortent toutes à la même
        taille cible depuis la même source, donc les chiffres sont
        directement comparables. C'est la mesure qui départage.
      • `gain_nettete` compare à la source, qui n'a PAS la même taille : il
        est indicatif, pas décisif. Un agrandissement bicubique/Lanczos le
        rend négatif (il lisse, il n'invente rien) — c'est normal, pas un
        défaut. `nettete_source` est rendue pour que ce soit lisible.
    """
    f = fiche_image(produite)
    n_src, n_out = nettete(source), nettete(produite)
    return {
        **f, "mode": mode, "scale": scale,
        "nettete": n_out,
        "nettete_source": n_src,
        "gain_nettete": round(n_out - n_src, 2),
        "derive": derive(source, produite),
        "usd": usd,
        "usd_par_point_de_nettete": (
            round(usd / (n_out - n_src), 4)
            if (usd not in (None, 0) and (n_out - n_src) > 0) else None),
    }
