# -*- coding: utf-8 -*-
"""D-30 (L5) — masque STATIQUE d'un clip du Montage : rectangle ou ellipse.

Pur, sans ffmpeg : `mask_of` borne le champ `mask` d'un clip, `mask_graph`
rend UNE instruction de filtergraph qui fabrique le masque. Le masque limite
la PILE D'EFFETS du clip (V1 : split → effets → alphamerge → overlay ; V2 :
maskedmerge — voir montage_service).

Mesures (24/09/2026, ffmpeg 9.0.1 = 8.1.1, 1280×720, 3 s) :
  - `geq` recalculé à chaque image : 2,19 s contre 0,29 s plein cadre (×7) →
    PROSCRIT ; calculé UNE fois (`d=1` + `trim=end_frame=1`) puis bouclé
    (`loop=loop=-1:size=1:start=0`) : 0,36 s, ellipse douce exacte ;
  - `drawbox color=white` en gray écrit 235 (plage limitée) : masque plafonné
    à 92 % → jamais de drawbox ici ;
  - `min()` de ffmpeg n'accepte que DEUX arguments (la forme à trois rend
    « Error initializing filters ») → imbrication ;
  - V2 (T2) : `maskedmerge` n'a PAS d'option `shortest` et un masque bouclé à
    l'infini ne finit jamais (77 022 images en 20 s) ; une image UNIQUE est
    répétée par le framesync (eof_action=repeat) : 60 images pour 2 s à 30
    i/s → `loop=False`. En gris, gray → gbrap donne un alpha 255 : le masque
    V2 porte les QUATRE plans (r, g, b, a) sinon un effet qui change l'alpha
    (chromakey) s'appliquerait hors du masque.
"""
from __future__ import annotations

import math

SHAPES = ("rect", "ellipse")


def _f(v):
    """float fini ou None. Un booléen n'est PAS un nombre (float(True) vaut
    1.0 : un `x: false` passait pour 0) -> None, comme une valeur illisible."""
    if isinstance(v, bool):
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def mask_of(raw) -> dict | None:
    """{shape,x,y,w,h,soft,inv} borné : x,y ∈ [0,1], w,h ∈ [0.01, 1-x|1-y],
    soft ∈ [0,0.5], inv bool (True seulement pour le booléen True) ; forme
    inconnue / non dict / coordonnée illisible (booléen compris) / w|h < 0.01
    -> None ; soft illisible ou booléen -> 0. Arrondi 1e-4."""
    if not isinstance(raw, dict) or raw.get("shape") not in SHAPES:
        return None
    x, y, w, h = (_f(raw.get(k)) for k in ("x", "y", "w", "h"))
    if None in (x, y, w, h):
        return None
    x, y = min(1.0, max(0.0, x)), min(1.0, max(0.0, y))
    w, h = min(w, 1.0 - x), min(h, 1.0 - y)
    if w < 0.01 or h < 0.01:
        return None
    soft = _f(raw.get("soft"))
    soft = 0.0 if soft is None else min(0.5, max(0.0, soft))
    r4 = lambda v: round(v, 4)                                  # noqa: E731
    return {"shape": raw["shape"], "x": r4(x), "y": r4(y), "w": r4(w), "h": r4(h),
            "soft": r4(soft), "inv": raw.get("inv") is True}


def _n(v) -> str:
    """Nombre court pour le filtergraph (entier sans décimale)."""
    v = round(float(v), 3)
    return str(int(v)) if v == int(v) else repr(v)


def _expr(m: dict, w: int, h: int) -> str:
    x0, x1 = m["x"] * w, (m["x"] + m["w"]) * w
    y0, y1 = m["y"] * h, (m["y"] + m["h"]) * h
    if m["shape"] == "ellipse":
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        rx, ry = max((x1 - x0) / 2.0, 0.5), max((y1 - y0) / 2.0, 0.5)
        s = max(m["soft"] * 2.0, 0.002)                 # fraction du rayon
        e = (f"255*clip((1-hypot((X-{_n(cx)})/{_n(rx)},(Y-{_n(cy)})/{_n(ry)}))"
             f"/{_n(s)},0,1)")
    else:
        sp = max(m["soft"] * min(x1 - x0, y1 - y0), 1.0)  # pixels
        e = (f"255*clip(min(min(X-{_n(x0)},{_n(x1)}-X),min(Y-{_n(y0)},{_n(y1)}-Y))"
             f"/{_n(sp)},0,1)")
    return f"255-({e})" if m["inv"] else e


def mask_graph(m: dict, w: int, h: int, fps, lbl: str, *, planes: str = "gray",
               loop: bool = True) -> str:
    """Une instruction filtergraph qui calcule le masque UNE fois.

    gray (V1) : color=c=black:s={w}x{h}:r={fps}:d=1,format=gray,geq=lum='E',
    trim=end_frame=1,loop=loop=-1:size=1:start=0[{lbl}] ;
    gbrap (V2) : color=c=black@0:…,format=gbrap,geq=r='E':g='E':b='E':a='E',
    trim=end_frame=1[{lbl}] (loop=False : image unique répétée par le
    framesync de maskedmerge).
    ellipse : 255*clip((1-hypot((X-cx)/rx,(Y-cy)/ry))/S,0,1), S = max(soft·2,
    0.002) ; rectangle : 255*clip(min(min(X-x0,x1-X),min(Y-y0,y1-Y))/Sp,0,1),
    Sp = max(soft·min(pw,ph),1) px ; inv -> 255-(…)."""
    e = _expr(m, int(w), int(h))
    if planes == "gbrap":
        head = (f"color=c=black@0:s={int(w)}x{int(h)}:r={_n(fps)}:d=1,format=gbrap,"
                f"geq=r='{e}':g='{e}':b='{e}':a='{e}'")
    else:
        head = (f"color=c=black:s={int(w)}x{int(h)}:r={_n(fps)}:d=1,format=gray,"
                f"geq=lum='{e}'")
    tail = ",trim=end_frame=1" + (",loop=loop=-1:size=1:start=0" if loop else "")
    return f"{head}{tail}[{lbl}]"
