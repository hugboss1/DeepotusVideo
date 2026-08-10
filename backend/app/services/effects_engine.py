"""Studio Effects/Mask engine.

Turns an "effect spec" (JSON, from the Studio Effects node) into an ffmpeg
filtergraph chain. Every effect is a PURE filter chain (no external input:
LUTs use lut3d=file, gradients use the `gradients` source filter) so it drops
straight into build_ffmpeg_command — applied either to ONE region's stream
(per-layer masking) or to the final composited frame (global post-pass).

Public API:
    build_chain(effects, in_lbl, out_lbl, uid, ctx) -> list[str]   # filtergraph statements
    catalog() -> dict                                              # for the Studio panel
Each effect dict: {"type": <name>, "intensity": 0..100, ...params}.
"""
from __future__ import annotations
import math


def _clamp01(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v


def _inten(eff, default=60):
    try:
        return _clamp01(float(eff.get("intensity", default)) / 100.0)
    except (TypeError, ValueError):
        return default / 100.0


def _c(hexstr, default="ffffff"):
    s = str(hexstr or "").lstrip("#").strip() or default
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) != 6:
        s = default
    return "0x" + s.lower()


def _one(i, o, filt):
    return [f"[{i}]{filt}[{o}]"]


#: Modes de fusion proposés. Liste blanche : la valeur part telle quelle dans
#: `-filter_complex`, un mode inventé casserait tout le rendu.
BLEND_MODES = ("screen", "overlay", "softlight", "hardlight", "multiply",
               "lighten", "darken", "addition", "difference", "normal")


def _blend_mode(v):
    m = str(v or "screen").strip().lower()
    return m if m in BLEND_MODES else "screen"


def _num(eff, key, default, lo, hi):
    """Paramètre numérique borné (une valeur absurde venant du client ne doit
    jamais atteindre la ligne de commande ffmpeg)."""
    try:
        v = float(eff.get(key, default))
    except (TypeError, ValueError):
        return float(default)
    if v != v:                                    # NaN
        return float(default)
    return lo if v < lo else hi if v > hi else v


