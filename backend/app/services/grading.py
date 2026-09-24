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

LE GRADE EST JUGÉ EN PLEIN : `_pile` retire des effets leurs bornes
temporelles (`t0`, `t1`, `fade_in`, `fade_out`, `ease_in`, `ease_out`) avant
`build_chain`. L'image montrée est donc celle de l'effet tel qu'il
s'applique au cœur de son intervalle, quel que soit le `t` de l'image (un
effet borné 5..6 s reste visible sur l'image de 1 s — sinon le panneau
jugerait un grade qu'il ne montre pas). Un effet `off: true` est ÉTEINT :
`build_chain` ne lit pas `off` (mesuré, revue T3), il est donc retiré avant
la chaîne ET hors de la clé, comme le fait le client (`dzmIsGradeEff`).

DERNIÈRE IMAGE LISIBLE — MESURÉ le 24/09/2026 (8.1.1 = 9.0.1,
scratchpad/mesure_t3.py puis mesure_t3b.py) : `-ss` au-delà de la dernière
image rend ZÉRO image avec un code de sortie 0 (échec muet). 25 i/s sur
2,00 s : 1,95 rend, 2,00 non ; 5 i/s sur 2,00 s : 1,80 rend, 1,85 NON (un
recul fixe de 0,1 s ne suffit pas) ; vidéo 2,00 s + audio 2,30 s :
`format=duration` vaut 2,30 et 2,00 ne rend rien (la durée du CONTENEUR
ment). D'où `_probe` qui lit `stream=duration,r_frame_rate` du flux `v:0`
(repli `format=duration`), `_t_lisible` qui recule à `durée − max(0,1 ;
1/fps)`, UN second essai à `t − 1/fps` si la sortie manque, et un fichier
de sortie absent qui reste une `MediaError`, jamais un succès.

Cache : `outputs/montage_cache` (celui de `montage_media`), clé sha1 de
(chemin résolu, mtime_ns, t demandé, pile NORMALISÉE, mtime des LUT `.cube`
référencées, masque, largeur, format) — le `t` DEMANDÉ et non le `t`
reculé : un second appel identique ne lance donc AUCUN sous-processus ; la
sonde ffprobe est elle-même en mémoire par (chemin résolu, mtime_ns). Un
succès du cache rafraîchit la date du fichier (`os.utime`, LRU approché).
Contrairement aux autres genres de ce dossier (un fichier par source),
celui-ci croît avec chaque réglage essayé : il est ÉLAGUÉ, par motif, après
chaque écriture (`prune_cache`, patron de `effects_preview._prune_cache`).
Écriture atomique (`_tmp_de` + `os.replace`) — et sous Windows `os.replace`
LÈVE `PermissionError [WinError 5]` si la cible est ouverte en lecture
(une `FileResponse` qui la sert, mesuré) : le temporaire est alors effacé
et l'image déjà en place, de même clé donc de même contenu, est rendue.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

from app.services import effects_engine as _fx
from app.services import mask_region as _mr
from app.services import montage_media as _MM

W_DEFAULT = 512
_W_MIN, _W_MAX = 16, 1920
_FPS = 25                      # cadence fictive du contexte d'effets / du masque
_RECUL = 0.1                   # recul MINIMAL ; le vrai est max(0,1 ; 1/fps)
_FMTS = {"png": ".png", "jpg": ".jpg"}
# Élagage : le quota est PAR MOTIF (une rafale d'aperçus ne chasse pas les
# scopes, et réciproquement) ; jamais un autre genre du dossier.
KEEP = {"*_grade.*": 600, "*_scopes.png": 200}
# Clés d'un effet qui ne changent pas l'image jugée : les bornes temporelles
# (le grade est jugé en plein), le libellé, l'identifiant et `off` (un effet
# éteint est retiré de la pile avant tout).
_TEMPS = ("t0", "t1", "fade_in", "fade_out", "ease_in", "ease_out")
_HORS_CLE = frozenset(_TEMPS + ("label", "id", "off"))
_PROBES: dict = {}             # (chemin résolu, mtime_ns) → (durée, w, h, fps)
_PROBES_MAX = 256

# `scale=512:-2` retiré en tête (revue T3 M-2) : l'entrée est DÉJÀ large de
# 512 (`_grade_graph(…, 512, …)`), PNG octet pour octet identique (mesuré).
SCOPES_GRAPH = (
    "format=yuv444p,split=3[sa][sb][sc];"
    "[sa]waveform=mode=column:display=stack:intensity=0.2[sw];"
    "[sb]vectorscope=mode=color2:graticule=green[sv];"
    "[sc]histogram=display_mode=overlay,scale=256:256[sh];"
    "[sv][sh]hstack=inputs=2[svh];[sw][svh]vstack=inputs=2")


def _pile(effects) -> list[dict]:
    """La pile JUGÉE : dicts seulement, effets `off` retirés, et chaque effet
    copié SANS ses clés `_HORS_CLE` (bornes temporelles, libellé, id). Sert
    À LA FOIS à la chaîne et à la clé : ce qui ne change pas l'image ne
    change pas la clé."""
    return [{k: v for k, v in e.items() if k not in _HORS_CLE}
            for e in (effects or []) if isinstance(e, dict) and not e.get("off")]


def _luts(effs) -> list:
    """[(nom, mtime_ns)] des LUT `.cube` référencées ET résolues : la LUT
    réécrite sous le même nom rend une autre image, donc une autre clé."""
    res = []
    for e in effs:
        lut = _fx._lut_path(e.get("file")) if e.get("file") else None
        if lut is not None:
            try:
                res.append((lut.name, lut.stat().st_mtime_ns))
            except OSError:
                res.append((lut.name, None))
    return res


def _cle(path: Path, *parts) -> str:
    try:
        mtime = path.stat().st_mtime_ns
    except OSError as e:
        raise _MM.MediaError("source illisible : %s" % path.name) from e
    brut = json.dumps([str(path.resolve()), mtime] + list(parts),
                      sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha1(brut.encode("utf-8")).hexdigest()[:20]


def _num(v) -> float:
    """Nombre fini ≥ 0 lu d'une valeur ffprobe (« 2.000000 », « 5/1 »), 0 sinon."""
    try:
        if isinstance(v, str) and "/" in v:
            a, b = v.split("/", 1)
            f = float(a) / float(b) if float(b) else 0.0
        else:
            f = float(v)
    except (TypeError, ValueError, ZeroDivisionError):
        return 0.0
    return f if math.isfinite(f) and f > 0 else 0.0


def _probe(path: Path) -> tuple[float, int, int, float]:
    """(durée, largeur, hauteur, i/s) du flux `v:0`. `MediaError` sinon.

    La durée est celle du FLUX vidéo (celle du conteneur inclut l'audio plus
    long : mesuré 2,30 pour une vidéo de 2,00), repli `format=duration`. En
    mémoire par (chemin résolu, mtime_ns), 256 entrées au plus."""
    try:
        cle = (str(path.resolve()), path.stat().st_mtime_ns)
    except OSError:
        cle = None
    if cle is not None and cle in _PROBES:
        return _PROBES[cle]
    r = _MM._run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                  "-show_entries", "stream=width,height,duration,r_frame_rate,avg_frame_rate"
                  ":format=duration", "-of", "json", str(path)],
                 timeout=30, quoi="la lecture de la source")
    try:
        d = json.loads((r.stdout or b"").decode("utf-8", errors="replace") or "{}")
        s = (d.get("streams") or [{}])[0]
        w, h = int(s.get("width") or 0), int(s.get("height") or 0)
        dur = _num(s.get("duration")) or _num((d.get("format") or {}).get("duration"))
        fps = _num(s.get("r_frame_rate")) or _num(s.get("avg_frame_rate"))
    except (ValueError, TypeError, AttributeError):
        w = h = 0
        dur = fps = 0.0
    if w <= 0 or h <= 0:
        raise _MM.MediaError("aucune image décodable dans « %s » — %s"
                             % (path.name, _MM._lignes_utiles(r.stderr)))
    res = (dur, w, h, fps if 0 < fps <= 1000 else float(_FPS))
    if cle is not None:
        if len(_PROBES) >= _PROBES_MAX:
            _PROBES.pop(next(iter(_PROBES)))
        _PROBES[cle] = res
    return res


