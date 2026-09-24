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
import re


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
    # L5 (24/09/2026) : la longueur seule ne suffisait pas — « ;[x]ab »
    # fait 6 caractères et partait tel quel dans le `-filter_complex` (le rendu
    # du Montage n'applique pas coerce_params). Chiffres hexadécimaux seulement.
    if len(s) != 6 or any(ch not in "0123456789abcdefABCDEF" for ch in s):
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


def _grade_basic(eff, i, o, u, ctx):
    """Étalonnage de base : température, exposition, contraste, saturation.

    ORDRE ÉMIS : `colortemperature` D'ABORD, `eq` ensuite. C'est l'ordre
    d'étalonnage usuel (balance des blancs, puis exposition/contraste/
    saturation), et surtout le seul où le curseur « saturation » reste une
    saturation. MESURÉ (protocole ci-dessous, `saturation`=0 + 3200 K),
    distance moyenne au gris par pixel — d = √((R−m)²+(G−m)²+(B−m)²) avec
    m = (R+G+B)/3, nulle si et seulement si R=G=B :
        aplat 0x2040a0 : source 94,205 → `eq` puis `ct` 24,042 ; `ct` puis
                         `eq` 2,160 ;
        mire testsrc2  : source 194,872 → `eq` puis `ct` 46,151 ; `ct` puis
                         `eq` 2,376.
    Avec `eq` en tête, `saturation`=0 grise l'image et `colortemperature` la
    RE-TEINTE aussitôt : un sépia franc là où l'utilisateur a demandé du gris.
    Verrouillé au caractère près par `k3200_chaine_entiere` et
    `bornes_opposees_ramenees` de test_montage_etalonnage.py.

    `eq` est TOUJOURS émis — mesuré, `eq=brightness=0:contrast=1:saturation=1`
    est l'identité EXACTE.

    `colortemperature` est OMIS à 6500 K, et ce n'est pas une coquetterie : le
    filtre n'est PAS l'identité à sa propre référence.

    PROTOCOLE DES CHIFFRES QUI SUIVENT — il change le résultat d'un ordre de
    grandeur, donc il se nomme. Source yuv420p (celle du rendu :
    montage_service pose `format=yuv420p` avant `build_chain`), DÉCODÉE une
    fois de chaque côté, filtre appliqué en mémoire, sortie PNG rgb24. Aucun
    SECOND encodage : la perte du codec est commune aux deux branches et
    s'annule. Mesure du 04/09/2026, ffmpeg 8.1.1-essentials du PATH (la
    version se nomme : un encodeur n'est pas l'autre), deux sources 270x480 —
    l'aplat 0x2040a0 et une mire testsrc2, trame à 0,5 s :

        filtre                | pixels changés | extremum/canal | couleurs
                              |                |                | déplacées
        eq neutre     (aplat) |      0/129 600 |      (0, 0, 0) |    0/1
        eq neutre     (mire)  |      0/129 600 |      (0, 0, 0) |    0/8 714
        ct=6500       (aplat) |129 600/129 600 |      (0, 1, 4) |    1/1
        ct=6500       (mire)  |110 299/129 600 |      (0, 1, 5) | 8 637/8 714

    LE CHIFFRE QUI DIT LA CHOSE est la dernière colonne, pas la première :
    sur un aplat, « 129 600 pixels sur 129 600 » compte UNE couleur 129 600
    fois. `colortemperature` à 6500 K déplace 99,1 % des couleurs distinctes
    de la mire ; le témoin `eq` neutre en déplace 0. L'amplitude, elle, est
    minuscule — (0, 1, 5) au pire.

    CORRECTION, gardée visible : un « jusqu'à (82, 89, 99) d'écart par canal »
    a figuré ici. Il sortait d'un DOUBLE encodage h264 (rendu à travers le
    filtre en mp4 yuv420p, puis trame relue). Re-mesuré sous ce protocole sur
    la mire : le témoin `eq` neutre — exact au pixel — y prend (50, 41, 69),
    et `ct=6500` (74, 76, 83). Le (82, 89, 99) lui-même ne se reproduit pas :
    son protocole n'avait pas été dit. Ce qu'il chiffrait de toute façon,
    c'est la perte de génération du codec, pas le filtre.

    Sans l'omission, poser les quatre curseurs au neutre aurait modifié
    l'image — exactement ce qu'un étalonnage neutre ne doit pas faire.
    Verrouillé par `neutre_identique` de test_montage_etalonnage.py.
    """
    ex = _num(eff, "exposure", 0, -100, 100) / 200.0      # eq brightness −0,5..0,5
    ct = _num(eff, "contrast", 100, 0, 200) / 100.0
    sa = _num(eff, "saturation", 100, 0, 200) / 100.0
    k = int(_num(eff, "temperature", 6500, 2000, 12000))
    parts = []
    if k != 6500:
        parts.append(f"colortemperature=temperature={k}")
    parts.append(f"eq=brightness={ex:.3f}:contrast={ct:.3f}:saturation={sa:.3f}")
    return _one(i, o, ",".join(parts))


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
    """Netteté. `mode` (L5, D-33) : `unsharp` (défaut — la commande est
    OCTET POUR OCTET celle d'avant le lot, verrouillée par
    `t1_sharpen_defaut_inchange_et_cas` de test_montage_l5.py) ou `cas`
    (Contrast Adaptive Sharpening, 0,28 s contre 0,24 s mesurés sur 2 s de
    1280x720). Mode inconnu -> `unsharp` (liste fermée, `_choice`)."""
    t = _inten(eff, 60)
    if _choice(eff, "mode", ("unsharp", "cas"), "unsharp") == "cas":
        return _one(i, o, f"cas=strength={t:.2f}")
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


