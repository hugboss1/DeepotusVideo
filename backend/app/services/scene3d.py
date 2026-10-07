# -*- coding: utf-8 -*-
"""Le Plateau 3D — la géométrie PURE (t127 T1, 07/10/2026).

Spec : docs/superpowers/specs/2026-08-29-plateau-previsualisation-3d-design.md §5 ; plan :
docs/superpowers/plans/2026-10-07-plan-plateau-3d.md. Aucune E/S : des nombres entrent, des nombres sortent — le banc
`tests/test_scene3d.py` recalcule chaque attendu à la main.

Conventions (gardées de la spec, qui les prenait à <model-viewer>) :
  * orbite [θ°, φ°, r] : θ = azimut autour de +Y compté depuis +Z, φ = angle polaire depuis +Y (90° = à l'horizon de
    la cible), r = distance caméra → cible en mètres. La caméra regarde la cible, le haut est +Y ;
  * une instance est posée PAR LE PIED : `pos` est le centre de sa base, sa boîte va de y à y + hauteur ; `dims` =
    [largeur x, hauteur y, profondeur z] en mètres avant échelle ; `rot` = angles d'Euler en degrés, ordre XYZ (celui
    de three.js, que l'écran emploie) ;
  * `fov` = champ VERTICAL en degrés ; l'aspect (largeur / hauteur) vient du format de la scène.

`h` = la fraction de la hauteur d'image qu'occupe la boîte du SUJET, NON écrêtée (au-delà de 1, le sujet déborde : gros
plan extrême). `dans_cadre` = la boîte entière est dans le cadre. Le `shot_type` découle de `h` par des seuils
CONFIGURABLES, rendus avec la mesure (§5.2 : une convention de cadrage, pas une loi).

Le mouvement (§5.3) se lit sur les deltas du premier au dernier keyframe, dans le vocabulaire du storyboard
(`schemas.CameraMove`). Écarts DATÉS par rapport à la table de la spec :
  * la grue se juge sur la HAUTEUR réelle de la caméra (y), pas sur φ : la spec écrit « φ ↓ (caméra descend) », ce qui
    contredit sa propre convention (φ compté depuis +Y : une caméra qui descend vers l'horizon voit φ AUGMENTER) ;
  * le dolly zoom est reconnu dans les deux sens (rayon ↓ et fov ↑, ou rayon ↑ et fov ↓) ;
  * une grue MONTANTE n'a pas de valeur dans le vocabulaire : plan fixe + avertissement qui le dit ;
  * `handheld`, `rack focus` ne sont jamais mesurés ; `low angle dramatic` est un ATTRIBUT (φ > 95° à un keyframe),
    proposé dans `attributs`, jamais rendu comme mouvement.
"""
import math

ASPECTS = {"16:9": 16 / 9, "9:16": 9 / 16, "1:1": 1.0, "2.39:1": 2.39}
SEUILS = {"establishing": 0.20, "wide": 0.45, "medium": 0.75, "close-up": 0.95}
_ORDRE_TYPES = ["establishing", "wide", "medium", "close-up"]
EASINGS = ("linear", "ease-in", "ease-out", "ease-in-out")
_SEUIL_MVT = 0.08            # en dessous (rapporté au rayon ou à 90°), un delta ne compte pas
_ECHANTILLONS = 24           # pas de vérification « sujet hors du cadre » le long du mouvement


def _num(v, nom, mini=None, strict=False):
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ValueError(f"{nom} illisible.")
    if not math.isfinite(f) or (mini is not None and (f <= mini if strict else f < mini)):
        raise ValueError(f"{nom} hors bornes.")
    return f


def _vec(v, nom, n=3):
    if not isinstance(v, (list, tuple)) or len(v) != n:
        raise ValueError(f"{nom} : {n} nombres attendus.")
    return [_num(x, nom) for x in v]


# ── §5.1 focale ↔ champ ──────────────────────────────────────────────────────
def fov_de_focale(focale_mm, capteur_mm=14.2) -> float:
    f = _num(focale_mm, "focale", 0, strict=True)
    c = _num(capteur_mm, "capteur", 0, strict=True)
    return math.degrees(2 * math.atan(c / (2 * f)))


def focale_de_fov(fov_deg, capteur_mm=14.2) -> float:
    a = _num(fov_deg, "fov", 0, strict=True)
    if a >= 180:
        raise ValueError("fov hors bornes.")
    c = _num(capteur_mm, "capteur", 0, strict=True)
    return c / (2 * math.tan(math.radians(a) / 2))