def _pas(fps: float) -> float:
    """Durée d'une image (s), au moins `_RECUL`."""
    return max(_RECUL, 1.0 / fps) if fps > 0 else _RECUL


def _t_lisible(t: float, dur: float, fps: float = _FPS) -> float:
    """`t` borné à la dernière image lisible : `durée − max(0,1 ; 1/fps)`."""
    t = max(0.0, float(t))
    recul = _pas(fps)
    if dur > 0 and t > dur - recul:
        t = max(0.0, dur - recul)
    return t


def _servi(out: Path) -> Path:
    """Succès du cache : la date du fichier est rafraîchie (LRU approché de
    `prune_cache`, qui garde les plus récents). Jamais d'exception."""
    try:
        os.utime(out)
    except OSError:
        pass
    return out


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


def _efface(p: Path) -> None:
    try:
        p.unlink(missing_ok=True)
    except OSError:
        pass


def _render(path: Path, t: float, parts: list[str], out_lbl: str, out: Path,
            quoi: str, pas: float = 0.0) -> Path:
    """Une image de `path` à `t` par `parts` → `out`. Si ffmpeg réussit SANS
    image (au-delà de la dernière, échec muet mesuré) et `pas` > 0, UN
    second essai à `t − pas`. Cible verrouillée (Windows) : voir l'en-tête."""
    tmp = _MM._tmp_de(out)
    # `-q:v` ne sert qu'au JPEG : sur PNG, octets identiques (mesuré).
    qv = ["-q:v", "3"] if out.suffix.lower() == ".jpg" else []
    essais = [t] + ([max(0.0, t - pas)] if pas > 0 and t > 0 else [])
    for i, te in enumerate(essais):
        r = _MM._run(["ffmpeg", "-y", "-v", "error", "-ss", "%.3f" % te, "-i", str(path),
                      "-filter_complex", ";".join(parts), "-map", f"[{out_lbl}]",
                      "-frames:v", "1"] + qv + [str(tmp)],
                     timeout=120, quoi=quoi)
        vide = r.returncode != 0 or not tmp.exists() or tmp.stat().st_size == 0
        if not vide:
            break
        _efface(tmp)
        if r.returncode != 0 or i == len(essais) - 1:
            raise _MM.MediaError("%s impossible pour « %s » — %s"
                                 % (quoi, path.name, _MM._lignes_utiles(r.stderr) or "aucune image"))
    try:
        res = _MM._ecrire(tmp, out)
    except OSError as e:
        _efface(tmp)
        if not out.exists():
            raise _MM.MediaError("%s impossible pour « %s » — écriture du cache refusée (%s)"
                                 % (quoi, path.name, e.__class__.__name__)) from e
        res = out            # même clé, même contenu : l'image en place fait foi
    prune_cache()
    return res