def _even(v):
    """Dimension paire : hstack/vstack/blend refusent deux entrées de tailles
    différentes, et une division entière impaire décale d'un pixel."""
    return max(2, int(v) // 2 * 2)


def _pt(v, hi):
    """Coordonnée d'un point de `gradients`, ramenée DANS l'image.

    Le filtre refuse une valeur hors [0, dimension] et fait échouer tout le
    rendu (« Result too large ») : un angle de fuite de lumière de 200° suffit
    à sortir du cadre. Mesuré sur GET /api/effects/preview.
    """
    return int(max(0, min(hi - 1, v)))


def _fps(ctx):
    """Cadence du rendu.

    Toute source synthétique (`gradients`, `color`) apporte SA propre cadence
    (25 i/s par défaut). Or `blend` prend la base de temps de sa PREMIÈRE
    entrée : une nappe à 25 i/s en première entrée re-cadence tout le clip à
    25 i/s, que `-r 30` re-duplique ensuite — un décalage temporel mesurable
    sur TOUTE la durée, y compris hors de [t0,t1] (mesuré : ~1,6/255 d'écart
    moyen, saccade à l'oeil). Les sources doivent donc porter `r=` la cadence
    du rendu. 30 = valeur du canevas par défaut de l'app, les appelants
    passent la vraie.
    """
    try:
        f = int(float((ctx or {}).get("fps") or 0))
    except (TypeError, ValueError):
        f = 0
    return f if 1 <= f <= 240 else 30


# ---- fusion en RGB ----------------------------------------------------------
#
# `blend` travaille PLAN PAR PLAN. Sur un flux yuv420p, un mode « screen » ou
# « softlight » s'applique donc aussi à U et V : le neutre 128 est repoussé
# vers 191 et l'image entière vire au magenta (mesuré sur la mire — un simple
# screen d'une image sur elle-même suffit à la détruire).
#
# Tout effet qui fusionne deux couches passe donc en gbrp AVANT le blend : le
# mode s'applique alors aux vraies composantes R/G/B. Le fondu dry/wet de
# `_timed` n'est pas concerné (mode `normal` = interpolation linéaire, juste
# dans les deux espaces).
#
# ATTENTION au placement : un `format=gbrp` posé en TÊTE de branche ne tient
# pas. `eq`, `curves`, `vignette` et `noise` n'acceptent que du YUV, ffmpeg
# insère donc une conversion, et `blend` — qui accepte les deux — adopte
# ensuite le format de sa PREMIÈRE entrée. Le même effet virait au magenta ou
# non selon l'ordre des entrées du blend. `format=gbrp` doit donc être le
# DERNIER filtre de CHACUNE des deux branches : les deux entrées sont alors
# figées et `blend` n'a plus le choix (vérifié au rendu, log `auto_scale`).
_RGB = "format=gbrp"


def _lut_path(name):
    """Resolve a user LUT name to a .cube inside the LUT folder, or None.

    The value lands inside a -filter_complex argument, where a quote ends the
    filter and lets the rest inject arbitrary filtergraph statements (movie=
    reads any local file into the render). So: basename only, .cube only, and
    it must already exist under the LUT dir — nothing else reaches ffmpeg.
    """
    if not name:
        return None
    from pathlib import Path
    from app.config import settings
    safe = Path(str(name)).name
    if not safe or safe != str(name) or not safe.lower().endswith(".cube"):
        return None
    p = settings.luts_path / safe
    return p if p.is_file() else None


# ---- LUT / grade presets (ffmpeg-native, no .cube needed) -------------------
GRADES = {
    "teal_orange": "curves=preset=increase_contrast,colorbalance=rs=-0.08:bs=0.10:gm=0.02:rm=0.06:bm=-0.06,eq=saturation=1.15",
    "cyberpunk":   "colorbalance=rs=0.06:bs=0.20:gm=-0.05,eq=saturation=1.4:contrast=1.1,hue=h=-8",
    "deepsea":     "colorbalance=bs=0.20:gs=0.08:rs=-0.14,eq=saturation=1.12:contrast=1.05,hue=h=6",
    "noir":        "hue=s=0,curves=preset=strong_contrast,eq=brightness=-0.02",
    "warm":        "colorbalance=rs=0.12:rm=0.06:bs=-0.08,eq=saturation=1.1",
    "cold":        "colorbalance=bs=0.14:bm=0.05:rs=-0.06,eq=saturation=1.05",
    "vintage":     "curves=preset=vintage",
    "cross":       "curves=preset=cross_process",
    "matrix":      "hue=s=0,colorbalance=gs=0.22:gm=0.28:gh=0.22,eq=contrast=1.2",
    "faded":       "curves=r='0/0.06 1/0.92':g='0/0.06 1/0.92':b='0/0.10 1/0.90',eq=saturation=0.85",
}

# ---- Colorize presets --------------------------------------------------------
COLORIZE = {
    "sepia":   "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131",
    "bw":      "hue=s=0",
    "duotone": "hue=s=0,colorbalance=rs=0.15:bs=0.10:rm=-0.08:bm=0.20:rh=-0.10:gh=0.06:bh=0.30",
    "matrix":  "hue=s=0,colorbalance=gs=0.28:gm=0.30:gh=0.28,eq=contrast=1.2",
    "redalert":"hue=s=0,colorbalance=rs=0.30:rm=0.30:rh=0.25,eq=contrast=1.15",
    "gold":    "hue=s=0,colorbalance=rs=0.20:gm=0.10:rm=0.15:bs=-0.15",
}


# ---- effect builders : (eff, in_lbl, out_lbl, uid, ctx) -> [statements] ------
def _grade(eff, i, o, u, ctx):
    lut = _lut_path(eff.get("file"))
    if lut:                                   # user .cube LUT
        f = str(lut).replace("\\", "/").replace(":", "\\:")
        return _one(i, o, f"lut3d=file='{f}'")
    return _one(i, o, GRADES.get(eff.get("preset", "teal_orange"), GRADES["teal_orange"]))


def _colorize(eff, i, o, u, ctx):
    base = COLORIZE.get(eff.get("preset", "duotone"), COLORIZE["duotone"])
    t = _inten(eff, 100)
    # mix strength via saturation/contrast nudge
    return _one(i, o, f"{base},eq=saturation={0.6 + 0.6 * t:.2f}")


def _vhs(eff, i, o, u, ctx):
    t = _inten(eff, 60)
    sp = _clamp01(float(eff.get("speed", 50)) / 100.0)
    w, h = ctx["w"], ctx["h"]
    amp = 2 + 16 * t                          # px displacement
    v = 1.5 + 9 * sp                          # temporal speed (sequenceable)
    f = 6                                     # spatial frequency (lines)
    ph = f"(Y/H)*{f}*2*PI+T*{v:.2f}"
    # low-res per-line displacement + per-channel offset (chroma bleed), restored
    geq = (f"format=gbrp,geq="
           f"r='r(mod(X+{amp:.1f}*sin({ph}),W),Y)':"
           f"g='g(mod(X+{amp * 0.6:.1f}*sin({ph}+0.6),W),Y)':"
           f"b='b(mod(X+{amp * 1.3:.1f}*sin({ph}+1.2),W),Y)'")
    return _one(i, o,
                f"scale=640:-2,{geq},scale={w}:{h},"
                f"noise=alls={int(6 + 20 * t)}:allf=t,"
                f"drawgrid=w=0:h=3:t=1:color=black@{0.10 + 0.18 * t:.2f},"
                f"eq=saturation={1 - 0.25 * t:.2f}:contrast={1 + 0.12 * t:.2f},format=yuv420p")


def _gradient(eff, i, o, u, ctx):
    w, h = ctx["w"], ctx["h"]
    c0, c1 = _c(eff.get("c0", "#00e5ff")), _c(eff.get("c1", "#9945ff"))
    op = _num(eff, "opacity", 40, 0, 100) / 100.0
    mode = _blend_mode(eff.get("blend", "screen"))
    a = math.radians(_num(eff, "angle", 45, 0, 360))
    dx, dy = math.cos(a), math.sin(a)
    x0 = _pt(w / 2 - dx * w / 2, w); y0 = _pt(h / 2 - dy * h / 2, h)
    x1 = _pt(w / 2 + dx * w / 2, w); y1 = _pt(h / 2 + dy * h / 2, h)
    return [f"gradients=s={w}x{h}:r={_fps(ctx)}:c0={c0}:c1={c1}:x0={x0}:y0={y0}:x1={x1}:y1={y1}:nb_colors=2,{_RGB}[{u}g]",
            f"[{i}]{_RGB}[{u}bs]",
            f"[{u}g][{u}bs]blend=all_mode={mode}:all_opacity={op:.2f}:shortest=1[{o}]"]


def _grain(eff, i, o, u, ctx):
    t = _inten(eff, 40)
    return _one(i, o, f"noise=alls={int(4 + 26 * t)}:allf=t+u")


def _vignette(eff, i, o, u, ctx):
    t = _inten(eff, 60)
    ang = 0.9 - 0.5 * t                       # smaller angle = stronger vignette
    return _one(i, o, f"vignette=angle={ang:.3f}")


def _chroma(eff, i, o, u, ctx):
    t = _inten(eff, 50)
    k = int(2 + 12 * t)
    return _one(i, o, f"rgbashift=rh=-{k}:bh={k}")


def _glitch(eff, i, o, u, ctx):
    t = _inten(eff, 60)
    k = int(4 + 18 * t)
    # time-gated horizontal shift blocks + chroma split + noise
    return _one(i, o,
                f"rgbashift=rh=-{k}:bh={k}:rv={k // 2},"
                f"noise=alls={int(10 + 30 * t)}:allf=t,"
                f"eq=contrast={1 + 0.15 * t:.2f}")


def _bloom(eff, i, o, u, ctx):
    t = _inten(eff, 60)
    return [f"[{i}]split=2[{u}a][{u}b]",
            f"[{u}b]gblur=sigma={8 + 24 * t:.1f},eq=brightness=0.06,{_RGB}[{u}bl]",
            f"[{u}a]{_RGB}[{u}a2]",
            f"[{u}bl][{u}a2]blend=all_mode=screen:all_opacity={0.3 + 0.5 * t:.2f}[{o}]"]


def _halation(eff, i, o, u, ctx):
    t = _inten(eff, 60)
    return [f"[{i}]split=2[{u}a][{u}b]",
            f"[{u}b]curves=preset=lighter,gblur=sigma={10 + 26 * t:.1f},"
            f"colorbalance=rs=0.25:rm=0.15,{_RGB}[{u}bl]",
            f"[{u}a]{_RGB}[{u}a2]",
            f"[{u}bl][{u}a2]blend=all_mode=screen:all_opacity={0.25 + 0.45 * t:.2f}[{o}]"]


def _scanlines(eff, i, o, u, ctx):
    t = _inten(eff, 60)
    return _one(i, o,
                f"drawgrid=w=0:h=3:t=1:color=black@{0.12 + 0.22 * t:.2f},"
                f"rgbashift=rh=-1:bh=1,vignette=angle=0.7")


def _letterbox(eff, i, o, u, ctx):
    w, h = ctx["w"], ctx["h"]
    ratio = float(eff.get("ratio", 2.35))
    bar = max(0, int((h - (w / ratio)) / 2))
    return _one(i, o,
                f"drawbox=x=0:y=0:w={w}:h={bar}:color=black@1:t=fill,"
                f"drawbox=x=0:y={h - bar}:w={w}:h={bar}:color=black@1:t=fill")


def _oldfilm(eff, i, o, u, ctx):
    t = _inten(eff, 60)
    return _one(i, o,
                f"curves=preset=vintage,noise=alls={int(8 + 22 * t)}:allf=t,"
                f"vignette=angle=0.6,eq=saturation={1 - 0.3 * t:.2f}")


def _sharpen(eff, i, o, u, ctx):
    t = _inten(eff, 60)
    return _one(i, o, f"unsharp=5:5:{0.5 + 2.0 * t:.2f}:5:5:0.0")


def _blur(eff, i, o, u, ctx):
    t = _inten(eff, 50)
    return _one(i, o, f"gblur=sigma={1 + 14 * t:.1f}")


def _dreamy(eff, i, o, u, ctx):
    t = _inten(eff, 60)
    return [f"[{i}]split=2[{u}a][{u}b]",
            f"[{u}b]gblur=sigma={6 + 18 * t:.1f},{_RGB}[{u}bl]",
            f"[{u}a]{_RGB}[{u}a2]",
            f"[{u}bl][{u}a2]blend=all_mode=screen:all_opacity={0.3 + 0.4 * t:.2f}[{o}]"]


def _pixelate(eff, i, o, u, ctx):
    t = _inten(eff, 50)
    d = max(2, int(4 + 40 * t))
    # On remonte aux dimensions EXACTES, pas à iw*d : la division entière ne
    # retombe pas juste (568/32*32 = 544). Tant que l'effet occupait tout le
    # clip la dérive passait inaperçue ; dès qu'on le mélange avec l'original
    # les deux entrées n'ont plus la même taille et le rendu se bloque.
    w = int((ctx or {}).get("w") or 0)
    h = int((ctx or {}).get("h") or 0)
    back = f"scale={w}:{h}:flags=neighbor" if w and h else f"scale=iw*{d}:ih*{d}:flags=neighbor"
    return _one(i, o, f"scale=iw/{d}:ih/{d}:flags=neighbor,{back}")


def _shake(eff, i, o, u, ctx):
    t = _inten(eff, 50)
    m = int(6 + 26 * t)
    sp = float(eff.get("speed", 50)) / 100.0
    f = 2 + 5 * sp
    return _one(i, o,
                f"pad=iw+{2 * m}:ih+{2 * m}:{m}:{m}:color=black,"
                f"crop=iw-{2 * m}:ih-{2 * m}:"
                f"'{m}+{m}*sin(2*PI*t*{f:.2f})':'{m}+{m}*cos(2*PI*t*{f * 0.8:.2f})'")


def _mirror(eff, i, o, u, ctx):
    """Moitié gauche + son reflet.

    Deux pièges, tous deux mesurés au rendu (scripts/qa/qa_effects_render.py) :
    la largeur de crop doit être PAIRE (en yuv420p la chroma est sous-
    échantillonnée, ffmpeg rabote une largeur impaire d'un pixel), et
    2 × (w // 2) ne retombe pas forcément sur w (270 -> 134 + 134 = 268).
    On remet donc la taille EXACTE : sinon blend refuse deux entrées de
    tailles différentes et c'est TOUT le rendu qui échoue, pas seulement
    l'effet (« First input link top parameters (size 268x480) do not match »).
    """
    w = int((ctx or {}).get("w") or 0)
    h = int((ctx or {}).get("h") or 0)
    back = f",scale={w}:{h}" if w > 1 and h > 1 else ""
    return [f"[{i}]crop='floor(iw/4)*2':ih:0:0[{u}l]",
            f"[{u}l]split=2[{u}l1][{u}l2]",
            f"[{u}l2]hflip[{u}r]",
            f"[{u}l1][{u}r]hstack=inputs=2{back}[{o}]"]


def _invert(eff, i, o, u, ctx):
    return _one(i, o, "negate")


# =============================================================================
# Élargissement du catalogue (rack VFX) — chacun de ces effets a été rendu
# pour de vrai avant d'entrer ici : une chaîne qui plante au rendu coûte plus
# cher à l'utilisateur qu'un effet absent.
# =============================================================================

def _prism(eff, i, o, u, ctx):
    """Prisme : aberration chromatique RADIALE (rouge vers l'extérieur, bleu
    vers l'intérieur). `chroma` décale en ligne droite ; ici l'écart croît
    avec la distance au centre, comme une vraie optique."""
    t = _inten(eff, 55)
    k = 2 + 22 * t
    return _one(i, o,
                f"{_RGB},geq="
                f"r='r(X+{k:.2f}*(X-W/2)/(W/2),Y+{k:.2f}*(Y-H/2)/(H/2))':"
                f"g='g(X,Y)':"
                f"b='b(X-{k:.2f}*(X-W/2)/(W/2),Y-{k:.2f}*(Y-H/2)/(H/2))'")


def _ripple(eff, i, o, u, ctx):
    """Ondulation : déplacement sinusoïdal croisé, animé dans le temps."""
    t = _inten(eff, 55)
    sp = _num(eff, "speed", 50, 0, 100) / 100.0
    a = 3 + 22 * t                                # amplitude en px
    f = 2 * math.pi * (2 + 8 * t)                 # fréquence spatiale
    s = 1.0 + 7.0 * sp                            # vitesse temporelle
    d = (f"X+{a:.1f}*sin({f:.3f}*Y/H+T*{s:.2f}),"
         f"Y+{a:.1f}*sin({f:.3f}*X/W+T*{s:.2f})")
    return _one(i, o, f"{_RGB},geq=r='r({d})':g='g({d})':b='b({d})'")


def _swirl(eff, i, o, u, ctx):
    """Tourbillon : rotation dont l'angle décroît du centre vers le bord."""
    t = _inten(eff, 55)
    k = 0.4 + 3.0 * t
    dist = "hypot(X-W/2,Y-H/2)/(W/2)"
    ang = f"({k:.3f}*max(0,1-{dist}))"
    d = (f"W/2+(X-W/2)*cos({ang})-(Y-H/2)*sin({ang}),"
         f"H/2+(X-W/2)*sin({ang})+(Y-H/2)*cos({ang})")
    return _one(i, o, f"{_RGB},geq=r='r({d})':g='g({d})':b='b({d})'")


def _lensdistort(eff, i, o, u, ctx):
    """Distorsion d'objectif : barillet (fisheye) ou coussinet.

    En barillet, `lenscorrection` rentre l'image et laisse un cadre noir : on
    re-agrandit puis on recadre pour que le cadre reste plein (le coussinet,
    lui, déborde déjà — aucun agrandissement n'est nécessaire).
    """
    t = _inten(eff, 55)
    w, h = _even(ctx["w"]), _even(ctx["h"])
    k1 = 0.05 + 0.35 * t
    if str(eff.get("preset", "barillet")) == "coussinet":
        k1 = -k1
        fill = ""
    else:
        z = 1.0 + 1.25 * k1
        fill = f",scale={_even(w * z)}:{_even(h * z)},crop={w}:{h}"
    return _one(i, o,
                f"lenscorrection=k1={k1:.3f}:k2={k1 * 0.25:.3f}:i=bilinear{fill}")


def _zoomblur(eff, i, o, u, ctx):
    """Zoom flou radial : moyenne de 9 copies progressivement zoomées.

    Les poids somment à 1 — l'opération reste une combinaison linéaire, donc
    juste même sur un flux yuv (pas de dérive de chrominance, contrairement à
    `screen`). Un dernier flou léger lisse l'escalier entre les copies : à 5
    copies on distinguait des fantômes au lieu d'une traînée.
    """
    t = _inten(eff, 55)
    w, h = _even(ctx["w"]), _even(ctx["h"])
    zmax = 0.03 + 0.20 * t
    n = 9
    zs = [1.0 + zmax * k / (n - 1) for k in range(n)]
    st = [f"[{i}]split={n}" + "".join(f"[{u}z{k}]" for k in range(n)),
          f"[{u}z0]null[{u}c0]"]
    for k in range(1, n):
        st.append(f"[{u}z{k}]scale={_even(w * zs[k])}:{_even(h * zs[k])},"
                  f"crop={w}:{h}[{u}c{k}]")
    prev = f"{u}c0"
    for k in range(1, n):
        dst = f"{u}m{k}"
        wa, wb = k / (k + 1.0), 1.0 / (k + 1.0)
        st.append(f"[{prev}][{u}c{k}]blend=all_expr='A*{wa:.4f}+B*{wb:.4f}'[{dst}]")
        prev = dst
    st.append(f"[{prev}]gblur=sigma={0.6 + 1.6 * t:.2f}[{o}]")
    return st


def _dirblur(eff, i, o, u, ctx):
    """Flou directionnel : moyenne de 9 copies translatées le long de l'angle.

    Pas de rotation intermédiaire (elle mangerait les coins : à 30° il faudrait
    agrandir de 80 % pour que le cadre reste couvert). Les bords sont étirés
    par `fillborders` avant translation, donc aucune bande noire n'entre. Un
    flou final lisse l'escalier entre copies.
    """
    t = _inten(eff, 55)
    w, h = _even(ctx["w"]), _even(ctx["h"])
    a = math.radians(_num(eff, "angle", 0, 0, 360))
    m = _even(4 + 46 * t)
    n = 9
    st = [f"[{i}]pad={w + 2 * m}:{h + 2 * m}:{m}:{m},"
          f"fillborders=left={m}:right={m}:top={m}:bottom={m}:mode=smear,"
          f"split={n}" + "".join(f"[{u}d{k}]" for k in range(n))]
    for k in range(n):
        f = (k / (n - 1.0)) * 2 - 1                      # -1 .. +1
        dx = int(round(m * f * math.cos(a)))
        dy = int(round(-m * f * math.sin(a)))
        st.append(f"[{u}d{k}]crop={w}:{h}:{m + dx}:{m + dy}[{u}p{k}]")
    prev = f"{u}p0"
    for k in range(1, n):
        dst = f"{u}q{k}"
        wa, wb = k / (k + 1.0), 1.0 / (k + 1.0)
        st.append(f"[{prev}][{u}p{k}]blend=all_expr='A*{wa:.4f}+B*{wb:.4f}'[{dst}]")
        prev = dst
    st.append(f"[{prev}]gblur=sigma={0.8 + 2.4 * t:.2f}[{o}]")
    return st


def _shakezoom(eff, i, o, u, ctx):
    """Tremblement d'objectif AVEC zoom : recadrage serré (le zoom qui laisse
    la marge), translation et roulis sinusoïdaux — la secousse « caméra à
    l'épaule » plutôt que le simple décalage de `shake`."""
    t = _inten(eff, 60)
    sp = _num(eff, "speed", 50, 0, 100) / 100.0
    w, h = _even(ctx["w"]), _even(ctx["h"])
    z = 1.06 + 0.18 * t
    m = 6 + 34 * t
    f = 3.0 + 7.0 * sp
    return _one(i, o,
                f"scale={_even(w * z)}:{_even(h * z)},"
                f"crop={w}:{h}:'(iw-ow)/2+{m:.1f}*sin(2*PI*t*{f:.2f})'"
                f":'(ih-oh)/2+{m:.1f}*cos(2*PI*t*{f * 0.79:.2f})',"
                f"rotate='{0.004 + 0.018 * t:.4f}*sin(2*PI*t*{f * 0.57:.2f})'"
                f":ow=iw:oh=ih:c=none")


def _kaleido(eff, i, o, u, ctx):
    """Kaléidoscope : symétrie 4 voies (`mirror` n'en fait que 2)."""
    w, h = _even(ctx["w"]), _even(ctx["h"])
    return [f"[{i}]scale={_even(w / 2)}:{_even(h / 2)}[{u}k]",
            f"[{u}k]split=2[{u}k1][{u}k2]",
            f"[{u}k2]hflip[{u}kf]",
            f"[{u}k1][{u}kf]hstack=inputs=2[{u}top]",
            f"[{u}top]split=2[{u}t1][{u}t2]",
            f"[{u}t2]vflip[{u}bt]",
            f"[{u}t1][{u}bt]vstack=inputs=2,scale={w}:{h}[{o}]"]


def _lightleak(eff, i, o, u, ctx):
    """Fuite de lumière : nappe colorée entrant par un bord, en `screen`.
    L'angle place le point chaud sur le pourtour."""
    t = _inten(eff, 60)
    w, h = ctx["w"], ctx["h"]
    c0 = _c(eff.get("c0", "#ff9a3c"))
    a = math.radians(_num(eff, "angle", 30, 0, 360))
    x0 = _pt(w / 2 + math.cos(a) * w * 0.62, w)
    y0 = _pt(h / 2 - math.sin(a) * h * 0.62, h)
    x1 = _pt(w / 2 - math.cos(a) * w * 0.30, w)
    y1 = _pt(h / 2 + math.sin(a) * h * 0.30, h)
    return [f"gradients=s={w}x{h}:r={_fps(ctx)}:c0={c0}:c1=0x000000:x0={x0}:y0={y0}:"
            f"x1={x1}:y1={y1}:nb_colors=2:speed=0.05,"
            f"gblur=sigma={20 + 40 * t:.0f},{_RGB}[{u}lk]",
            f"[{i}]{_RGB}[{u}bs]",
            f"[{u}lk][{u}bs]blend=all_mode=screen:"
            f"all_opacity={0.20 + 0.65 * t:.2f}:shortest=1[{o}]"]


def _radial(eff, i, o, u, ctx):
    """Dégradé radial : halo coloré centré, mode de fusion au choix."""
    w, h = ctx["w"], ctx["h"]
    c0, c1 = _c(eff.get("c0", "#ffb45a")), _c(eff.get("c1", "#000000"))
    op = _num(eff, "opacity", 55, 0, 100) / 100.0
    mode = _blend_mode(eff.get("blend", "screen"))
    cx = _pt(w * _num(eff, "cx", 50, 0, 100) / 100.0, w)
    cy = _pt(h * _num(eff, "cy", 40, 0, 100) / 100.0, h)
    return [f"gradients=s={w}x{h}:r={_fps(ctx)}:c0={c0}:c1={c1}:type=radial:"
            f"x0={cx}:y0={cy}:x1={w - 1}:y1={h - 1}:nb_colors=2,{_RGB}[{u}rg]",
            f"[{i}]{_RGB}[{u}bs]",
            f"[{u}rg][{u}bs]blend=all_mode={mode}:all_opacity={op:.2f}:shortest=1[{o}]"]


def _filmburn(eff, i, o, u, ctx):
    """Film brûlé : point chaud qui mange l'image + base vintage granuleuse."""
    t = _inten(eff, 65)
    w, h = ctx["w"], ctx["h"]
    return [f"gradients=s={w}x{h}:r={_fps(ctx)}:c0=0xfff0b0:c1=0x000000:type=radial:"
            f"x0={_pt(w * 0.32, w)}:y0={_pt(h * 0.62, h)}:"
            f"x1={_pt(w * (0.9 - 0.45 * t), w)}:y1={h - 1}:nb_colors=2:speed=0.08,"
            f"gblur=sigma=18,eq=contrast=1.5,{_RGB}[{u}fb]",
            f"[{i}]curves=preset=vintage,noise=alls={int(6 + 22 * t)}:allf=t,"
            f"vignette=angle={0.75 - 0.25 * t:.2f},{_RGB}[{u}bs]",
            f"[{u}fb][{u}bs]blend=all_mode=screen:"
            f"all_opacity={0.35 + 0.6 * t:.2f}:shortest=1[{o}]"]


def _particles(eff, i, o, u, ctx, *, kind):
    """Base commune pluie / neige / braises.

    Aucun asset n'est livré : le champ de particules est un bruit ffmpeg FIXE
    (`allf=u`, donc identique d'une image à l'autre) découpé sur deux hauteurs
    d'image et défilé par l'expression `y` de `crop` — c'est le défilement qui
    fait le mouvement. Un bruit temporel (`allf=t`) grésillerait sur place.
    """
    t = _inten(eff, 60)
    sp = _num(eff, "speed", 50, 0, 100) / 100.0
    w, h = _even(ctx["w"]), _even(ctx["h"])
    fps = _fps(ctx)
    if kind == "rain":
        fw = _even(max(160, w / 2))
        small = _even(max(24, h / 5))             # étiré x10 => traînées
        thr = int(184 - 10 * t)
        vit = 500 + 900 * sp
        src = (f"color=c=gray:s={fw}x{small}:r={fps},noise=alls=100:allf=u,"
               f"format=gray,lutyuv=y='if(gt(val,{thr}),255,0)',"
               f"scale={fw}:{2 * h}:flags=neighbor")
        yexp = f"'mod(t*{vit:.0f},{h})'"
        post = f"scale={w}:{h},gblur=sigma=0.6,eq=contrast=1.6,{_RGB}"
        op = 0.25 + 0.5 * t
    elif kind == "snow":
        # Champ étroit puis ré-agrandi : c'est l'agrandissement qui donne aux
        # flocons une taille visible (un pixel de bruit resterait un point).
        fw = _even(max(96, w / 8))
        thr = int(182 - 8 * t)
        vit = 40 + 160 * sp
        src = (f"color=c=gray:s={fw}x{_even(h / 4)}:r={fps},noise=alls=100:allf=u,"
               f"format=gray,lutyuv=y='if(gt(val,{thr}),255,0)',"
               f"scale={fw}:{2 * h}:flags=neighbor")
        yexp = f"'mod(t*{vit:.0f},{h})'"
        post = f"scale={w}:{h},gblur=sigma=3.5,eq=contrast=2.4,{_RGB}"
        op = 0.45 + 0.5 * t
    else:                                          # braises, qui MONTENT
        fw = _even(max(160, w / 5))
        thr = int(189 - 8 * t)
        vit = 50 + 160 * sp
        src = (f"color=c=gray:s={fw}x{2 * h}:r={fps},noise=alls=100:allf=u,"
               f"format=gray,lutyuv=y='if(gt(val,{thr}),255,0)'")
        yexp = f"'{h}-mod(t*{vit:.0f},{h})'"
        post = (f"scale={w}:{h},gblur=sigma=2.5,{_RGB},"
                f"lutrgb=r='val':g='clip(val*0.42,0,255)':b='clip(val*0.10,0,255)',"
                f"{_RGB}")
        op = 0.4 + 0.55 * t
    return [f"{src}[{u}pf]",
            f"[{u}pf]crop={fw}:{h}:0:{yexp},{post}[{u}pl]",
            f"[{i}]{_RGB}[{u}bs]",
            f"[{u}pl][{u}bs]blend=all_mode=screen:"
            f"all_opacity={op:.2f}:shortest=1[{o}]"]


def _rain(eff, i, o, u, ctx):
    return _particles(eff, i, o, u, ctx, kind="rain")


def _snow(eff, i, o, u, ctx):
    return _particles(eff, i, o, u, ctx, kind="snow")


def _embers(eff, i, o, u, ctx):
    return _particles(eff, i, o, u, ctx, kind="embers")


def _posterize(eff, i, o, u, ctx):
    """Postérisation : quantification du nombre de niveaux par composante."""
    t = _inten(eff, 60)
    lv = max(2, int(round(12 - 9 * t)))            # 12 niveaux -> 3
    q = 255.0 / (lv - 1)
    e = f"floor(val*{lv}/256)*{q:.4f}"
    return _one(i, o, f"lutrgb=r='{e}':g='{e}':b='{e}'")


def _dither(eff, i, o, u, ctx):
    """Tramage ordonné (Bayer 4x4) : la quantification est décalée par une
    matrice de seuils, ce qui remplace le banding par une trame — le rendu
    « impression / pixel art » que la postérisation seule ne donne pas."""
    t = _inten(eff, 60)
    lv = max(2, int(round(8 - 5 * t)))
    bay = "st(0,(mod(X,4)*4+mod(Y,4))/16-0.5)"
    def q(ch):
        return (f"{bay}\\;clip(floor({ch}(X,Y)/255*{lv - 1}+ld(0)+0.5)"
                f"/{lv - 1}*255,0,255)")
    return _one(i, o, f"{_RGB},geq=r='{q('r')}':g='{q('g')}':b='{q('b')}'")


def _glowedge(eff, i, o, u, ctx):
    """Bord lumineux : contours en néon rajoutés en `screen`.

    `sobel` plutôt qu'`edgedetect` : il rend la MAGNITUDE des contours sur
    fond noir, et par composante — un `screen` dessus n'allume que les
    contours, en gardant leur couleur. `edgedetect=colormix` renvoie l'image
    entière retouchée : fusionnée, elle éclaircit tout au lieu de souligner.
    """
    t = _inten(eff, 60)
    return [f"[{i}]split=2[{u}a][{u}b]",
            f"[{u}b]{_RGB},sobel=scale={0.6 + 1.6 * t:.2f},"
            f"gblur=sigma={0.8 + 2.5 * t:.1f},{_RGB}[{u}e]",
            f"[{u}a]{_RGB}[{u}a2]",
            f"[{u}e][{u}a2]blend=all_mode=screen:"
            f"all_opacity={0.4 + 0.55 * t:.2f}[{o}]"]


def _paper(eff, i, o, u, ctx):
    """Texture papier : grain fixe en lumière douce + teinte crème + vignette.
    Le bruit est spatial (`allf=u`), pas temporel : la texture ne grésille pas
    d'une image à l'autre, comme une vraie feuille."""
    t = _inten(eff, 60)
    w, h = ctx["w"], ctx["h"]
    fps = _fps(ctx)
    return [f"color=c=gray:s={w}x{h}:r={fps},noise=alls={int(10 + 40 * t)}:allf=u,"
            f"gblur=sigma=0.8,{_RGB}[{u}pp]",
            f"[{i}]eq=saturation={1 - 0.4 * t:.2f}:contrast={1 - 0.1 * t:.2f},"
            f"colorbalance=rs={0.08 * t:.3f}:gs={0.04 * t:.3f}:bs={-0.07 * t:.3f},"
            f"{_RGB}[{u}bs]",
            f"[{u}pp][{u}bs]blend=all_mode=softlight:"
            f"all_opacity={0.4 + 0.55 * t:.2f}:shortest=1[{u}mx]",
            f"[{u}mx]vignette=angle={0.9 - 0.25 * t:.2f}[{o}]"]


EFFECTS = {
    "grade": _grade, "lut": _grade, "colorize": _colorize, "vhs": _vhs,
    "gradient": _gradient, "grain": _grain, "vignette": _vignette,
    "chroma": _chroma, "glitch": _glitch, "bloom": _bloom, "halation": _halation,
    "scanlines": _scanlines, "letterbox": _letterbox, "oldfilm": _oldfilm,
    "sharpen": _sharpen, "blur": _blur, "dreamy": _dreamy, "pixelate": _pixelate,
    "shake": _shake, "mirror": _mirror, "invert": _invert,
    # --- rack VFX ---
    "prism": _prism, "ripple": _ripple, "swirl": _swirl,
    "lensdistort": _lensdistort, "zoomblur": _zoomblur, "dirblur": _dirblur,
    "shakezoom": _shakezoom, "kaleido": _kaleido, "lightleak": _lightleak,
    "radial": _radial, "filmburn": _filmburn, "rain": _rain, "snow": _snow,
    "embers": _embers, "posterize": _posterize, "dither": _dither,
    "glowedge": _glowedge, "paper": _paper,
}


# ---- enveloppe temporelle (t0/t1 + courbes de Bézier) -----------------------
#
# ffmpeg ne rampe pas uniformément : sur les 20 effets, seuls vignette,
# letterbox, shake et gradient acceptent une expression dépendant de `t` pour
# leur paramètre ; d'autres n'y arrivent que par commandes différées, et
# pixelate/mirror/vhs refusent même `enable=` (leur chaîne contient scale,
# crop, pad ou hstack). Implémenter au cas par cas donnerait un comportement
# différent selon l'effet choisi, découvert au rendu.
#
# On enveloppe donc TOUS les effets dans un fondu dry/wet, vérifié sur les 20 :
#     [in]split=2[a][b]; [b]<effet>[p]; [a][p]blend=all_opacity=<rampe>[out]
# L'opacité suit la courbe demandée, l'effet est absent hors de [t0,t1].
#
# La courbe elle-même ne peut pas être résolue dans ffmpeg (Bézier = calcul
# itératif). On l'échantillonne côté Python : la rampe devient une expression
# en escalier, imperceptible au pas retenu, et surtout EXACTEMENT la courbe
# dessinée par l'utilisateur — pas une approximation qui divergerait en
# silence.

#: Pas d'échantillonnage des rampes, en secondes.
_RAMP_STEP = 1.0 / 25.0

#: Effets dont l'identité EST le paramètre : un fondu dry/wet les dédouble au
#: lieu de les atténuer. Ils sont gated (enable=) mais pas fondus.
_NO_CROSSFADE = ("shake", "shakezoom")


def _ease_at(spec, u):
    """Valeur 0..1 de la courbe en u. Réutilise `ease()` d'animation_service,
    qui gère à la fois les presets nommés et la forme cubic-bezier(a,b,c,d)."""
    from app.services.animation_service import ease
    return ease(spec or "smooth", max(0.0, min(1.0, u)))


def _opacity_cmds(target, t0, t1, fade_in, fade_out, ease_in, ease_out):
    """Commandes sendcmd pilotant l'opacité du blend `target`.

    all_opacity n'accepte PAS d'expression (option flottante) ; il est en
    revanche commandable à l'exécution. On échantillonne donc la courbe côté
    Python et on émet une commande par pas — évaluée une fois par image, là
    où une expression `all_expr` coûterait un calcul par pixel.

    PIÈGE ffmpeg (mesuré, pas déduit — voir scripts/qa/qa_effects_render.py) :
    `blend` ne recopie all_opacity dans l'opacité de chaque plan QUE si la
    valeur est strictement inférieure à 1 (vf_blend.c, config_params :
    « if (s->all_opacity < 1) param->opacity = s->all_opacity; »). Une
    commande « all_opacity 1 » est donc acceptée (ret 0) mais SANS effet :
    l'opacité reste celle d'avant. Sans rampe (fade_in = fade_out = 0), la
    seule valeur « pleine » envoyée est justement 1 — l'effet ne s'allumait
    jamais, sur AUCUN des 21 effets et sur AUCUN des chemins de rendu.
    À 100 % on remet donc all_opacity à 1 (ce qui rouvre la garde) puis on
    pose explicitement l'opacité des 4 plans. Correct aussi le jour où ffmpeg
    corrigera la garde : les deux écritures disent la même chose.
    """
    cmds = []

    def at(t, v):
        t = max(0.0, t)
        v = max(0.0, min(1.0, v))
        if v >= 1.0:
            cmds.append(f"{t:.3f} {target} all_opacity 1")
            for p in range(4):
                cmds.append(f"{t:.3f} {target} c{p}_opacity 1")
            return
        cmds.append(f"{t:.3f} {target} all_opacity {v:.4f}")

    at(0.0, 0.0)                                   # effet absent avant t0
    if fade_in > 0:
        n = max(1, int(round(fade_in / _RAMP_STEP)))
        for i in range(n + 1):
            at(t0 + i * fade_in / n, _ease_at(ease_in, i / n))
    else:
        at(t0, 1.0)
    if fade_out > 0:
        n = max(1, int(round(fade_out / _RAMP_STEP)))
        for i in range(n + 1):
            at(t1 - fade_out + i * fade_out / n, 1.0 - _ease_at(ease_out, i / n))
    else:
        at(t1, 0.0)
    at(t1 + 0.001, 0.0)                            # effet absent après t1
    # sendcmd sépare ses intervalles par « ; », qui est aussi le séparateur de
    # chaînes du filtergraph : il doit être échappé.
    return "\\;".join(cmds)


def _timed(eff, stmts, in_lbl, out_lbl, uid, ctx):
    """Enveloppe une chaîne d'effet dans son intervalle et sa rampe.

    Mécanisme unique pour les 20 effets : on duplique le flux, on applique
    l'effet sur une copie, et on mélange les deux avec une opacité pilotée
    dans le temps. `enable=` n'est PAS utilisé — pixelate, mirror, vhs et
    shake le refusent (leur chaîne contient scale, crop, pad ou hstack).
    """
    try:
        t0 = float(eff.get("t0"))
        t1 = float(eff.get("t1"))
    except (TypeError, ValueError):
        return stmts                      # pas de bornes -> effet plein clip
    dur = float((ctx or {}).get("dur") or 0) or None
    t0 = max(0.0, t0)
    t1 = min(t1, dur) if dur else t1
    if t1 - t0 < 0.05:
        return stmts
    span = t1 - t0
    fi = max(0.0, min(float(eff.get("fade_in", 0) or 0), span / 2))
    fo = max(0.0, min(float(eff.get("fade_out", 0) or 0), span / 2))
    if eff.get("type") in _NO_CROSSFADE:
        # Mélanger une image secouée avec une image fixe la dédouble au lieu
        # de l'atténuer : pour ceux-là, entrée et sortie franches.
        fi = fo = 0.0

    # Libellés de l'enveloppe : préfixe DÉDIÉ. build_chain passe le même uid à
    # l'effet et à l'enveloppe, et bloom/halation/dreamy nomment déjà leurs
    # propres branches « <uid>a » et « <uid>b » — exactement les libellés du
    # split dry/wet. Le graphe restait complet (les quatre libellés portaient
    # le même flux, donc rien de visible), mais l'appariement était laissé au
    # parseur : la branche « originale » pouvait être tirée du split INTERNE
    # de l'effet, donc dans son format à lui. Mesuré : ~2/255 d'écart hors
    # intervalle sur ces trois effets, là où les autres tombaient à 0.000.
    env = f"{uid}env"
    tag = f"blend@{env}"
    inner = f"{env}w"
    body = []
    for st in stmts:
        body.append(st.replace(f"[{in_lbl}]", f"[{env}b]", 1)
                      .replace(f"[{out_lbl}]", f"[{inner}]"))
    cmds = _opacity_cmds(tag, t0, t1, fi, fo, eff.get("ease_in"), eff.get("ease_out"))
    # Dans blend, la PREMIÈRE entrée est le calque du dessus et all_opacity
    # est SON opacité : c'est donc l'effet qui doit venir en premier pour que
    # l'opacité 0 laisse voir l'original.
    # La branche « effet » est ramenée en yuv420p AVANT le mélange. Sans cela,
    # un effet qui travaille en RGB (gradient, bloom, chroma…) force blend à
    # négocier un format RGB, et c'est la branche ORIGINALE qui subit un
    # aller-retour yuv->rgb->yuv : mesuré à ~2/255 d'écart moyen sur toute la
    # durée du clip, y compris hors de [t0,t1] où l'effet est censé être
    # absent. Avec ce format=, hors intervalle l'image est identique au bit
    # près à un rendu sans effet (vérifié : écart 0.000).
    # Le `format=` AVANT le split est indispensable : `split` recopie les
    # images, ses deux sorties partagent donc le MÊME format. Sans lui, un
    # effet qui travaille en RGB (bloom, halation, dreamy… dont la chaîne
    # contient un blend interne) tire le split entier en gbrp et la branche
    # originale repart en yuv420p à la sortie — un aller-retour subi par
    # l'image d'origine, y compris quand l'effet est éteint. Les trois
    # chemins de rendu fournissent déjà du yuv420p ici (segments Montage,
    # régions et post-pass du Studio), donc rien n'est perdu.
    return ([f"[{in_lbl}]format=yuv420p,split=2[{env}a][{env}b]"] + body +
            [f"[{inner}]format=yuv420p[{inner}f]",
             f"[{env}a]sendcmd=c='{cmds}'[{env}a2]",
             f"[{inner}f][{env}a2]{tag}=all_mode=normal:all_opacity=0[{out_lbl}]"])


def build_chain(effects, in_lbl, out_lbl, uid, ctx):
    """Thread `effects` into a filtergraph from in_lbl to out_lbl.
    Returns a list of filtergraph statements. Empty -> a passthrough copy.

    Un effet portant `t0`/`t1` (secondes, locales au clip) n'agit que sur cet
    intervalle ; `fade_in`/`fade_out` et `ease_in`/`ease_out` y ajoutent une
    rampe suivant une courbe de Bézier.
    """
    effects = [e for e in (effects or []) if isinstance(e, dict) and e.get("type") in EFFECTS]
    if not effects:
        return [f"[{in_lbl}]null[{out_lbl}]"]
    stmts, cur = [], in_lbl
    last = len(effects) - 1
    for idx, eff in enumerate(effects):
        nxt = out_lbl if idx == last else f"{uid}s{idx}"
        uid_e = f"{uid}e{idx}"
        try:
            one = EFFECTS[eff["type"]](eff, cur, nxt, uid_e, ctx)
            stmts += _timed(eff, one, cur, nxt, uid_e, ctx)
        except Exception:
            stmts.append(f"[{cur}]null[{nxt}]")
        cur = nxt
    return stmts


# =============================================================================
# Catalogue : catégories, libellés FR, paramètres et leurs BORNES.
#
# Les bornes ne sont pas décoratives : elles servent au panneau (curseurs,
# nuanciers, listes) ET au serveur, qui refuse ou ramène dans l'intervalle
# toute valeur reçue avant de la mettre dans une ligne de commande ffmpeg.
# =============================================================================

#: Catégories, dans l'ordre d'affichage du rack.
CATEGORIES = (
    ("etalonnage", "Étalonnage"),
    ("retro", "Rétro"),
    ("lumiere", "Lumière"),
    ("atmosphere", "Atmosphère"),
    ("distorsion", "Distorsion"),
    ("mouvement", "Mouvement"),
    ("cadrage", "Cadrage"),
    ("stylisation", "Stylisation"),
)

#: Gabarit par paramètre. `type` pilote le contrôle affiché :
#: range = curseur, color = nuancier, choice = liste, lut = fichier .cube.
_PARAM_DEFAULTS = {
    "intensity": {"type": "range", "min": 0, "max": 100, "step": 1,
                  "default": 60, "label": "Intensité"},
    "speed":     {"type": "range", "min": 0, "max": 100, "step": 1,
                  "default": 50, "label": "Vitesse"},
    "angle":     {"type": "range", "min": 0, "max": 360, "step": 1,
                  "default": 45, "label": "Angle", "unit": "°"},
    "opacity":   {"type": "range", "min": 0, "max": 100, "step": 1,
                  "default": 40, "label": "Opacité"},
    "cx":        {"type": "range", "min": 0, "max": 100, "step": 1,
                  "default": 50, "label": "Centre X"},
    "cy":        {"type": "range", "min": 0, "max": 100, "step": 1,
                  "default": 40, "label": "Centre Y"},
    "c0":        {"type": "color", "default": "#00e5ff", "label": "Couleur 1"},
    "c1":        {"type": "color", "default": "#9945ff", "label": "Couleur 2"},
    "blend":     {"type": "choice", "choices": list(BLEND_MODES),
                  "default": "screen", "label": "Fusion"},
    "ratio":     {"type": "choice", "choices": ["2.39", "2.35", "1.85", "1.33"],
                  "default": "2.35", "label": "Format"},
    "preset":    {"type": "choice", "choices": [], "default": "",
                  "label": "Préréglage"},
    "file":      {"type": "lut", "default": "", "label": "LUT .cube"},
}

#: (catégorie, libellé, paramètres, aide) + surcharges de bornes éventuelles.
_CATALOG = {
    # --- Étalonnage ---
    "grade":      ("etalonnage", "LUT / Étalonnage", ["preset", "file"],
                   "Ambiances colorimétriques, ou votre propre LUT .cube.", {}),
    "colorize":   ("etalonnage", "Colorisation", ["preset", "intensity"],
                   "Sépia, noir et blanc, duotone, matrice.", {}),
    "invert":     ("etalonnage", "Négatif", [], "Inverse toutes les couleurs.", {}),
    "posterize":  ("etalonnage", "Postérisation", ["intensity"],
                   "Réduit le nombre de niveaux : aplats façon sérigraphie.", {}),
    # --- Rétro ---
    "vhs":        ("retro", "VHS", ["intensity", "speed"],
                   "Bande usée : lignes tremblées, bavure chroma, bruit.", {}),
    "scanlines":  ("retro", "Scanlines / CRT", ["intensity"],
                   "Lignes de balayage d'un tube cathodique.", {}),
    "oldfilm":    ("retro", "Vieux film", ["intensity"],
                   "Étalonnage fané, poussière, vignette.", {}),
    "grain":      ("retro", "Grain film", ["intensity"],
                   "Grain argentique animé.", {}),
    "filmburn":   ("retro", "Film brûlé", ["intensity"],
                   "Point chaud qui mange la pellicule.",
                   {"intensity": {"default": 65}}),
    "dither":     ("retro", "Tramage", ["intensity"],
                   "Trame ordonnée Bayer : dégradés en points, façon impression.", {}),
    # --- Lumière ---
    "bloom":      ("lumiere", "Bloom / Halo", ["intensity"],
                   "Les hautes lumières débordent.", {}),
    "halation":   ("lumiere", "Halation", ["intensity"],
                   "Halo rouge autour des lumières, comme sur pellicule.", {}),
    "vignette":   ("lumiere", "Vignette", ["intensity"],
                   "Assombrit les bords, concentre le regard.", {}),
    "gradient":   ("lumiere", "Dégradé linéaire",
                   ["c0", "c1", "angle", "opacity", "blend"],
                   "Nappe de deux couleurs sur toute l'image.", {}),
    "radial":     ("lumiere", "Dégradé radial",
                   ["c0", "c1", "cx", "cy", "opacity", "blend"],
                   "Halo coloré placé où vous voulez.",
                   {"c0": {"default": "#ffb45a"}, "c1": {"default": "#000000"},
                    "opacity": {"default": 55}}),
    "lightleak":  ("lumiere", "Fuite de lumière", ["intensity", "angle", "c0"],
                   "Lumière parasite entrant par un bord du cadre.",
                   {"c0": {"default": "#ff9a3c"}, "angle": {"default": 30}}),
    # --- Atmosphère ---
    "rain":       ("atmosphere", "Pluie", ["intensity", "speed"],
                   "Averse procédurale en surimpression.", {}),
    "snow":       ("atmosphere", "Neige", ["intensity", "speed"],
                   "Flocons procéduraux en surimpression.", {}),
    "embers":     ("atmosphere", "Braises", ["intensity", "speed"],
                   "Étincelles orange qui montent.", {}),
    # --- Distorsion ---
    "chroma":     ("distorsion", "Aberration chromatique", ["intensity"],
                   "Décalage rouge/bleu en ligne droite.", {}),
    "glitch":     ("distorsion", "Glitch", ["intensity"],
                   "Ruptures numériques, bruit et décalage de couches.", {}),
    "prism":      ("distorsion", "Prisme", ["intensity"],
                   "Aberration radiale : l'écart grandit vers les bords.",
                   {"intensity": {"default": 55}}),
    "ripple":     ("distorsion", "Ondulation", ["intensity", "speed"],
                   "Vague sinusoïdale animée sur toute l'image.",
                   {"intensity": {"default": 55}}),
    "swirl":      ("distorsion", "Tourbillon", ["intensity"],
                   "Rotation qui s'amortit du centre vers les bords.",
                   {"intensity": {"default": 55}}),
    "lensdistort": ("distorsion", "Distorsion d'objectif", ["intensity", "preset"],
                    "Barillet (fisheye) ou coussinet.",
                    {"intensity": {"default": 55}}),
    # --- Mouvement ---
    "blur":       ("mouvement", "Flou", ["intensity"], "Flou gaussien.", {}),
    "dirblur":    ("mouvement", "Flou directionnel", ["intensity", "angle"],
                   "Filé de mouvement suivant un angle.",
                   {"angle": {"default": 0}, "intensity": {"default": 55}}),
    "zoomblur":   ("mouvement", "Zoom flou radial", ["intensity"],
                   "Traînées partant du centre, effet de propulsion.",
                   {"intensity": {"default": 55}}),
    "shake":      ("mouvement", "Secousse caméra", ["intensity", "speed"],
                   "Tremblement de cadre.", {}),
    "shakezoom":  ("mouvement", "Secousse + zoom", ["intensity", "speed"],
                   "Caméra à l'épaule : recadrage serré, roulis et tremblement.", {}),
    # --- Cadrage ---
    "letterbox":  ("cadrage", "Bandes cinéma", ["ratio"],
                   "Bandes noires au format choisi.", {}),
    "mirror":     ("cadrage", "Miroir", [], "Symétrie gauche/droite.", {}),
    "kaleido":    ("cadrage", "Kaléidoscope", [],
                   "Symétrie 4 voies, motif de kaléidoscope.", {}),
    # --- Stylisation ---
    "pixelate":   ("stylisation", "Pixelisation", ["intensity"],
                   "Gros pixels, façon censure ou jeu rétro.", {}),
    "sharpen":    ("stylisation", "Netteté", ["intensity"],
                   "Renforce les détails.", {}),
    "dreamy":     ("stylisation", "Doux / Rêve", ["intensity"],
                   "Voile diffus sur les hautes lumières.", {}),
    "glowedge":   ("stylisation", "Bord lumineux", ["intensity"],
                   "Les contours s'illuminent, style néon.", {}),
    "paper":      ("stylisation", "Texture papier", ["intensity"],
                   "Grain de feuille, teinte crème, coins assombris.", {}),
}

#: Alias historique : « lut » et « grade » sont le même effet.
_ALIASES = {"lut": "grade"}


def categories():
    """Catégories du rack, dans l'ordre, avec le nombre d'effets.

    Le compte se fait sur `catalog()`, pas sur la table brute : il doit
    correspondre à ce que le panneau affichera réellement (alias compris).
    """
    counts = {}
    for spec in catalog().values():
        c = spec.get("cat")
        counts[c] = counts.get(c, 0) + 1
    return [{"id": cid, "label": lab, "count": counts.get(cid, 0)}
            for cid, lab in CATEGORIES]


def param_spec(name, effect_type=None):
    """Bornes d'un paramètre, éventuellement surchargées par l'effet."""
    base = dict(_PARAM_DEFAULTS.get(name) or
                {"type": "range", "min": 0, "max": 100, "step": 1,
                 "default": 50, "label": name})
    entry = _CATALOG.get(effect_type or "")
    if entry and len(entry) > 4:
        base.update(entry[4].get(name) or {})
    if name == "preset":
        if effect_type in ("grade", "lut"):
            base["choices"] = list(GRADES)
        elif effect_type == "colorize":
            base["choices"] = list(COLORIZE)
        elif effect_type == "lensdistort":
            base["choices"] = ["barillet", "coussinet"]
        if base["choices"]:
            base["default"] = base["choices"][0]
    return base


def catalog():
    """Catalogue complet pour le panneau Effets et pour /api/effects/catalog.

    Forme conservée depuis la Phase 2 (dict indexé par type, `label`,
    `params` = liste de noms, `presets` = liste) — le bundle compilé et
    /api/montage/effects s'appuient dessus. S'y ajoutent `cat` (catégorie),
    `hint` (aide) et `bounds` (bornes par paramètre).
    """
    out = {}
    for name, entry in _CATALOG.items():
        cat, label, params, hint = entry[0], entry[1], entry[2], entry[3]
        spec = {"label": label, "cat": cat, "hint": hint,
                "params": list(params),
                "bounds": {p: param_spec(p, name) for p in params}}
        if "preset" in params:
            spec["presets"] = list(spec["bounds"]["preset"].get("choices") or [])
        out[name] = spec
    # « lut » reste exposé (compat) mais pointe sur la même définition.
    for alias, target in _ALIASES.items():
        if target in out:
            out[alias] = dict(out[target], label=out[target]["label"])
    return out
