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
    op = _clamp01(float(eff.get("opacity", 40)) / 100.0)
    mode = str(eff.get("blend", "screen"))
    a = math.radians(float(eff.get("angle", 45)))
    dx, dy = math.cos(a), math.sin(a)
    x0 = int(w / 2 - dx * w / 2); y0 = int(h / 2 - dy * h / 2)
    x1 = int(w / 2 + dx * w / 2); y1 = int(h / 2 + dy * h / 2)
    return [f"gradients=s={w}x{h}:c0={c0}:c1={c1}:x0={x0}:y0={y0}:x1={x1}:y1={y1}:nb_colors=2[{u}g]",
            f"[{i}][{u}g]blend=all_mode={mode}:all_opacity={op:.2f}[{o}]"]


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
            f"[{u}b]gblur=sigma={8 + 24 * t:.1f},eq=brightness=0.06[{u}bl]",
            f"[{u}a][{u}bl]blend=all_mode=screen:all_opacity={0.3 + 0.5 * t:.2f}[{o}]"]


def _halation(eff, i, o, u, ctx):
    t = _inten(eff, 60)
    return [f"[{i}]split=2[{u}a][{u}b]",
            f"[{u}b]curves=preset=lighter,gblur=sigma={10 + 26 * t:.1f},"
            f"colorbalance=rs=0.25:rm=0.15[{u}bl]",
            f"[{u}a][{u}bl]blend=all_mode=screen:all_opacity={0.25 + 0.45 * t:.2f}[{o}]"]


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
            f"[{u}b]gblur=sigma={6 + 18 * t:.1f}[{u}bl]",
            f"[{u}a][{u}bl]blend=all_mode=screen:all_opacity={0.3 + 0.4 * t:.2f}[{o}]"]


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
    return [f"[{i}]crop=iw/2:ih:0:0[{u}l]",
            f"[{u}l]split=2[{u}l1][{u}l2]",
            f"[{u}l2]hflip[{u}r]",
            f"[{u}l1][{u}r]hstack=inputs=2[{o}]"]


def _invert(eff, i, o, u, ctx):
    return _one(i, o, "negate")


EFFECTS = {
    "grade": _grade, "lut": _grade, "colorize": _colorize, "vhs": _vhs,
    "gradient": _gradient, "grain": _grain, "vignette": _vignette,
    "chroma": _chroma, "glitch": _glitch, "bloom": _bloom, "halation": _halation,
    "scanlines": _scanlines, "letterbox": _letterbox, "oldfilm": _oldfilm,
    "sharpen": _sharpen, "blur": _blur, "dreamy": _dreamy, "pixelate": _pixelate,
    "shake": _shake, "mirror": _mirror, "invert": _invert,
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
_NO_CROSSFADE = ("shake",)


def _ease_at(spec, u):
    """Valeur 0..1 de la courbe en u. Réutilise `ease()` d'animation_service,
    qui gère à la fois les presets nommés et la forme cubic-bezier(a,b,c,d)."""
    from app.services.animation_service import ease
    return ease(spec or "smooth", max(0.0, min(1.0, u)))


def _opacity_cmds(target, t0, t1, fade_in, fade_out, ease_in, ease_out):
    """Commandes sendcmd pilotant all_opacity du blend `target`.

    all_opacity n'accepte PAS d'expression (option flottante) ; il est en
    revanche commandable à l'exécution. On échantillonne donc la courbe côté
    Python et on émet une commande par pas — évaluée une fois par image, là
    où une expression `all_expr` coûterait un calcul par pixel.
    """
    cmds = []

    def at(t, v):
        cmds.append(f"{max(0.0, t):.3f} {target} all_opacity {max(0.0, min(1.0, v)):.4f}")

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

    tag = f"blend@{uid}"
    inner = f"{uid}w"
    body = []
    for st in stmts:
        body.append(st.replace(f"[{in_lbl}]", f"[{uid}b]", 1)
                      .replace(f"[{out_lbl}]", f"[{inner}]"))
    cmds = _opacity_cmds(tag, t0, t1, fi, fo, eff.get("ease_in"), eff.get("ease_out"))
    # Dans blend, la PREMIÈRE entrée est le calque du dessus et all_opacity
    # est SON opacité : c'est donc l'effet qui doit venir en premier pour que
    # l'opacité 0 laisse voir l'original.
    return ([f"[{in_lbl}]split=2[{uid}a][{uid}b]"] + body +
            [f"[{uid}a]sendcmd=c='{cmds}'[{uid}a2]",
             f"[{inner}][{uid}a2]blend@{uid}=all_mode=normal:all_opacity=0[{out_lbl}]"])


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


def catalog():
    """Describe available effects for the Studio panel (Phase 2)."""
    return {
        "grade": {"label": "LUT / Grade", "presets": list(GRADES), "params": ["preset", "file"]},
        "colorize": {"label": "Colorisation", "presets": list(COLORIZE), "params": ["preset", "intensity"]},
        "vhs": {"label": "VHS", "params": ["intensity", "speed"]},
        "gradient": {"label": "Dégradé", "params": ["c0", "c1", "angle", "opacity", "blend"]},
        "grain": {"label": "Grain film", "params": ["intensity"]},
        "vignette": {"label": "Vignette", "params": ["intensity"]},
        "chroma": {"label": "Aberration chromatique", "params": ["intensity"]},
        "glitch": {"label": "Glitch", "params": ["intensity"]},
        "bloom": {"label": "Bloom / Glow", "params": ["intensity"]},
        "halation": {"label": "Halation", "params": ["intensity"]},
        "scanlines": {"label": "Scanlines / CRT", "params": ["intensity"]},
        "letterbox": {"label": "Letterbox ciné", "params": ["ratio"]},
        "oldfilm": {"label": "Old film", "params": ["intensity"]},
        "sharpen": {"label": "Netteté", "params": ["intensity"]},
        "blur": {"label": "Flou", "params": ["intensity"]},
        "dreamy": {"label": "Soft / Dreamy", "params": ["intensity"]},
        "pixelate": {"label": "Pixelate", "params": ["intensity"]},
        "shake": {"label": "Camera shake", "params": ["intensity", "speed"]},
        "mirror": {"label": "Miroir", "params": []},
        "invert": {"label": "Négatif", "params": []},
    }