def graded_frame(path, t, effects=None, mask=None, w: int = W_DEFAULT,
                 fmt: str = "png") -> Path:
    """L'image étalonnée de `path` à `t` s, large de `w` px (paire), en
    `fmt` ("png" | "jpg"). Cache `montage_cache/<sha1>_grade.<ext>`.

    La pile est JUGÉE EN PLEIN : bornes temporelles (`t0`, `t1`, `fade_*`,
    `ease_*`) retirées, effets `off` éteints (voir l'en-tête)."""
    p = Path(path)
    ext = _FMTS.get(str(fmt).lower().lstrip("."), ".png")
    w = _pair(max(_W_MIN, min(_W_MAX, int(w))))
    effs = _pile(effects)
    m = _mr.mask_of(mask)
    out = _MM._cache_dir() / ("%s_grade%s" % (
        _cle(p, "grade", round(float(t), 3), effs, _luts(effs), m, w, ext), ext))
    if out.exists():
        return _servi(out)
    dur, sw, sh, fps = _probe(p)
    h = _haut(w, sw, sh)
    parts = _grade_graph(effs, m, w, h, "gout")
    return _render(p, _t_lisible(t, dur, fps), parts, "gout", out, "l'image étalonnée",
                   pas=_pas(fps))


def scopes_png(path, t, effects=None, mask=None) -> Path:
    """Scopes combinés (waveform, vectorscope, histogramme) 512×512 de
    l'image ÉTALONNÉE de `path` à `t` s. Cache `…_scopes.png`. Même pile
    jugée en plein que `graded_frame` (bornes temporelles retirées, `off`
    éteints)."""
    p = Path(path)
    effs = _pile(effects)
    m = _mr.mask_of(mask)
    out = _MM._cache_dir() / ("%s_scopes.png" % _cle(p, "scopes", round(float(t), 3), effs,
                                                     _luts(effs), m))
    if out.exists():
        return _servi(out)
    dur, sw, sh, fps = _probe(p)
    h = _haut(512, sw, sh)
    parts = _grade_graph(effs, m, 512, h, "gsrc")
    parts.append("[gsrc]" + SCOPES_GRAPH + "[scopes]")
    return _render(p, _t_lisible(t, dur, fps), parts, "scopes", out, "les scopes",
                   pas=_pas(fps))


def prune_cache(keep: dict | None = None) -> dict:
    """Borne le cache de ce module : pour chaque motif, les `n` fichiers les
    plus RÉCENTS survivent. Rend {motif: nombre effacé}. Jamais d'exception ;
    un `unlink` qui échoue (fichier servi, WinError 32) n'arrête pas les
    suivants."""
    res = {}
    for motif, n in (keep or KEEP).items():
        k = 0
        try:
            dates = []
            for f in _MM._cache_dir().glob(motif):
                if ".tmp." in f.name:
                    continue
                try:
                    dates.append((f.stat().st_mtime, f))
                except OSError:
                    pass
            dates.sort(key=lambda x: x[0], reverse=True)
            for _, f in dates[int(n):]:
                try:
                    f.unlink(missing_ok=True)
                    k += 1
                except OSError:
                    pass
        except OSError:
            pass
        res[motif] = k
    return res
