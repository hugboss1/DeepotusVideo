# -*- coding: utf-8 -*-
"""D-31 / D-32 (L5) — IMAGE ÉTALONNÉE d'un instant et SCOPES.

`graded_frame` rend UNE image d'une source vidéo à `t` s, la pile d'effets
d'un clip appliquée comme au rendu du Montage (mise à l'échelle, `setsar=1`,
`format=yuv420p`, PUIS les effets — l'ordre de la chaîne V1 — et, s'il y a un
masque, le même montage que V1 : split → effets → alphamerge du masque
calculé une fois → `overlay=0:0:shortest=1`). Elle sert l'aperçu du panneau
Étalonnage, les vignettes de la lightbox et l'image que lit `color_match`.
`scopes_png` pose le graphe MESURÉ du plan (waveform colonne, vectorscope,
histogramme, 512×512) sur cette image étalonnée : le scope montre ce que le
rendu produira.

MESURÉ le 24/09/2026 (8.1.1 = 9.0.1, scratchpad/mesure_t3.py) sur une vidéo
de 2,00 s à 25 i/s : `-ss 1.95 -frames:v 1` rend une image, `-ss 1.99` (et
au-delà) N'EN REND AUCUNE avec un code de sortie 0 — un échec muet. D'où
`_t_lisible` : au-delà de `durée − 0,1`, on recule à `durée − 0,1` ; et un
fichier de sortie absent est une `MediaError`, jamais un succès.

Cache : `outputs/montage_cache` (celui de `montage_media`), clé sha1 de
(chemin résolu, mtime_ns, t demandé, pile, masque, largeur, format) — le `t`
DEMANDÉ et non le `t` reculé : un second appel identique ne lance donc AUCUN
sous-processus (ni ffprobe ni ffmpeg). Contrairement aux autres genres de ce
dossier (un fichier par source), celui-ci croît avec chaque réglage essayé :
il est ÉLAGUÉ, par motif, après chaque écriture (`prune_cache`, patron de
`effects_preview._prune_cache`). Écriture atomique (`_tmp_de` + `os.replace`).
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from app.services import effects_engine as _fx
from app.services import mask_region as _mr
from app.services import montage_media as _MM

W_DEFAULT = 512
_W_MIN, _W_MAX = 16, 1920
_FPS = 25                      # cadence fictive du contexte d'effets / du masque
_RECUL = 0.1                   # mesuré : durée − 0,1 rend toujours une image
_FMTS = {"png": ".png", "jpg": ".jpg"}
# Élagage : le quota est PAR MOTIF (une rafale d'aperçus ne chasse pas les
# scopes, et réciproquement) ; jamais un autre genre du dossier.
KEEP = {"*_grade.*": 600, "*_scopes.png": 200}

SCOPES_GRAPH = (
    "scale=512:-2,format=yuv444p,split=3[sa][sb][sc];"
    "[sa]waveform=mode=column:display=stack:intensity=0.2[sw];"
    "[sb]vectorscope=mode=color2:graticule=green[sv];"
    "[sc]histogram=display_mode=overlay,scale=256:256[sh];"
    "[sv][sh]hstack=inputs=2[svh];[sw][svh]vstack=inputs=2")


def _cle(path: Path, *parts) -> str:
    try:
        mtime = path.stat().st_mtime_ns
    except OSError as e:
        raise _MM.MediaError("source illisible : %s" % path.name) from e
    brut = json.dumps([str(path.resolve()), mtime] + list(parts),
                      sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha1(brut.encode("utf-8")).hexdigest()[:20]


def _probe(path: Path) -> tuple[float, int, int]:
    """(durée, largeur, hauteur) du premier flux vidéo. `MediaError` sinon."""
    r = _MM._run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                  "-show_entries", "stream=width,height:format=duration",
                  "-of", "json", str(path)], timeout=30, quoi="la lecture de la source")
    try:
        d = json.loads((r.stdout or b"").decode("utf-8", errors="replace") or "{}")
        s = (d.get("streams") or [{}])[0]
        w, h = int(s.get("width") or 0), int(s.get("height") or 0)
        try:
            dur = float((d.get("format") or {}).get("duration") or 0.0)
        except (TypeError, ValueError):
            dur = 0.0
    except (ValueError, TypeError, AttributeError):
        w = h = 0
        dur = 0.0
    if w <= 0 or h <= 0:
        raise _MM.MediaError("aucune image décodable dans « %s » — %s"
                             % (path.name, _MM._lignes_utiles(r.stderr)))
    return (dur if math.isfinite(dur) else 0.0), w, h


def _t_lisible(t: float, dur: float) -> float:
    t = max(0.0, float(t))
    if dur > 0 and t > dur - _RECUL:
        t = max(0.0, dur - _RECUL)
    return t


def _pair(v: int) -> int:
    return max(2, int(v) - int(v) % 2)


def _haut(w: int, sw: int, sh: int) -> int:
    """Hauteur PAIRE la plus proche du rapport de la source (demi arrondi
    vers le haut : 320×180 → 240×136, comme `scale=240:-2`)."""
    return max(2, int(w * sh / sw / 2.0 + 0.5) * 2)


def _grade_graph(effects, mask, w: int, h: int, out: str) -> list[str]:
    """Le graphe `[0:v]` → `[out]` : échelle, yuv420p, pile (masquée)."""
    parts = [f"[0:v]scale={w}:{h},setsar=1,format=yuv420p[gpre]"]
    effs = [e for e in (effects or []) if isinstance(e, dict)]
    ctx = {"w": w, "h": h, "dur": 1.0, "fps": _FPS}
    m = _mr.mask_of(mask) if effs else None
    if effs and m:
        parts.append("[gpre]split[gmo][gme]")
        parts += _fx.build_chain(effs, "gme", "gmf", "gfx", ctx)
        parts.append("[gmf]format=yuva420p[gmfa]")
        parts.append(_mr.mask_graph(m, w, h, _FPS, "gmk"))
        parts.append("[gmfa][gmk]alphamerge[gmm]")
        parts.append(f"[gmo][gmm]overlay=0:0:shortest=1,format=yuv420p[{out}]")
    else:
        parts += _fx.build_chain(effs, "gpre", out, "gfx", ctx)
    return parts


def _render(path: Path, t: float, parts: list[str], out_lbl: str, out: Path,
            quoi: str) -> Path:
    tmp = _MM._tmp_de(out)
    r = _MM._run(["ffmpeg", "-y", "-v", "error", "-ss", "%.3f" % t, "-i", str(path),
                  "-filter_complex", ";".join(parts), "-map", f"[{out_lbl}]",
                  "-frames:v", "1", "-q:v", "3", str(tmp)],
                 timeout=120, quoi=quoi)
    if r.returncode != 0 or not tmp.exists() or tmp.stat().st_size == 0:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise _MM.MediaError("%s impossible pour « %s » — %s"
                             % (quoi, path.name, _MM._lignes_utiles(r.stderr) or "aucune image"))
    res = _MM._ecrire(tmp, out)
    prune_cache()
    return res


def graded_frame(path, t, effects=None, mask=None, w: int = W_DEFAULT,
                 fmt: str = "png") -> Path:
    """L'image étalonnée de `path` à `t` s, large de `w` px (paire), en
    `fmt` ("png" | "jpg"). Cache `montage_cache/<sha1>_grade.<ext>`."""
    p = Path(path)
    ext = _FMTS.get(str(fmt).lower().lstrip("."), ".png")
    w = _pair(max(_W_MIN, min(_W_MAX, int(w))))
    effs = [e for e in (effects or []) if isinstance(e, dict)]
    m = _mr.mask_of(mask)
    out = _MM._cache_dir() / ("%s_grade%s" % (
        _cle(p, "grade", round(float(t), 3), effs, m, w, ext), ext))
    if out.exists():
        return out
    dur, sw, sh = _probe(p)
    h = _haut(w, sw, sh)
    parts = _grade_graph(effs, m, w, h, "gout")
    return _render(p, _t_lisible(t, dur), parts, "gout", out, "l'image étalonnée")


def scopes_png(path, t, effects=None, mask=None) -> Path:
    """Scopes combinés (waveform, vectorscope, histogramme) 512×512 de
    l'image ÉTALONNÉE de `path` à `t` s. Cache `…_scopes.png`."""
    p = Path(path)
    effs = [e for e in (effects or []) if isinstance(e, dict)]
    m = _mr.mask_of(mask)
    out = _MM._cache_dir() / ("%s_scopes.png" % _cle(p, "scopes", round(float(t), 3), effs, m))
    if out.exists():
        return out
    dur, sw, sh = _probe(p)
    h = _haut(512, sw, sh)
    parts = _grade_graph(effs, m, 512, h, "gsrc")
    parts.append("[gsrc]" + SCOPES_GRAPH + "[scopes]")
    return _render(p, _t_lisible(t, dur), parts, "scopes", out, "les scopes")


def prune_cache(keep: dict | None = None) -> dict:
    """Borne le cache de ce module : pour chaque motif, les `n` fichiers les
    plus RÉCENTS survivent. Rend {motif: nombre effacé}. Jamais d'exception."""
    res = {}
    for motif, n in (keep or KEEP).items():
        k = 0
        try:
            files = sorted((f for f in _MM._cache_dir().glob(motif) if ".tmp." not in f.name),
                           key=lambda f: f.stat().st_mtime, reverse=True)
            for f in files[int(n):]:
                f.unlink(missing_ok=True)
                k += 1
        except OSError:
            pass
        res[motif] = k
    return res