# ── orbite → caméra ──────────────────────────────────────────────────────────
def position_camera(orbit, target) -> list:
    th, ph, r = _vec(orbit, "orbit")
    tx, ty, tz = _vec(target, "target")
    t, p = math.radians(th), math.radians(ph)
    return [tx + r * math.sin(p) * math.sin(t), ty + r * math.cos(p), tz + r * math.sin(p) * math.cos(t)]


def _base(pos, target):
    f = [target[i] - pos[i] for i in range(3)]
    n = math.sqrt(sum(x * x for x in f))
    if n < 1e-9:
        raise ValueError("caméra confondue avec sa cible.")
    f = [x / n for x in f]
    up = [0.0, 1.0, 0.0]
    if abs(f[1]) > 1 - 1e-9:                 # visée verticale : le « haut » de l'image devient -Z
        up = [0.0, 0.0, -1.0]
    rx = [f[1] * up[2] - f[2] * up[1], f[2] * up[0] - f[0] * up[2], f[0] * up[1] - f[1] * up[0]]
    nr = math.sqrt(sum(x * x for x in rx))
    rx = [x / nr for x in rx]
    u = [rx[1] * f[2] - rx[2] * f[1], rx[2] * f[0] - rx[0] * f[2], rx[0] * f[1] - rx[1] * f[0]]
    return f, rx, u


def projeter(points, camera, aspect) -> list:
    """Chaque point monde → (ndc_x, ndc_y, profondeur). ndc ∈ [-1, 1] dans le cadre ; profondeur ≤ 0 = derrière."""
    pos = position_camera(camera["orbit"], camera["target"])
    target = _vec(camera["target"], "target")
    fov = _num(camera.get("fov"), "fov", 0, strict=True)
    f, rx, u = _base(pos, target)
    tv = math.tan(math.radians(fov) / 2)
    out = []
    for p in points:
        d = [p[i] - pos[i] for i in range(3)]
        z = sum(d[i] * f[i] for i in range(3))
        x = sum(d[i] * rx[i] for i in range(3))
        y = sum(d[i] * u[i] for i in range(3))
        if z <= 1e-9:
            out.append((None, None, z))
        else:
            out.append((x / (z * tv * aspect), y / (z * tv), z))
    return out


