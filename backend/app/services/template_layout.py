# -*- coding: utf-8 -*-
"""Plan-templates T2 (tache #73 du suivi, 03/10/2026) — REAGENCER un gabarit dans un autre format (9:16, 16:9, 1:1, 4:5).

Decisions de l'utilisateur (03/10) :
- les grandes CASES (un quart de la toile ou plus, ou bord a bord sur un axe) suivent la nouvelle toile EN PROPORTION —
  la video y est recadree (fit cover), jamais deformee ; les petits ELEMENTS (avatar en coin, logo, badge, textes)
  gardent leurs PROPORTIONS et leur ANCRAGE (debut, centre ou fin selon le tiers ou tombe leur centre) ; une region peut forcer son
  comportement par axe : `constraints: {"h": mode, "v": mode}`, mode parmi debut | centre | fin | etirer | auto ;
- les TEXTES suivent l'echelle de leur region (tailles de police, positions et echelle des elements d'un bandeau) ;
- le resultat est une COPIE enregistree (la galerie « Rejouer en … »), apres un apercu qui AVERTIT — notamment quand un
  avatar HeyGen change de format : ses rendus epingles (#67) seraient regeneres, donc payes.
Le plan etirait chaque axe a part (un avatar 250x250 devenait 444x141) et ne touchait ni polices ni bandeau.
Un gabarit SEQUENTIEL ne change que de toile : ses actes se recadrent deja au format (template_service, cover-scale).
"""
from __future__ import annotations

import copy

#: Les formats de l'app — la MEME table que quick_finish.CANVAS et montage_service._CANVAS (un banc surveille l'ecart).
FORMATS = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080), "4:5": (1080, 1350)}
MODES = ("auto", "debut", "centre", "fin", "etirer")
SEUIL_CASE = 0.25                  # part de la toile au-dela de laquelle une region est une case
BORD = 0.02                        # a moins de 2 % de deux bords opposes, une region est bord a bord (une case)
#: Taille de police implicite des types qui ecrivent du texte (template_service : text_slot 48, badge 34, ticker 40).
TAILLE_DEFAUT = {"text": 48, "text_slot": 48, "badge": 34, "ticker": 40}   # « text » : 48 aussi (oubli corrige, #74)


def format_de(tpl: dict) -> str | None:
    c = (tpl or {}).get("canvas") or {}
    try:
        w, h = int(c.get("width")), int(c.get("height"))
    except (TypeError, ValueError):
        return None
    for f, (fw, fh) in FORMATS.items():
        if (fw, fh) == (w, h):
            return f
    return None


def verifier_contraintes(regions) -> None:
    """ValueError qui nomme la region et le mode inventes (appele par TemplateEngine._validate)."""
    for r in regions or []:
        c = r.get("constraints")
        if c is None:
            continue
        if not isinstance(c, dict) or set(c) - {"h", "v"}:
            raise ValueError(f"Region {r.get('id')} : « constraints » attend {{\"h\": mode, \"v\": mode}}.")
        for ax, m in c.items():
            if m not in MODES:
                raise ValueError(f"Region {r.get('id')} : contrainte {ax}={m!r} inconnue — {', '.join(MODES)}.")


def _mode_auto(p0: float, l0: float, L0: float) -> str:
    """L'ancrage d'un element : par TIERS de son centre (un avatar a 40 px du coin est « dans le coin » ; une marge
    fixe en pourcentage le ratait — trouve par le banc)."""
    c = (p0 + l0 / 2) / L0
    if c < 1 / 3:
        return "debut"
    if c > 2 / 3:
        return "fin"
    return "centre"


def _axe(p0, l0, L0, L1, s, mode):
    """(position, longueur) sur un axe. `etirer` : proportion de la toile ; sinon longueur a l'echelle s, ancree."""
    if mode == "etirer":
        k = L1 / L0
        p1, l1 = round(p0 * k), round(l0 * k)
    else:
        if mode == "auto":
            mode = _mode_auto(p0, l0, L0)
        l1 = round(l0 * s)
        if mode == "debut":
            p1 = round(p0 * s)
        elif mode == "fin":
            p1 = L1 - round((L0 - p0 - l0) * s) - l1
        else:
            p1 = round((p0 + l0 / 2) / L0 * L1 - l1 / 2)
    # Pas de bornage : pour un gabarit VALIDE, l'arrondi ne deborde jamais de la toile (mesure 03/10 sur toutes les
    # positions et les douze paires de formats) et s >= 0.5625 garde toute longueur >= 1 — un garde-fou serait du code mort.
    return p1, l1


def _est_case(r, W0, H0) -> bool:
    x, y, w, h = (float(r.get(k) or 0) for k in ("x", "y", "width", "height"))
    pleine_l = x <= W0 * BORD and x + w >= W0 * (1 - BORD)
    pleine_h = y <= H0 * BORD and y + h >= H0 * (1 - BORD)
    return w * h >= SEUIL_CASE * W0 * H0 or pleine_l or pleine_h