# =============================================================================
# L5 — couleur (D-27 roues, D-28 accord, D-29 courbes + teinte/saturation par
# couleur) et D-33 (effets de correction). Mesures du 24/09/2026 sur ffmpeg
# 9.0.1 (binaire de l'app) ET 8.1.1 (PATH de développement) : valeurs
# identiques. Le rendu du Montage n'applique PAS coerce_params : chaque
# constructeur borne lui-même ses paramètres par `_num` / `_choice`.
# =============================================================================

#: Les quatre courbes à points de l'effet `curves` (maître, rouge, vert, bleu).
_CURVE_KEYS = ("pts_m", "pts_r", "pts_g", "pts_b")

#: Paramètres CACHÉS au rack : le rack (vfxrack.js) dessine un curseur pour
#: tout type qu'il ne connaît pas — une chaîne de points y deviendrait un
#: curseur absurde. `catalog()` les liste sous la clé `points`, hors `params` ;
#: `coerce_params` les garde nettoyés par `curves_clean`.
_HIDDEN = {"curves": _CURVE_KEYS}

_CURVE_IDENT = "0/0 1/1"


def _f3(v):
    """Nombre au millième, sans zéros inutiles : 0.500 -> 0.5, 1.000 -> 1."""
    s = f"{float(v):.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


#: RÈGLE UNIQUE de lecture (24/09/2026 — Python et JS divergeaient ; le client
#: la rejoue sur tests/l5_courbes_vecteurs.json). Séparateurs : blancs ASCII
#: (espace, tab, CR, LF) OU virgules — PAS \x0b, \x0c, \x1c…, ni les blancs
#: Unicode que `str.split()` acceptait. Chiffres ASCII seulement (`\d` de
#: Python accepte « ١ » ou « １ »).
_CURVE_SEP = re.compile(r"[ \t\r\n,]+")
_CURVE_NUM = r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?"
_CURVE_TOK = re.compile(_CURVE_NUM + "/" + _CURVE_NUM)
_CURVE_MAX_TOK = 256


