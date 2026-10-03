# -*- coding: utf-8 -*-
"""Plan-templates T9 / D2 (tache #76 du suivi, PR A, 03/10/2026) — ANIMATIONS d'entree et de sortie des regions.

Champ d'une region (facultatif) :
    "animation": {"in":  {"type": T, "duration": s, "delay": s, "easing": E},
                  "out": {"type": T, "duration": s, "delay": s, "easing": E}}
    T : fade | slide_left | slide_right | slide_up | slide_down | pop
        (le nom dit le SENS DU MOUVEMENT, comme les presets d'animation de l'app : slide_left entre par la droite et
        sort par la gauche ; slide_up entre par le bas et sort par le haut ; pop grossit depuis son centre / retrecit)
    E : linear | ease_out | back (rebond, depasse puis revient) — le fondu reste lineaire
    "in"  : commence a `delay` secondes ; "out" : finit `delay` secondes avant la fin du rendu.
Decisions de l'utilisateur (03/10) : fondu, glissement, pop + courbes ; TOUTES les regions visibles (cases, textes,
badges, stickers, separateurs, bandeaux, tickers ; le liseré d'un masque suit sa case) ; SANS animation, la commande
ffmpeg est celle d'avant a l'octet.
Technique (mesuree sur ffmpeg 9.0.1) : la region animee est dessinee par son code habituel sur une COUCHE transparente
(source `color=black@0` creee DANS le graphe — donnee en entree, elle sortait en yuv420p, opaque — puis drawbox avec
`replace=1`, superpositions en `format=auto`) ; la couche recoit fondus (fade alpha=1), puis pour le pop un recadrage
sur la case et un `scale` evalue a chaque image ; elle est posee a des x/y fonctions de t.
Le plan disait le pop impossible (« scale n'accepte pas le temps ») : faux, `scale=...:eval=frame` lit `t`.

Conversion des blocs `transitions` (tache #76, 03/10/2026, decision de l'utilisateur : livres ET personnels, a la
lecture) : le bloc PLURIEL au niveau du gabarit n'etait lu par personne. `convertir_transitions` le remplace par ce que
le moteur lit : `fade_in` -> `animation.in` fondu de la region visee (spatial) ; entree d'un gabarit sequentiel ->
`transition` de l'acte vise (cle singuliere lue par build_sequential_command). Ce que la region porte deja l'emporte.
« cyan_flash » devient un VRAI flash de couleur (decision « 1+2 » : le flash blanc reste `flash`) — voir
build_sequential_command.
"""
from __future__ import annotations

import re

TYPES = ("fade", "slide_left", "slide_right", "slide_up", "slide_down", "pop")
COURBES = ("linear", "ease_out", "back")
VISIBLES = ("video_slot", "image_slot", "text", "text_slot", "badge", "ticker", "sticker", "separator", "brand_strip",
            "component")   # #76 PR E : l'animation d'une instance passe a chacune de ses regions
DUREE_DEFAUT = 0.6


