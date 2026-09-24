# -*- coding: utf-8 -*-
"""D-28 (L5) — ACCORD DE COULEUR entre deux plans du Montage.

Statistiques YCbCr d'une image (PIL, sans numpy) et transfert affine par
canal (Reinhard réduit : gain = écart-type réf / cible borné 0,5..2), émis
par l'effet `colormatch` du moteur (`lutyuv`, forme PIVOTÉE autour de 128 :
`(val-128)·G + 128 + O`, décision du contrôleur du 24/09/2026 après la revue
de T1 — la forme `val·G + O` agissait autour de 0 sur U/V et teintait les
gris dès que G ≠ 1).

PLAGE LIMITÉE, et c'est tout le sujet (faits mesurés du plan L5) : `lutyuv`
voit le flux yuv420p du rendu, en plage LIMITÉE (0x808080 → Y = 126) ;
`Image.convert("YCbCr")` de PIL est en plage PLEINE (JPEG). Les moyennes
sont donc ramenées en plage limitée — `Y = 16 + Y_pl·219/255`,
`C = 128 + (C_pl−128)·224/255`, écarts-types multipliés par 219/255 et
224/255 — sinon le décalage calculé serait faux d'environ 10 % sur Y.
MESURÉ (24/09/2026, 8.1.1 = 9.0.1, scratchpad/mesure_t3.py) contre le yuv444p
BRUT de la même image : Y plus bas de 1,0 à 1,5 niveau par le chemin PIL
(double arrondi rgb24), U/V à 0,5 près — sous la tolérance de 6/255 de
l'accord, et le même biais frappe la référence et la cible.

L'image lue est celle de `grading.graded_frame` (sans effet, 256 px) : même
extraction, même `format=yuv420p` que le rendu, même cache.
"""
from __future__ import annotations

from pathlib import Path

_W_STATS = 256            # largeur de l'image analysée (ne change rien aux moyennes)
_G_MIN, _G_MAX = 0.5, 2.0  # bornes du gain (celles du moteur, `_colormatch`)
_O_MAX = 128.0            # |décalage| (celle du moteur)
_SIG_MIN = 0.5            # écart-type sous lequel un gain n'a pas de sens
# auto : écart-type de Y visé au moins (48 en plage pleine, cf. plan D-28).
_SIG_Y_AUTO = 48.0 * 219.0 / 255.0


def image_stats(png) -> dict:
    """{"y": (moy, σ), "u": …, "v": …} d'une IMAGE, en plage LIMITÉE."""
    from PIL import Image, ImageStat
    with Image.open(Path(png)) as im:
        st = ImageStat.Stat(im.convert("RGB").convert("YCbCr"))
    ky, kc = 219.0 / 255.0, 224.0 / 255.0
    (my, mu, mv), (sy, su, sv) = st.mean[:3], st.stddev[:3]
    r = lambda v: round(float(v), 3)                      # noqa: E731
    return {"y": (r(16.0 + my * ky), r(sy * ky)),
            "u": (r(128.0 + (mu - 128.0) * kc), r(su * kc)),
            "v": (r(128.0 + (mv - 128.0) * kc), r(sv * kc))}


def frame_stats(path, t: float = 1.0) -> dict:
    """Statistiques de l'image de `path` à `t` s (au-delà de la durée : la
    dernière image lisible, voir `grading`). `MediaError` si illisible."""
    from app.services import grading
    return image_stats(grading.graded_frame(path, t, None, None, _W_STATS, "png"))


def _canal(mr: float, sr: float, mt: float, st: float) -> tuple[float, float]:
    """(G, O) d'un canal, forme pivotée : sortie = (val−128)·G + 128 + O.

    G = σr/σt borné [0,5 ; 2] (1 si un des écarts-types est nul : un aplat
    n'a pas de contraste à accorder). O = (μr−128) − G·(μt−128). Si O sort de
    [−128 ; 128], on RAMÈNE G dans l'intervalle qui garde |O| ≤ 128 (priorité
    à la MOYENNE : un gain borné puis un décalage borné ratent la moyenne de
    80 niveaux sur un Y 60 → 200, voir le banc) ; si cet intervalle ne
    rencontre pas [0,5 ; 2], G prend la borne la plus proche et O est borné."""
    a, b = mr - 128.0, mt - 128.0
    g = 1.0 if (st < _SIG_MIN or sr < _SIG_MIN) else max(_G_MIN, min(_G_MAX, sr / st))
    o = a - g * b
    if abs(o) > _O_MAX and abs(b) > 1e-9:
        lo, hi = sorted(((a - _O_MAX) / b, (a + _O_MAX) / b))
        lo, hi = max(lo, _G_MIN), min(hi, _G_MAX)
        if lo <= hi:
            g = min(max(g, lo), hi)
        else:
            g = _G_MIN if hi < _G_MIN else _G_MAX
        o = a - g * b
    o = max(-_O_MAX, min(_O_MAX, o))
    return round(g, 3), round(o, 3)


def _effet(canaux: dict) -> dict:
    out = {"type": "colormatch"}
    for k in "yuv":
        out[f"{k}_gain"], out[f"{k}_off"] = canaux[k]
    return out


def match_effect(ref: dict, tgt: dict) -> dict:
    """L'effet `colormatch` qui aligne `tgt` sur `ref` (stats `frame_stats`)."""
    return _effet({k: _canal(float(ref[k][0]), float(ref[k][1]),
                             float(tgt[k][0]), float(tgt[k][1])) for k in "yuv"})


def auto_effect(tgt: dict) -> dict:
    """Correction AUTOMATIQUE vers des cibles neutres : U, V moyens → 128
    (sans toucher à leur écart-type), moyenne de Y conservée, écart-type de Y
    relevé à 48 (plage pleine) au moins. Un plan neutre n'est donc jamais
    teinté (décalages chroma nuls)."""
    my, sy = float(tgt["y"][0]), float(tgt["y"][1])
    ref = {"y": (my, max(sy, _SIG_Y_AUTO)),
           "u": (128.0, float(tgt["u"][1])),
           "v": (128.0, float(tgt["v"][1]))}
    return match_effect(ref, tgt)