def curves_clean(s) -> str:
    """'x/y x/y …' -> chaîne canonique d'une courbe `curves` de ffmpeg.

    Lecture (règle unique, voir `_CURVE_SEP`) : jetons séparés par blancs
    ASCII ou virgules ; seuls les 256 premiers jetons non vides sont lus
    (invalides compris) ; un jeton valide est EXACTEMENT NOMBRE/NOMBRE
    (décimal ASCII, exposant permis ; ni `_`, ni inf/nan, un seul `/`) ; un
    jeton invalide — ou un nombre qui déborde en infini (1e999) — est SAUTÉ,
    les autres gardés.
    x, y bornés à [0, 1] et arrondis au millième ; triés ; x dupliqués
    fusionnés (le DERNIER gagne) ; extrémités x=0 et x=1 ajoutées si absentes,
    à la valeur du point le plus proche (mesuré : un point UNIQUE donne une
    courbe constante, et ffmpeg refuse (-22) des x non strictement croissants
    ou un y hors [0, 1]) ; 16 points au plus (au-delà : sous-échantillonné en
    gardant les extrémités). Entrée invalide ou vide -> '0/0 1/1'.
    """
    if not isinstance(s, str):
        return _CURVE_IDENT
    pts = {}
    toks = [t for t in _CURVE_SEP.split(s) if t][:_CURVE_MAX_TOK]
    for tok in toks:
        if not _CURVE_TOK.fullmatch(tok):
            continue
        a, _, b = tok.partition("/")
        x, y = float(a), float(b)
        if not (math.isfinite(x) and math.isfinite(y)):
            continue
        x = round(min(1.0, max(0.0, x)), 3) + 0.0
        y = round(min(1.0, max(0.0, y)), 3) + 0.0
        pts[x] = y
    if not pts:
        return _CURVE_IDENT
    xs = sorted(pts)
    if xs[0] != 0.0:
        pts[0.0] = pts[xs[0]]
    if xs[-1] != 1.0:
        pts[1.0] = pts[xs[-1]]
    xs = sorted(pts)
    if len(xs) > 16:
        n = len(xs)
        xs = [xs[k] for k in sorted({round(j * (n - 1) / 15) for j in range(16)})]
    return " ".join(f"{_f3(x)}/{_f3(pts[x])}" for x in xs)


def _choice(eff, key, choices, default):
    """Valeur d'une liste fermée ; toute autre -> `default`."""
    v = str(eff.get(key, default))
    return v if v in choices else default


def _wheels(eff, i, o, u, ctx):
    """D-27 — roues lift / gamma / gain, par canal RVB.

    PAS `colorbalance` : mesuré sur un gris 128, `rs=0.3` ne bouge rien (il
    n'agit que sur les ombres) — inutilisable comme décalage. PAS `eq`
    `gamma_r/g/b` : il agit sur les plans YUV, pas RVB. Formule mesurée
    (rampe 0/64/128/192/255, L/G/Γ = 0.1/1.2/1.5 -> R [54,132,191,242,255],
    écart <= 1 niveau au calcul Python) :
        out = 255 · clip(L + (val/255)·(G − L), 0, 1) ^ (1/Γ)
    Canal neutre (L 0, G 1, Γ 1) -> `val` ; tout neutre -> `null`.
    """
    parts, actif = [], False
    for ch in "rgb":
        lo = round(_num(eff, f"lift_{ch}", 0, -0.5, 0.5), 3)
        ga = round(_num(eff, f"gamma_{ch}", 1, 0.25, 4), 3)
        gn = round(_num(eff, f"gain_{ch}", 1, 0, 2), 3)
        if lo == 0 and ga == 1 and gn == 1:
            parts.append(f"{ch}='val'")
            continue
        actif = True
        parts.append(f"{ch}='255*pow(clip({lo:.3f}+(val/255)*({gn:.3f}-({lo:.3f})),0,1),"
                     f"{1.0 / ga:.4f})'")
    if not actif:
        return _one(i, o, "null")
    return _one(i, o, "lutrgb=" + ":".join(parts))


def _curves(eff, i, o, u, ctx):
    """D-29 — courbes à points (maître + RVB), interpolation `pchip`
    (monotone : pas de dépassement entre deux points, mesuré 64 -> 83 contre
    81 en `natural`). Seules les courbes non identité sont émises ; le maître
    s'applique APRÈS les canaux (mesuré). Tout identité -> `null`."""
    parts = []
    for key, letter in zip(_CURVE_KEYS, "mrgb"):
        s = curves_clean(eff.get(key, _CURVE_IDENT))
        if all(a == b for a, b in (p.split("/") for p in s.split(" "))):
            continue
        parts.append(f"{letter}='{s}'")
    if not parts:
        return _one(i, o, "null")
    return _one(i, o, "curves=interp=pchip:" + ":".join(parts))