def _n(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def verifier_animations(tpl: dict) -> None:
    """ValueError qui nomme la region et le champ (appele par TemplateEngine._validate)."""
    seq = (tpl or {}).get("render_mode") == "sequential"
    for r in (tpl or {}).get("regions") or []:
        if "animation" not in r or r["animation"] is None:
            continue
        rid, a = r.get("id"), r["animation"]
        if seq:
            raise ValueError(f"Region {rid} : les animations valent pour les gabarits spatiaux (pas séquentiels).")
        if r.get("type") not in VISIBLES:
            raise ValueError(f"Region {rid} : une {r.get('type')} ne s'anime pas (régions visibles seulement).")
        if not isinstance(a, dict) or set(a) - {"in", "out"}:
            raise ValueError(f"Region {rid} : animation attend {{\"in\": …, \"out\": …}}.")
        for sens, m in a.items():
            if m is None:
                continue
            if not isinstance(m, dict) or m.get("type") not in TYPES:
                raise ValueError(f"Region {rid} : animation.{sens}.type parmi {', '.join(TYPES)}.")
            if "duration" in m and not (_n(m["duration"]) and 0.05 <= m["duration"] <= 10):
                raise ValueError(f"Region {rid} : animation.{sens}.duration doit être entre 0.05 et 10 s.")
            if "delay" in m and not (_n(m["delay"]) and 0 <= m["delay"] <= 600):
                raise ValueError(f"Region {rid} : animation.{sens}.delay doit être entre 0 et 600 s.")
            if m.get("easing", "ease_out") not in COURBES:
                raise ValueError(f"Region {rid} : animation.{sens}.easing parmi {', '.join(COURBES)}.")


def normaliser(r: dict) -> dict | None:
    """{"in": {...}|None, "out": {...}|None} complete (durees, delais, courbes par defaut) ; None sans animation."""
    a = r.get("animation")
    if not isinstance(a, dict):
        return None
    out = {}
    for sens in ("in", "out"):
        m = a.get(sens)
        if isinstance(m, dict) and m.get("type") in TYPES:
            out[sens] = {"type": m["type"], "d": float(m.get("duration", DUREE_DEFAUT)), "delai": float(m.get("delay", 0)),
                         "e": m.get("easing", "ease_out")}
        else:
            out[sens] = None
    return out if (out["in"] or out["out"]) else None


def _f(v: float) -> str:
    return f"{round(float(v), 4):g}"


def _courbe(p: str, e: str) -> str:
    """L'expression ffmpeg de la courbe appliquee a p (deja borne a 0..1)."""
    if e == "linear":
        return f"({p})"
    if e == "back":                     # easeOutBack (c1 = 1.70158) : depasse la cible puis revient
        return f"(1+2.70158*pow(({p})-1,3)+1.70158*pow(({p})-1,2))"
    return f"(1-pow(1-({p}),3))"         # ease_out cubique


def _progres(m: dict, duree: float, sortie: bool) -> str:
    """p (0..1) de l'animation : entree de delai a delai+d ; sortie de fin-delai-d a fin-delai."""
    t0 = (duree - m["delai"] - m["d"]) if sortie else m["delai"]
    return f"clip((t-{_f(t0)})/{_f(m['d'])},0,1)"


def chaine(anim: dict, src: str, dst: str, box: tuple, toile: tuple, duree: float) -> tuple:
    """(filtres, x, y) : la couche `src` (toile entiere, rgba) animee jusqu'a `dst`, a poser a (x, y) — expressions de
    t pour l'overlay. Fondus par fade alpha ; glissements par decalage ; pop par recadrage sur la case + scale."""
    rx, ry, rw, rh = box
    W, H = toile
    filtres, cur = [], src
    fx = []
    ent, sor = anim.get("in"), anim.get("out")
    if ent and ent["type"] == "fade":
        fx.append(f"fade=t=in:st={_f(ent['delai'])}:d={_f(ent['d'])}:alpha=1")
    if sor and sor["type"] == "fade":
        fx.append(f"fade=t=out:st={_f(max(0.0, duree - sor['delai'] - sor['d']))}:d={_f(sor['d'])}:alpha=1")
    # glissements : le nom dit le SENS DU MOUVEMENT (convention des presets d'animation de l'app : « slide-left » va de
    # x 70 a 50) ; entree : part du decalage vers 0 ; sortie : va de 0 vers le decalage — hors de la toile
    def decal(m, sortie):
        hors = {"gauche": (-(rx + rw), 0), "droite": (W - rx, 0), "haut": (0, -(ry + rh)), "bas": (0, H - ry)}
        vers = {"slide_left": "gauche", "slide_right": "droite", "slide_up": "haut", "slide_down": "bas"}[m["type"]]
        oppose = {"gauche": "droite", "droite": "gauche", "haut": "bas", "bas": "haut"}
        return hors[vers] if sortie else hors[oppose[vers]]   # on entre par le cote oppose, on sort par le cote vise
    xs, ys = [], []
    for m, sortie in ((ent, False), (sor, True)):
        if m and m["type"].startswith("slide_"):
            dx, dy = decal(m, sortie)
            e = _courbe(_progres(m, duree, sortie), m["e"])
            k = e if sortie else f"(1-{e})"
            if dx:
                xs.append(f"{dx}*{k}")
            if dy:
                ys.append(f"{dy}*{k}")
    pop = [(m, s) for m, s in ((ent, False), (sor, True)) if m and m["type"] == "pop"]
    if pop:
        marge = int(max(rw, rh) * 0.15) + 8                 # le contour, l'ombre et le rebond depassent un peu la case
        x0, y0 = max(0, rx - marge), max(0, ry - marge)
        x1, y1 = min(W, rx + rw + marge), min(H, ry + rh + marge)
        fx.append(f"crop={x1 - x0}:{y1 - y0}:{x0}:{y0}")
        s = []
        for m, sortie in pop:
            e = _courbe(_progres(m, duree, sortie), m["e"])
            s.append(f"(1-{e})" if sortie else e)
        sx = "*".join(s)
        fx.append(f"scale=w='max(1,trunc(iw*max(0.01,{sx})))':h='max(1,trunc(ih*max(0.01,{sx})))':eval=frame")
        cx, cy = x0 + (x1 - x0) / 2, y0 + (y1 - y0) / 2
        bx, by = f"{_f(cx)}-overlay_w/2", f"{_f(cy)}-overlay_h/2"
    else:
        bx, by = "0", "0"
    if fx:
        filtres.append(f"[{cur}]{','.join(fx)}[{dst}]")
    else:
        filtres.append(f"[{cur}]null[{dst}]")
    # round() : overlay TRONQUE sa position (puis la rend paire en yuv420) ; la courbe « back » vaut 2,2e-16 a p = 0,
    # soit 239,9999 au lieu de 240 -> 238 : deux lignes du badge depassaient AVANT son entree (vu sur la preuve)
    x = "round(" + "+".join([bx] + [f"({v})" for v in xs]) + ")" if xs else bx
    y = "round(" + "+".join([by] + [f"({v})" for v in ys]) + ")" if ys else by
    return filtres, x, y


# ----- conversion des blocs `transitions` (tache #76, 03/10/2026) -----

COULEUR = re.compile(r"^#?[0-9A-Fa-f]{6}$")
FLASH_DEFAUT = "#00e5ff"   # le cyan de la marque (le seul des gabarits livres)
ACTES = ("video_slot", "image_slot")   # ce que build_sequential_command enchaine


def convertir_transitions(tpl):
    """Le gabarit SANS bloc `transitions`, converti en ce que le moteur lit (copie ; l'entree n'est pas touchee).
    Spatial : `fade_in` -> animation.in {fade, duration, delay} de la region visee, si elle n'a pas deja une entree.
    Sequentiel : chaque entree -> `transition` {type, duration_s} de l'acte vise, s'il n'en a pas deja une.
    Ce qui vise une region absente, ou un type sans equivalent, est abandonne (personne ne le lisait)."""
    if not isinstance(tpl, dict) or "transitions" not in tpl:
        return tpl
    t = dict(tpl)
    vieux = t.pop("transitions")
    seq = t.get("render_mode") == "sequential"
    regions = [dict(r) if isinstance(r, dict) else r for r in (t.get("regions") or [])]
    par_id: dict = {}
    for r in regions:
        if isinstance(r, dict) and r.get("id"):
            par_id.setdefault(r["id"], r)
    for v in vieux if isinstance(vieux, list) else []:
        if not isinstance(v, dict) or not isinstance(v.get("type"), str):
            continue
        r = par_id.get(v.get("target"))
        if r is None:
            continue
        d, dl = v.get("duration_s"), v.get("delay_s")
        if seq:
            if r.get("type") in ACTES and not r.get("transition"):
                tr = {"type": v["type"]}
                if _n(d) and d > 0:
                    tr["duration_s"] = float(d)
                r["transition"] = tr
        elif v["type"] == "fade_in" and r.get("type") in VISIBLES:
            a = dict(r["animation"]) if isinstance(r.get("animation"), dict) else {}
            if a.get("in"):
                continue
            m = {"type": "fade"}
            if _n(d) and 0.05 <= d <= 10:
                m["duration"] = float(d)
            if _n(dl) and 0 <= dl <= 600:
                m["delay"] = float(dl)
            a["in"] = m
            r["animation"] = a
    t["regions"] = regions
    return t


def verifier_transitions(tpl: dict) -> None:
    """La `transition` d'un acte : un objet dont la couleur (flash) est un hexa #rrggbb — elle entre dans le graphe.
    (La duree n'est pas bornee ici : build_sequential_command la borne deja, et la refuser casserait des graphes du Studio.)"""
    for r in (tpl or {}).get("regions") or []:
        tr = r.get("transition") if isinstance(r, dict) else None
        if tr is None:
            continue
        rid = r.get("id")
        if not isinstance(tr, dict) or not isinstance(tr.get("type", ""), str):
            raise ValueError(f"Region {rid} : transition attend {{\"type\": …, \"duration_s\": …}}.")
        if "color" in tr and not (isinstance(tr["color"], str) and COULEUR.match(tr["color"])):
            raise ValueError(f"Region {rid} : transition.color attend une couleur #rrggbb.")