# ── les instances ────────────────────────────────────────────────────────────
def _rotation(rot):
    """Matrice 3×3 des angles d'Euler en degrés, ordre XYZ intrinsèque (three.js : M = Rx·Ry·Rz)."""
    a, b, c = (math.radians(x) for x in rot)
    ca, sa, cb, sb, cc, sc = math.cos(a), math.sin(a), math.cos(b), math.sin(b), math.cos(c), math.sin(c)
    rxm = [[1, 0, 0], [0, ca, -sa], [0, sa, ca]]
    rym = [[cb, 0, sb], [0, 1, 0], [-sb, 0, cb]]
    rzm = [[cc, -sc, 0], [sc, cc, 0], [0, 0, 1]]

    def mul(m, n):
        return [[sum(m[i][k] * n[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    return mul(mul(rxm, rym), rzm)


def coins(instance) -> list:
    """Les 8 coins monde de la boîte d'une instance (posée par le pied, puis échelle, rotation, translation)."""
    w, h, d = _vec(instance.get("dims"), "dims")
    if min(w, h, d) <= 0:
        raise ValueError("dims : trois longueurs positives attendues.")
    tr = instance.get("transform") or {}
    pos = _vec(tr.get("pos", [0, 0, 0]), "pos")
    rot = _vec(tr.get("rot", [0, 0, 0]), "rot")
    s = _num(tr.get("scale", 1), "scale", 0, strict=True)
    m = _rotation(rot)
    out = []
    for x in (-w / 2, w / 2):
        for y in (0.0, h):
            for z in (-d / 2, d / 2):
                v = [x * s, y * s, z * s]
                out.append([pos[i] + sum(m[i][k] * v[k] for k in range(3)) for i in range(3)])
    return out


def sujet(scene):
    for inst in (scene or {}).get("instances") or []:
        if isinstance(inst, dict) and inst.get("role") == "sujet":
            return inst
    raise ValueError("aucun sujet dans la scène : marquez une instance « sujet ».")


def aspect_de(scene) -> float:
    a = (scene or {}).get("aspect", "16:9")
    if a not in ASPECTS:
        raise ValueError(f"aspect inconnu ({a}) : {', '.join(ASPECTS)}.")
    return ASPECTS[a]


# ── §5.2 shot_type mesuré ────────────────────────────────────────────────────
def type_de_plan(h, seuils=None) -> str:
    s = dict(SEUILS, **(seuils or {}))
    for nom in _ORDRE_TYPES:
        if h < s[nom]:
            return nom
    return "extreme close-up"


def mesure(scene, camera, seuils=None) -> dict:
    asp = aspect_de(scene)
    cs = coins(sujet(scene))
    pr = projeter(cs, camera, asp)
    devant = [p for p in pr if p[0] is not None]
    if not devant:
        h, dedans = 0.0, False
    else:
        ys = [p[1] for p in devant]
        h = (max(ys) - min(ys)) / 2
        dedans = len(devant) == 8 and all(abs(p[0]) <= 1 and abs(p[1]) <= 1 for p in devant)
    s = dict(SEUILS, **(seuils or {}))
    cap = _num((scene or {}).get("capteur_mm", 14.2), "capteur", 0, strict=True)
    return {"h": round(h, 4), "shot_type": type_de_plan(h, s), "seuils": s,
            "distance_m": _vec(camera["orbit"], "orbit")[2],
            "fov": _num(camera.get("fov"), "fov", 0, strict=True),
            "focale_mm": round(focale_de_fov(camera["fov"], cap), 3), "dans_cadre": dedans}


def _centre_ndc(scene, camera):
    cs = coins(sujet(scene))
    c = [sum(p[i] for p in cs) / 8 for i in range(3)]
    return projeter([c], camera, aspect_de(scene))[0]


# ── keyframes ────────────────────────────────────────────────────────────────
def _ease(u, nom):
    if nom == "ease-in":
        return u * u
    if nom == "ease-out":
        return 1 - (1 - u) * (1 - u)
    if nom == "ease-in-out":
        return u * u * (3 - 2 * u)
    return u


def valider_keyframes(kfs) -> list:
    if not isinstance(kfs, list) or not kfs:
        raise ValueError("au moins un keyframe.")
    out, prev = [], None
    for k in kfs:
        if not isinstance(k, dict):
            raise ValueError("keyframe illisible.")
        t = _num(k.get("t"), "t", 0)
        if prev is not None and t <= prev:
            raise ValueError("les keyframes doivent avancer dans le temps.")
        e = k.get("easing", "ease-in-out")
        if e not in EASINGS:
            raise ValueError(f"easing inconnu ({e}).")
        orbit = _vec(k.get("orbit"), "orbit")
        if orbit[2] <= 0:
            raise ValueError("rayon d'orbite hors bornes.")
        out.append({"t": t, "orbit": orbit, "target": _vec(k.get("target"), "target"),
                    "fov": _num(k.get("fov"), "fov", 0, strict=True), "easing": e})
        prev = t
    return out


def interpoler(kfs, t) -> dict:
    ks = valider_keyframes(kfs)
    if t <= ks[0]["t"] or len(ks) == 1:
        k = ks[0] if t <= ks[0]["t"] or len(ks) == 1 else ks[-1]
        return {"orbit": list(k["orbit"]), "target": list(k["target"]), "fov": k["fov"]}
    if t >= ks[-1]["t"]:
        k = ks[-1]
        return {"orbit": list(k["orbit"]), "target": list(k["target"]), "fov": k["fov"]}
    for a, b in zip(ks, ks[1:]):
        if a["t"] <= t <= b["t"]:
            u = _ease((t - a["t"]) / (b["t"] - a["t"]), a["easing"])
            lerp = lambda x, y: x + (y - x) * u   # noqa: E731
            return {"orbit": [lerp(a["orbit"][i], b["orbit"][i]) for i in range(3)],
                    "target": [lerp(a["target"][i], b["target"][i]) for i in range(3)],
                    "fov": lerp(a["fov"], b["fov"])}
    raise AssertionError("inatteignable")


# ── §5.3 le mouvement ───────────────────────────────────────────────────────
def _f1(x):
    return f"{x:.1f}"


def mouvement(scene, kfs, capteur_mm=None) -> dict:
    ks = valider_keyframes(kfs)
    cap = capteur_mm if capteur_mm is not None else (scene or {}).get("capteur_mm", 14.2)
    a, b = ks[0], ks[-1]
    r0, r1 = a["orbit"][2], b["orbit"][2]
    ya = position_camera(a["orbit"], a["target"])[1]
    yb = position_camera(b["orbit"], b["target"])[1]
    dth = b["orbit"][0] - a["orbit"][0]
    dtgt = math.dist(a["target"], b["target"])
    d = {"rayon": (r1 - r0) / r0, "theta": dth / 90, "hauteur": (yb - ya) / r0, "cible": dtgt / r0,
         "fov": (b["fov"] - a["fov"]) / a["fov"]}
    avert, attributs = [], []
    if any(k["orbit"][1] > 95 for k in ks):
        attributs.append("low angle dramatic")
    whip = any(n["t"] - m["t"] < 0.5 and abs(n["orbit"][0] - m["orbit"][0]) >= 60 for m, n in zip(ks, ks[1:]))
    if abs(d["rayon"]) > 0.1 and abs(d["fov"]) > 0.1 and d["rayon"] * d["fov"] < 0:
        move = "dolly zoom (vertigo effect)"
    elif abs(dth) >= 300:
        move = "360-degree orbit"
    elif whip:
        move = "whip pan transition"
    else:
        dom = max(("rayon", "theta", "hauteur", "cible"), key=lambda k: abs(d[k]))
        if abs(d[dom]) < _SEUIL_MVT:
            move = "static, locked-off"
        elif dom == "rayon":
            move = "slow push-in" if d["rayon"] < 0 else "slow pull-out"
        elif dom == "cible":
            move = "tracking shot"
        elif dom == "hauteur" and d["hauteur"] < 0:
            move = "crane shot descending"
        else:
            move = "static, locked-off"
            avert.append("grue montante ou orbite partielle : aucune valeur du vocabulaire ne la nomme — "
                         "choisissez le mouvement à la main.")
    # le sujet sort-il du cadre en cours de route ? (son CENTRE : un gros plan qui déborde n'est pas une sortie)
    if len(ks) > 1:
        hors = []
        for i in range(_ECHANTILLONS + 1):
            t = a["t"] + (b["t"] - a["t"]) * i / _ECHANTILLONS
            c = _centre_ndc(scene, interpoler(ks, t))
            if c[0] is None or abs(c[0]) > 1 or abs(c[1]) > 1:
                hors.append(t)
        if hors:
            avert.append(f"le sujet sort du cadre entre {hors[0]:.2f} s et {hors[-1]:.2f} s (son centre est hors "
                         "du cadre) — hors du cadre.")
    # §5.4 le prompt, depuis les chiffres
    f1 = focale_de_fov(b["fov"], cap)
    if move == "slow push-in":
        tete = f"slow dolly in from {_f1(r0)} m to {_f1(r1)} m"
    elif move == "slow pull-out":
        tete = f"slow dolly out from {_f1(r0)} m to {_f1(r1)} m"
    elif move == "360-degree orbit":
        tete = f"360-degree orbit around the subject at {_f1(r0)} m"
    elif move == "tracking shot":
        tete = f"tracking shot following the subject over {_f1(dtgt)} m"
    elif move == "crane shot descending":
        tete = f"crane down from {_f1(ya)} m to {_f1(yb)} m camera height"
    elif move == "dolly zoom (vertigo effect)":
        tete = f"dolly zoom from {_f1(r0)} m at {focale_de_fov(a['fov'], cap):.0f} mm to {_f1(r1)} m at {f1:.0f} mm"
    elif move == "whip pan transition":
        tete = f"whip pan of {abs(dth):.0f} degrees"
    else:
        tete = f"static, locked-off shot at {_f1(r1)} m"
    c = _centre_ndc(scene, {"orbit": b["orbit"], "target": b["target"], "fov": b["fov"]})
    if c[0] is None or abs(c[0]) <= 1 / 3:
        place = "subject centered"
    else:
        place = "subject held on the " + ("left" if c[0] < 0 else "right") + " third"
    ph = b["orbit"][1]
    angle = "eye-level" if 80 <= ph <= 100 else ("high angle" if ph < 80 else "low angle")
    prompt = f"{tete}, {place}, {angle}, {f1:.0f} mm"
    return {"camera_move": move, "motion_prompt": prompt, "avertissements": avert, "attributs": attributs,
            "deltas": {k: round(v, 4) for k, v in d.items()}}