def _colormatch(eff, i, o, u, ctx):
    """D-28 — accord de couleur : transfert affine par plan en `lutyuv`,
    PIVOTÉ autour de 128 (décision du contrôleur, 24/09/2026) :
        out = clip((val − 128)·G + 128 + O, 0, 255)
    Sans pivot, un gain sur U/V déplaçait un gris neutre (mesuré : U 128 ->
    192 pour un gain 1,5) ; pivoté, le gris reste à 128 ±2 et seul O le
    décale. Plage LIMITÉE, celle du flux yuv420p du rendu (mesuré Y 126 ->
    ~136 pour G 1,2 et O 10). Les gains et décalages sont calculés par
    color_match.py ; ici on ne fait que les borner et les émettre, les trois
    plans sous la même forme. Tout neutre -> `null`."""
    parts, actif = [], False
    for p in "yuv":
        g = round(_num(eff, f"{p}_gain", 1, 0.5, 2), 3)
        off = round(_num(eff, f"{p}_off", 0, -128, 128), 3)
        actif = actif or g != 1 or off != 0
        parts.append(f"{p}='clip((val-128)*{g:.3f}+128{off:+.3f},0,255)'")
    if not actif:
        return _one(i, o, "null")
    return _one(i, o, "lutyuv=" + ":".join(parts))


_HUESAT_COLORS = ("a", "r", "y", "g", "c", "b", "m")


def _huesat(eff, i, o, u, ctx):
    """D-29 — teinte / saturation par couleur (`huesaturation`). Mesuré :
    `saturation=-1:colors=r` ne touche QUE la bande rouge ((200,40,40) ->
    (133,73,73)) à la force 1 ; une désaturation complète demande `strength`
    10 — c'est donc la force PAR DÉFAUT (revue T1, M-4). `a` = toutes les
    couleurs. Teinte 0 et saturation 0 -> `null`."""
    h = round(_num(eff, "hue", 0, -180, 180), 1)
    s = round(_num(eff, "sat", 0, -100, 100), 1)
    if h == 0 and s == 0:
        return _one(i, o, "null")
    st = _num(eff, "strength", 10, 1, 100)
    col = _choice(eff, "colors", _HUESAT_COLORS, "a")
    cols = "r+y+g+c+b+m+a" if col == "a" else col
    return _one(i, o, f"huesaturation=hue={h:.1f}:saturation={s / 100.0:.3f}:"
                      f"strength={st:.1f}:colors={cols}")


def _monochrome(eff, i, o, u, ctx):
    """Monochrome teinté : `cb`/`cr` placent la teinte du filtre coloré. Pas
    d'identité (un monochrome est toujours gris)."""
    cb = _num(eff, "cb", 0, -1, 1)
    cr = _num(eff, "cr", 0, -1, 1)
    return _one(i, o, f"monochrome=cb={cb:.2f}:cr={cr:.2f}:size=1:high=0")


def _denoise(eff, i, o, u, ctx):
    """D-33 — débruitage. `nlmeans` ÉCARTÉ (88 s pour 2 s de 720p, 19 s même
    allégé). `hqdn3d` (0,34 s) ou `atadenoise` (0,26 s). t = intensité/50,
    donc t ∈ [0, 2] : l'intensité par défaut (50) donne les valeurs mesurées
    4:3:6:4.5 et, en atadenoise, les seuils par défaut de ffmpeg (a 0,02,
    b 0,04) ; à 100 ils doublent (0,04 / 0,08), loin des plafonds de ffmpeg
    (0,3 / 5) — d'où aucun `min` ici. 0 -> `null`."""
    t = _num(eff, "intensity", 50, 0, 100) / 50.0
    if t <= 0:
        return _one(i, o, "null")
    if _choice(eff, "mode", ("hqdn3d", "atadenoise"), "hqdn3d") == "atadenoise":
        a, b = 0.02 * t, 0.04 * t
        th = ":".join(f"{p}a={a:.4f}:{p}b={b:.4f}" for p in "012")
        return _one(i, o, f"atadenoise={th}:s=9")
    return _one(i, o, f"hqdn3d={4 * t:.3f}:{3 * t:.3f}:{6 * t:.3f}:{4.5 * t:.3f}")