def _echelle_textes(r: dict, k: float) -> None:
    if isinstance(r.get("size"), (int, float)):
        r["size"] = max(8, round(r["size"] * k))
    elif r.get("type") in TAILLE_DEFAUT:
        r["size"] = max(8, round(TAILLE_DEFAUT[r["type"]] * k))
    if isinstance(r.get("radius"), (int, float)):
        r["radius"] = max(0, round(r["radius"] * k))
    if isinstance(r.get("text_min_size"), (int, float)):   # tâche #74 : la taille mini et les effets de texte suivent aussi
        r["text_min_size"] = max(6, round(r["text_min_size"] * k))
    tc = r.get("text_curve")   # tâche #76 : le rayon de l'arc suit l'échelle, comme la taille du texte
    if isinstance(tc, dict) and isinstance(tc.get("radius"), (int, float)):
        tc["radius"] = max(20, round(tc["radius"] * k, 2))
    fx = r.get("text_effects")
    if isinstance(fx, dict):
        for nom, champs in (("stroke", ("px",)), ("shadow", ("dx", "dy", "blur")), ("box", ("radius", "pad"))):
            sous = fx.get(nom)
            if isinstance(sous, dict):
                for c in champs:
                    if isinstance(sous.get(c), (int, float)):
                        sous[c] = round(sous[c] * k, 2)
    m = r.get("mask")
    if isinstance(m, dict):   # tâche #74 : les épaisseurs du masque suivent l'échelle ; fenêtres et points sont des fractions
        for c in ("radius", "feather_px", "border_px"):
            if isinstance(m.get(c), (int, float)):
                m[c] = round(m[c] * k, 2)
        for t in m.get("holes") or []:
            if isinstance(t, dict) and isinstance(t.get("radius"), (int, float)):
                t["radius"] = round(t["radius"] * k, 2)
    for it in r.get("items") or []:
        if not isinstance(it, dict):
            continue
        for c in ("x", "y"):
            if isinstance(it.get(c), (int, float)):
                it[c] = round(it[c] * k)
        if isinstance(it.get("size"), (int, float)):
            it["size"] = max(8, round(it["size"] * k))
        if isinstance(it.get("scale"), (int, float)):
            it["scale"] = round(it["scale"] * k, 4)


def reflow(tpl: dict, fmt: str) -> tuple:
    """(gabarit reagence, avertissements). Ne modifie pas `tpl`. ValueError : format inconnu, toile illisible."""
    if fmt not in FORMATS:
        raise ValueError(f"Format inconnu : {fmt} — {', '.join(FORMATS)}.")
    out = copy.deepcopy(tpl)
    out.pop("_builtin", None)
    c = out.get("canvas") or {}
    try:
        W0, H0 = float(c["width"]), float(c["height"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("Toile illisible (canvas.width / canvas.height).")
    if W0 <= 0 or H0 <= 0:
        raise ValueError("Toile illisible (dimensions nulles).")
    W1, H1 = FORMATS[fmt]
    verifier_contraintes(out.get("regions"))
    c["width"], c["height"] = W1, H1
    out["canvas"] = c
    out.setdefault("metadata", {})
    if isinstance(out["metadata"], dict):
        out["metadata"]["format"] = fmt
    avert = []
    if out.get("render_mode") in ("sequential", "montage"):
        avert.append("Gabarit séquentiel : ses actes se recadrent déjà au format ; seule la toile change.")
        return out, avert
    s = min(W1 / W0, H1 / H0)
    for r in out.get("regions") or []:
        if not all(isinstance(r.get(k), (int, float)) for k in ("x", "y", "width", "height")):
            continue                   # une piste audio (ou toute region sans geometrie) n'est pas placee
        cons = r.get("constraints") or {}
        case = _est_case(r, W0, H0)
        mh = cons.get("h") or ("etirer" if case else "auto")
        mv = cons.get("v") or ("etirer" if case else "auto")
        x, w = _axe(float(r["x"]), float(r["width"]), W0, W1, s, mh)
        y, h = _axe(float(r["y"]), float(r["height"]), H0, H1, s, mv)
        r["x"], r["y"], r["width"], r["height"] = x, y, w, h
        _echelle_textes(r, s)          # s = min des deux rapports : le texte tient dans toute region, etiree ou non
    return out, avert


def avertissements_heygen(avant: dict, apres: dict) -> list:
    """Les avatars HeyGen dont le FORMAT de generation change : leurs rendus epingles ne vaudront plus (payes a nouveau)."""
    from app.services.pipeline import _heygen_aspect_for_slot
    out = []
    for r in avant.get("regions") or []:
        if r.get("type") != "video_slot" or r.get("default_provider") != "heygen" or not r.get("slot_name"):
            continue
        a, b = _heygen_aspect_for_slot(avant, r["slot_name"]), _heygen_aspect_for_slot(apres, r["slot_name"])
        if a and b and a != b:
            out.append(f"L'avatar « {r.get('slot_label') or r['slot_name']} » passe de {a} à {b} : "
                       "ses rendus épinglés seront régénérés (payants) au prochain rendu de ce gabarit.")
    return out