def _deflicker(eff, i, o, u, ctx):
    """D-33 — anti-scintillement (moyenne arithmétique de N images)."""
    n = int(round(_num(eff, "size", 5, 2, 15)))
    return _one(i, o, f"deflicker=size={n}:mode=am")


def _deband(eff, i, o, u, ctx):
    """D-33 — anti-escaliers de dégradé. Seuil 0,005 + 0,04·t sur les trois
    plans (0,02 = défaut ffmpeg à t ≈ 0,375)."""
    t = _inten(eff, 40)
    thr = 0.005 + 0.04 * t
    return _one(i, o, f"deband=1thr={thr:.3f}:2thr={thr:.3f}:3thr={thr:.3f}:range=16:blur=1")


def _chromakey(eff, i, o, u, ctx):
    """D-33 — clé couleur. Mesuré : `chromakey=color=0x00FF00:similarity=0.1`
    puis `overlay` rend le vert transparent ; `despill` nettoie le bord
    ((104,84,85) -> (84,0,85)). Piège : `color=c=green` vaut 0x007F00, d'où
    une couleur hexadécimale explicite. L'alpha n'a de sens que sur un plan
    SUPERPOSÉ (V2) : sur V1, le `format=yuv420p` du rendu le perd."""
    key = _c(eff.get("key", "#00ff00"), "00ff00")
    sim = _num(eff, "similarity", 10, 1, 100) / 100.0
    bl = _num(eff, "smooth", 0, 0, 100) / 100.0
    sp = _choice(eff, "despill", ("aucun", "vert", "bleu"), "vert")
    tail = {"vert": ",despill=type=green", "bleu": ",despill=type=blue"}.get(sp, "")
    return _one(i, o, f"format=yuva420p,chromakey=color={key}:similarity={sim:.3f}:"
                      f"blend={bl:.3f}{tail}")


def _tmix(eff, i, o, u, ctx):
    """D-33 — fondu d'images successives (traînée / lissage temporel)."""
    return _one(i, o, f"tmix=frames={_choice(eff, 'frames', ('3', '5', '7'), '3')}")


EFFECTS = {
    "grade": _grade, "lut": _grade, "grade_basic": _grade_basic,
    # --- L5 : couleur et correction ---
    "wheels": _wheels, "curves": _curves, "colormatch": _colormatch,
    "huesat": _huesat, "monochrome": _monochrome, "denoise": _denoise,
    "deflicker": _deflicker, "deband": _deband, "chromakey": _chromakey,
    "tmix": _tmix,
    "colorize": _colorize, "vhs": _vhs,
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
    # L5 (D-33) : débruitage, anti-scintillement, anti-escaliers. Le rack
    # (vfxNormCat) affiche toute catégorie servie ici, sans rien côté écran.
    ("correction", "Correction"),
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
    # --- étalonnage de base (P4) : quatre curseurs, quatre bornes. Le panneau
    # (vfxrack.js, `bounds` par effet) les lit ICI : il n'y a rien d'autre à
    # écrire côté écran pour que les curseurs apparaissent.
    "exposure":  {"type": "range", "min": -100, "max": 100, "step": 1,
                  "default": 0, "label": "Exposition"},
    "contrast":  {"type": "range", "min": 0, "max": 200, "step": 1,
                  "default": 100, "label": "Contraste"},
    "saturation": {"type": "range", "min": 0, "max": 200, "step": 1,
                   "default": 100, "label": "Saturation"},
    "temperature": {"type": "range", "min": 2000, "max": 12000, "step": 100,
                    "default": 6500, "label": "Température", "unit": "K"},
    "preset":    {"type": "choice", "choices": [], "default": "",
                  "label": "Préréglage"},
    "file":      {"type": "lut", "default": "", "label": "LUT .cube"},
    # --- L5 (24/09/2026). Aucun de ces noms n'existait : pas de collision de
    # sens avec un gabarit partagé (mesuré avant). `mode` est un gabarit VIDE,
    # chaque effet qui l'emploie fournit ses choix par surcharge (entry[4]).
    **{f"lift_{k}": {"type": "range", "min": -0.5, "max": 0.5, "step": 0.01,
                     "default": 0, "label": f"Lift {n}"}
       for k, n in (("r", "rouge"), ("g", "vert"), ("b", "bleu"))},
    **{f"gamma_{k}": {"type": "range", "min": 0.25, "max": 4, "step": 0.01,
                      "default": 1, "label": f"Gamma {n}"}
       for k, n in (("r", "rouge"), ("g", "vert"), ("b", "bleu"))},
    **{f"gain_{k}": {"type": "range", "min": 0, "max": 2, "step": 0.01,
                     "default": 1, "label": f"Gain {n}"}
       for k, n in (("r", "rouge"), ("g", "vert"), ("b", "bleu"))},
    **{f"{p}_gain": {"type": "range", "min": 0.5, "max": 2, "step": 0.01,
                     "default": 1, "label": f"Gain {p.upper()}"} for p in "yuv"},
    **{f"{p}_off": {"type": "range", "min": -128, "max": 128, "step": 1,
                    "default": 0, "label": f"Décalage {p.upper()}"} for p in "yuv"},
    "hue":       {"type": "range", "min": -180, "max": 180, "step": 1,
                  "default": 0, "label": "Teinte", "unit": "°"},
    "sat":       {"type": "range", "min": -100, "max": 100, "step": 1,
                  "default": 0, "label": "Saturation"},
    "strength":  {"type": "range", "min": 1, "max": 100, "step": 1,
                  "default": 10, "label": "Force"},
    "colors":    {"type": "choice", "choices": list(_HUESAT_COLORS),
                  "default": "a", "label": "Couleurs"},
    "cb":        {"type": "range", "min": -1, "max": 1, "step": 0.01,
                  "default": 0, "label": "Teinte bleue"},
    "cr":        {"type": "range", "min": -1, "max": 1, "step": 0.01,
                  "default": 0, "label": "Teinte rouge"},
    "mode":      {"type": "choice", "choices": [], "default": "",
                  "label": "Mode"},
    "key":       {"type": "color", "default": "#00ff00", "label": "Couleur clé"},
    "similarity": {"type": "range", "min": 1, "max": 100, "step": 1,
                   "default": 10, "label": "Similarité"},
    "smooth":    {"type": "range", "min": 0, "max": 100, "step": 1,
                  "default": 0, "label": "Fondu du bord"},
    "despill":   {"type": "choice", "choices": ["aucun", "vert", "bleu"],
                  "default": "vert", "label": "Débordement"},
    "frames":    {"type": "choice", "choices": ["3", "5", "7"],
                  "default": "3", "label": "Images"},
    "size":      {"type": "range", "min": 2, "max": 15, "step": 1,
                  "default": 5, "label": "Images"},
}

#: (catégorie, libellé, paramètres, aide) + surcharges de bornes éventuelles.
_CATALOG = {
    # --- Étalonnage ---
    "grade":      ("etalonnage", "LUT / Étalonnage", ["preset", "file"],
                   "Ambiances colorimétriques, ou votre propre LUT .cube.", {}),
    # JUSTE APRÈS « grade » : c'est cette position qui met les quatre curseurs
    # SOUS la LUT dans le rack (l'ordre de ce dict est celui de l'affichage).
    # Elle ne dit rien de l'ordre dans la CHAÎNE d'un clip : là, c'est la pile
    # posée par l'utilisateur qui décide.
    "grade_basic": ("etalonnage", "Réglages de base",
                    ["exposure", "contrast", "saturation", "temperature"],
                    "Exposition, contraste, saturation, température — sous la LUT.",
                    {}),
    # --- L5 (D-27/D-28/D-29) : l'étalonnage passe de 6 à 11 (alias lut
    # compris). Les neuf curseurs des roues restent VISIBLES : ce sont les
    # seuls réglages possibles sur un clip d'ajustement (D-9), où le panneau
    # Étalonnage n'est pas monté.
    "wheels":     ("etalonnage", "Roues lift / gamma / gain",
                   [f"{g}_{k}" for g in ("lift", "gamma", "gain") for k in "rgb"],
                   "Ombres, tons moyens, hautes lumières : un réglage par canal.", {}),
    "curves":     ("etalonnage", "Courbes", [],
                   "Courbes à points maître et RVB — se règlent dans le panneau Étalonnage.",
                   {}),
    "huesat":     ("etalonnage", "Teinte / saturation par couleur",
                   ["colors", "hue", "sat", "strength"],
                   "Teinte ou saturation d'une gamme de couleurs ; force 10 = désaturation complète.",
                   {}),
    "colormatch": ("etalonnage", "Accord de couleur",
                   ["y_gain", "y_off", "u_gain", "u_off", "v_gain", "v_off"],
                   "Aligne ce plan sur les statistiques d'un autre (panneau Étalonnage).",
                   {}),
    "monochrome": ("etalonnage", "Monochrome", ["cb", "cr"],
                   "Noir et blanc à travers un filtre coloré.", {}),
    "colorize":   ("etalonnage", "Colorisation", ["preset", "intensity"],
                   "Sépia, noir et blanc, duotone, matrice.", {}),
    "invert":     ("etalonnage", "Négatif", [], "Inverse toutes les couleurs.", {}),
    "posterize":  ("etalonnage", "Postérisation", ["intensity"],
                   "Réduit le nombre de niveaux : aplats façon sérigraphie.", {}),
    # --- Correction (L5, D-33) ---
    "denoise":    ("correction", "Débruitage", ["mode", "intensity"],
                   "Réduit le bruit vidéo : hqdn3d (fort) ou atadenoise (doux).",
                   {"mode": {"choices": ["hqdn3d", "atadenoise"], "default": "hqdn3d"},
                    "intensity": {"default": 50}}),
    "deflicker":  ("correction", "Anti-scintillement", ["size"],
                   "Lisse les variations de luminosité d'une image à l'autre.", {}),
    "deband":     ("correction", "Anti-escaliers", ["intensity"],
                   "Adoucit les marches visibles dans les dégradés.",
                   {"intensity": {"default": 40}}),
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
    "tmix":       ("mouvement", "Traînée d'images", ["frames"],
                   "Mélange les images successives : traînée ou lissage temporel.", {}),
    # --- Cadrage ---
    "letterbox":  ("cadrage", "Bandes cinéma", ["ratio"],
                   "Bandes noires au format choisi.", {}),
    "mirror":     ("cadrage", "Miroir", [], "Symétrie gauche/droite.", {}),
    "kaleido":    ("cadrage", "Kaléidoscope", [],
                   "Symétrie 4 voies, motif de kaléidoscope.", {}),
    "chromakey":  ("cadrage", "Incrustation (clé couleur)",
                   ["key", "similarity", "smooth", "despill"],
                   "Rend transparente une couleur — sur un plan superposé (V2).", {}),
    # --- Stylisation ---
    "pixelate":   ("stylisation", "Pixelisation", ["intensity"],
                   "Gros pixels, façon censure ou jeu rétro.", {}),
    "sharpen":    ("stylisation", "Netteté", ["intensity", "mode"],
                   "Renforce les détails : unsharp (classique) ou cas (adaptatif).",
                   {"mode": {"choices": ["unsharp", "cas"], "default": "unsharp"}}),
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
        if name in _HIDDEN:
            # Paramètres cachés au rack (voir `_HIDDEN`), hors `params`.
            spec["points"] = list(_HIDDEN[name])
        out[name] = spec
    # « lut » reste exposé (compat) mais pointe sur la même définition.
    for alias, target in _ALIASES.items():
        if target in out:
            out[alias] = dict(out[target], label=out[target]["label"])
    return out
