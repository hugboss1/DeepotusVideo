#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mesure_style.py - mesureur de style visuel (PIL pur, zero dependance externe).

Reduit une image a un jeu de nombres reproductibles : palette dominante,
distribution tonale, saturation, accent chromatique, geometrie de composition.
Sert deux fois dans la boucle :

  1) en amont, sur un corpus de references, pour FABRIQUER une fiche de style ;
  2) en aval, sur une image GENEREE, pour JUGER si elle tient dans les bornes.

Usage
-----
  # mesurer un corpus et ecrire la fiche agregee
  python mesure_style.py --corpus refs/ --json fiche_style.json

  # mesurer une seule image
  python mesure_style.py --une image.png

  # juger une image generee contre une fiche
  python mesure_style.py --verifier sortie.png --fiche fiche_style.json

Options
-------
  --inset F      rogne F (fraction, ex. 0.06) sur chaque bord avant mesure.
                 Utile pour retirer la bande de titre d'une affiche.
  --palette N    nombre de couleurs dominantes par image (defaut 8).
  --clusters N   nombre de teintes maitres dans la palette fusionnee (defaut 9).
  --quiet        n'ecrit que le JSON, pas de tableau.

Conventions de mesure (a citer telles quelles dans toute fiche produite)
-----------------------------------------------------------------------
  L      = clarte CIE L* (D65, sRGB) remise a l'echelle 0..255  (L* x 2.55)
  C      = chroma CIE LCh, C* = sqrt(a*^2 + b*^2), unites LAB natives
  h      = teinte CIE LCh en degres, atan2(b*, a*), 0 = axe rouge-magenta
  S      = saturation HSV 0..255 (PIL)
  sombre = part de la masse de pixels a L < 64      (soit L* < 25.1)
  clair  = part de la masse de pixels a L > 200     (soit L* > 78.4)
  gris   = part de la masse de pixels a C < 10
  E      = energie de contraste local = |L - flou_gaussien(L, r)|, r = 1.5% du petit cote
  vide   = part de pixels a E < 4 (contraste local sous ~1.6% de l'echelle L)
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from statistics import median

try:
    from PIL import Image, ImageFilter
except ImportError:  # pragma: no cover
    sys.stderr.write("PIL/Pillow est requis. pip install Pillow\n")
    raise

EXTS = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff")

TAILLE_PALETTE = 256   # petit cote de la vignette servant a la quantification
TAILLE_COMPO = 384     # plus grand cote de l'image servant a la geometrie
SEUIL_SOMBRE = 64      # L
SEUIL_CLAIR = 200      # L
SEUIL_GRIS = 10.0      # C*
SEUIL_VIDE = 4.0       # E
MASSE_CENTRALE = 0.80  # part d'energie enfermee dans la bbox de masse principale


# --------------------------------------------------------------------------
# colorimetrie (sRGB <-> CIE L*a*b*, D65) -- pas de dependance, LUT memoisee
# --------------------------------------------------------------------------

_LIN = [((c / 255.0 / 12.92) if (c / 255.0) <= 0.04045
         else (((c / 255.0) + 0.055) / 1.055) ** 2.4) for c in range(256)]
_XN, _YN, _ZN = 0.95047, 1.00000, 1.08883
_cache_lab: dict[tuple[int, int, int], tuple[float, float, float]] = {}


def _f(t: float) -> float:
    return t ** (1.0 / 3.0) if t > 0.008856451679035631 else (7.787037037037035 * t + 16.0 / 116.0)


def rgb_vers_lab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    """sRGB 0..255 -> (L*, a*, b*). Memoise : un corpus n'a que ~10^4 teintes uniques."""
    hit = _cache_lab.get(rgb)
    if hit is not None:
        return hit
    r, g, b = _LIN[rgb[0]], _LIN[rgb[1]], _LIN[rgb[2]]
    x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / _XN
    y = (0.2126729 * r + 0.7151522 * g + 0.0721750 * b) / _YN
    z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / _ZN
    fx, fy, fz = _f(x), _f(y), _f(z)
    out = (116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz))
    _cache_lab[rgb] = out
    return out


def lab_vers_rgb(lab: tuple[float, float, float]) -> tuple[int, int, int]:
    L, a, b = lab
    fy = (L + 16.0) / 116.0
    fx = fy + a / 500.0
    fz = fy - b / 200.0

    def inv(t: float) -> float:
        t3 = t ** 3
        return t3 if t3 > 0.008856451679035631 else (t - 16.0 / 116.0) / 7.787037037037035

    x, y, z = inv(fx) * _XN, inv(fy) * _YN, inv(fz) * _ZN
    r = 3.2404542 * x - 1.5371385 * y - 0.4985314 * z
    g = -0.9692660 * x + 1.8760108 * y + 0.0415560 * z
    bb = 0.0556434 * x - 0.2040259 * y + 1.0572252 * z
    out = []
    for c in (r, g, bb):
        c = 12.92 * c if c <= 0.0031308 else 1.055 * (max(c, 0.0) ** (1 / 2.4)) - 0.055
        out.append(max(0, min(255, int(round(c * 255.0)))))
    return tuple(out)  # type: ignore[return-value]


def hexa(rgb: tuple[int, int, int]) -> str:
    return "#%02X%02X%02X" % rgb


def de_hexa(s: str) -> tuple[int, int, int]:
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def chroma_teinte(lab: tuple[float, float, float]) -> tuple[float, float]:
    _, a, b = lab
    c = math.hypot(a, b)
    h = math.degrees(math.atan2(b, a)) % 360.0
    return c, h


def nom_de_teinte(h: float, c: float, L: float) -> str:
    """Etiquette lisible, purement descriptive -- aide la lecture du tableau."""
    if c < SEUIL_GRIS:
        if L < 20:
            return "noir"
        if L < 45:
            return "gris sombre"
        if L < 70:
            return "gris moyen"
        return "gris clair"
    bandes = [
        (15, "rouge"), (45, "rouge-orange"), (70, "ocre-orange"), (95, "ocre-jaune"),
        (150, "vert"), (200, "vert-bleu"), (250, "bleu"), (300, "violet"),
        (345, "magenta"), (360, "rouge"),
    ]
    for borne, nom in bandes:
        if h < borne:
            return nom
    return "rouge"


# --------------------------------------------------------------------------
# helpers histogramme pondere
# --------------------------------------------------------------------------

def _percentile_pondere(paires: list[tuple[float, float]], p: float) -> float:
    """paires = [(valeur, poids)] non triees. p dans [0,1]."""
    if not paires:
        return 0.0
    paires = sorted(paires, key=lambda t: t[0])
    total = sum(w for _, w in paires)
    if total <= 0:
        return 0.0
    cible = p * total
    cum = 0.0
    for v, w in paires:
        cum += w
        if cum >= cible:
            return v
    return paires[-1][0]


def _rogne(im: Image.Image, inset: float) -> Image.Image:
    if inset <= 0:
        return im
    w, h = im.size
    dx, dy = int(w * inset), int(h * inset)
    if w - 2 * dx < 16 or h - 2 * dy < 16:
        return im
    return im.crop((dx, dy, w - dx, h - dy))


# --------------------------------------------------------------------------
# fond chromatique / accent isole
# --------------------------------------------------------------------------

N_BANDES = 36          # bandes de teinte de 10 degres
C_COLOREE = 15.0       # au-dela : le pixel a une teinte, en deca c'est du gris
C_ACCENT_MIN = 22.0    # un accent doit etre franchement colore
ECART_ACCENT = 40.0    # degres minimum entre l'accent et la teinte du fond
PART_ACCENT_MIN = 0.004  # 0,4 % de la toile : un accent, pas un grain de bruit


def _dist_teinte(a: float, b: float) -> float:
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


def _fond_et_accent(couleurs: list, n_pix: int) -> tuple[dict | None, dict | None]:
    """Separe le champ dominant de l'accent minoritaire.

    Le fond = la bande de teinte qui porte le plus de masse coloree.
    L'accent = la bande la plus chargee en chroma parmi celles qui sont
    a plus de ECART_ACCENT degres du fond -- c'est ce que veut dire << isole >>.
    Sans bande candidate, l'image est declaree monochrome : c'est un resultat,
    pas un echec.
    """
    masse = [0.0] * N_BANDES
    somme_c = [0.0] * N_BANDES
    pixels: list[list[tuple[float, tuple[float, float, float], float]]] = [
        [] for _ in range(N_BANDES)]
    masse_coloree = 0.0
    for cnt, rgb in couleurs:
        lab = rgb_vers_lab(rgb)
        c, h = chroma_teinte(lab)
        if c < C_COLOREE:
            continue
        i = int(h // 10.0) % N_BANDES
        masse[i] += cnt
        somme_c[i] += c * cnt
        pixels[i].append((c, lab, float(cnt)))
        masse_coloree += cnt

    if masse_coloree / n_pix < 0.02:  # moins de 2 % de toile coloree
        return ({"monochrome": True, "part_coloree": round(masse_coloree / n_pix, 4)}, None)

    # lissage circulaire : une teinte a cheval sur deux bandes ne doit pas se scinder
    lisse = [masse[(i - 1) % N_BANDES] + masse[i] + masse[(i + 1) % N_BANDES]
             for i in range(N_BANDES)]
    i_fond = max(range(N_BANDES), key=lambda i: lisse[i])
    h_fond = i_fond * 10.0 + 5.0

    def _representant(bandes_idx: list[int]) -> tuple[str, float, float, float, float]:
        """Centroide LAB de la moitie la plus chromatique des pixels retenus."""
        pool = [p for i in bandes_idx for p in pixels[i]]
        if not pool:
            return ("#000000", 0.0, 0.0, 0.0, 0.0)
        pool.sort(key=lambda t: -t[0])
        cible = sum(p[2] for p in pool) * 0.5
        cum, garde = 0.0, []
        for p in pool:
            garde.append(p)
            cum += p[2]
            if cum >= cible:
                break
        tw = sum(p[2] for p in garde) or 1.0
        L = sum(p[1][0] * p[2] for p in garde) / tw
        a = sum(p[1][1] * p[2] for p in garde) / tw
        b = sum(p[1][2] * p[2] for p in garde) / tw
        c, h = chroma_teinte((L, a, b))
        return (hexa(lab_vers_rgb((L, a, b))), c, h, L, tw)

    v_fond = [(i_fond - 1) % N_BANDES, i_fond, (i_fond + 1) % N_BANDES]
    hexf, cf_, hf_, Lf_, _ = _representant(v_fond)
    fond = {
        "monochrome": False,
        "hex": hexf,
        "h": round(hf_, 1),
        "C": round(cf_, 1),
        "L": round(Lf_ * 2.55, 1),
        "nom": nom_de_teinte(hf_, cf_, Lf_),
        "part_de_surface": round(lisse[i_fond] / n_pix, 4),
        "part_coloree_totale": round(masse_coloree / n_pix, 4),
    }

    candidats = []
    for i in range(N_BANDES):
        if _dist_teinte(i * 10.0 + 5.0, h_fond) < ECART_ACCENT:
            continue
        part = lisse[i] / n_pix
        if part < PART_ACCENT_MIN or masse[i] <= 0:
            continue
        c_moy = somme_c[i] / masse[i]
        if c_moy < C_ACCENT_MIN:
            continue
        candidats.append((c_moy, i, part))

    if not candidats:
        return (fond, None)

    _, i_acc, part_acc = max(candidats, key=lambda t: t[0])
    v_acc = [(i_acc - 1) % N_BANDES, i_acc, (i_acc + 1) % N_BANDES]
    hexa_, ca_, ha_, La_, _ = _representant(v_acc)
    # noyau chaud : la part de toile a la fois dans la teinte et franchement saturee
    noyau = sum(p[2] for i in v_acc for p in pixels[i] if p[0] >= 30.0)
    accent = {
        "hex": hexa_,
        "h": round(ha_, 1),
        "C": round(ca_, 1),
        "L": round(La_ * 2.55, 1),
        "nom": nom_de_teinte(ha_, ca_, La_),
        "part_de_surface": round(part_acc, 4),
        "part_noyau_C30": round(noyau / n_pix, 4),
        "ecart_teinte_au_fond": round(_dist_teinte(ha_, hf_), 1),
    }
    return (fond, accent)


# --------------------------------------------------------------------------
# mesure d'une image
# --------------------------------------------------------------------------

def mesurer(chemin: str, inset: float = 0.0, n_palette: int = 8) -> dict:
    im0 = Image.open(chemin)
    im0.draft("RGB", im0.size)  # decodage JPEG accelere si dispo
    im = im0.convert("RGB")
    largeur_src, hauteur_src = im.size
    im = _rogne(im, inset)
    w_src, h_src = im.size

    res: dict = {
        "fichier": os.path.basename(chemin),
        "px_source": [largeur_src, hauteur_src],
        "inset": inset,
        "format": {
            "largeur": w_src,
            "hauteur": h_src,
            "ratio_l_sur_h": round(w_src / h_src, 4),
            "portrait": bool(h_src > w_src),
        },
    }

    # ---- vignette de couleur -------------------------------------------------
    vig = im.copy()
    vig.thumbnail((TAILLE_PALETTE, TAILLE_PALETTE), Image.LANCZOS)
    n_pix = vig.size[0] * vig.size[1]

    # couleurs uniques + comptes : tout le reste se calcule dessus (rapide)
    couleurs = vig.getcolors(maxcolors=n_pix) or []
    if not couleurs:
        couleurs = [(n_pix, (0, 0, 0))]

    # ---- palette dominante par quantification median-cut ---------------------
    meth = getattr(Image, "Quantize", None)
    mc = meth.MEDIANCUT if meth is not None else 0
    q = vig.quantize(colors=n_palette, method=mc, dither=Image.Dither.NONE)
    pal = q.getpalette() or []
    comptes = sorted(q.getcolors(maxcolors=n_palette * 4) or [], key=lambda t: -t[0])
    palette = []
    for cnt, idx in comptes[:n_palette]:
        rgb = (pal[idx * 3], pal[idx * 3 + 1], pal[idx * 3 + 2])
        lab = rgb_vers_lab(rgb)
        c, h = chroma_teinte(lab)
        palette.append({
            "hex": hexa(rgb),
            "part": round(cnt / n_pix, 4),
            "L": round(lab[0], 1),
            "C": round(c, 1),
            "h": round(h, 1),
            "nom": nom_de_teinte(h, c, lab[0]),
        })
    res["palette"] = palette

    # ---- tons, saturation, gris ----------------------------------------------
    L_pond: list[tuple[float, float]] = []
    C_pond: list[tuple[float, float]] = []
    masse_sombre = masse_claire = masse_gris = 0.0
    for cnt, rgb in couleurs:
        lab = rgb_vers_lab(rgb)
        L255 = lab[0] * 2.55
        c, _ = chroma_teinte(lab)
        L_pond.append((L255, cnt))
        C_pond.append((c, cnt))
        if L255 < SEUIL_SOMBRE:
            masse_sombre += cnt
        if L255 > SEUIL_CLAIR:
            masse_claire += cnt
        if c < SEUIL_GRIS:
            masse_gris += cnt

    p05 = _percentile_pondere(L_pond, 0.05)
    p50 = _percentile_pondere(L_pond, 0.50)
    p95 = _percentile_pondere(L_pond, 0.95)
    res["tons"] = {
        "L_p05": round(p05, 1),
        "L_p50": round(p50, 1),
        "L_p95": round(p95, 1),
        "etendue_p05_p95": round(p95 - p05, 1),
        "part_sombre_L_moins_64": round(masse_sombre / n_pix, 4),
        "part_claire_L_plus_200": round(masse_claire / n_pix, 4),
    }

    # saturation HSV en parallele de la chroma LAB
    hsv = vig.convert("HSV")
    canal_s = hsv.getchannel("S")
    hist_s = canal_s.histogram()
    s_pond = [(float(v), float(n)) for v, n in enumerate(hist_s) if n]
    res["saturation"] = {
        "S_hsv_p50": round(_percentile_pondere(s_pond, 0.50), 1),
        "S_hsv_p95": round(_percentile_pondere(s_pond, 0.95), 1),
        "C_lab_p50": round(_percentile_pondere(C_pond, 0.50), 1),
        "C_lab_p95": round(_percentile_pondere(C_pond, 0.95), 1),
        "part_quasi_gris_C_moins_10": round(masse_gris / n_pix, 4),
    }

    # ---- fond chromatique et accent isole ------------------------------------
    # NE PAS passer par la quantification : median-cut depense tous ses tiroirs
    # sur le champ dominant, si bien qu'un accent a 2 % de surface n'obtient
    # jamais d'entree. On travaille sur l'histogramme de teinte pleine fidelite.
    res["fond"], res["accent"] = _fond_et_accent(couleurs, n_pix)

    # ---- composition ---------------------------------------------------------
    gris = im.convert("L")
    gris.thumbnail((TAILLE_COMPO, TAILLE_COMPO), Image.LANCZOS)
    gw, gh = gris.size
    rayon = max(1.0, 0.015 * min(gw, gh))
    flou = gris.filter(ImageFilter.GaussianBlur(radius=rayon))
    # getdata() disparait dans Pillow 14 (10/2027) ; get_flattened_data() n'existe
    # pas avant Pillow 11. On prend celui qui est la.
    def _plat(img: Image.Image) -> list:
        f = getattr(img, "get_flattened_data", None)
        return list(f()) if f is not None else list(img.getdata())

    px_g = _plat(gris)
    px_f = _plat(flou)
    E = [abs(a - b) for a, b in zip(px_g, px_f)]

    total_E = float(sum(E)) or 1.0
    prof_x = [0.0] * gw
    prof_y = [0.0] * gh
    tiers = [[0.0] * 3 for _ in range(3)]
    n_vide = 0
    sx = sy = 0.0
    i = 0
    for y in range(gh):
        ty = min(2, (y * 3) // gh)
        ligne = tiers[ty]
        for x in range(gw):
            e = E[i]
            i += 1
            if e < SEUIL_VIDE:
                n_vide += 1
                continue
            prof_x[x] += e
            prof_y[y] += e
            sx += e * x
            sy += e * y
            ligne[min(2, (x * 3) // gw)] += e

    def _intervalle(prof: list[float], part: float) -> tuple[float, float]:
        tot = sum(prof) or 1.0
        marge = (1.0 - part) / 2.0
        cum = 0.0
        lo = hi = 0
        seuil_lo, seuil_hi = marge * tot, (1.0 - marge) * tot
        vu_lo = False
        for k, v in enumerate(prof):
            cum += v
            if not vu_lo and cum >= seuil_lo:
                lo, vu_lo = k, True
            if cum >= seuil_hi:
                hi = k
                break
        else:
            hi = len(prof) - 1
        return lo / len(prof), (hi + 1) / len(prof)

    x0, x1 = _intervalle(prof_x, MASSE_CENTRALE)
    y0, y1 = _intervalle(prof_y, MASSE_CENTRALE)
    somme_tiers = sum(sum(r) for r in tiers) or 1.0

    res["composition"] = {
        "centroide_x": round(sx / total_E / gw, 4),
        "centroide_y": round(sy / total_E / gh, 4),
        "masse_bbox": {
            "x0": round(x0, 4), "x1": round(x1, 4),
            "y0": round(y0, 4), "y1": round(y1, 4),
            "part_surface": round((x1 - x0) * (y1 - y0), 4),
            "centre_y": round((y0 + y1) / 2.0, 4),
            "largeur": round(x1 - x0, 4),
            "hauteur": round(y1 - y0, 4),
        },
        "part_vide_E_moins_4": round(n_vide / (gw * gh), 4),
        "energie_moyenne": round(total_E / (gw * gh), 2),
        "tiers": [[round(v / somme_tiers, 4) for v in r] for r in tiers],
        "part_bande_centrale": round(sum(tiers[k][1] for k in range(3)) / somme_tiers, 4),
        "part_rangee_haute": round(sum(tiers[0]) / somme_tiers, 4),
        "part_rangee_basse": round(sum(tiers[2]) / somme_tiers, 4),
    }
    return res


# --------------------------------------------------------------------------
# agregation d'un corpus
# --------------------------------------------------------------------------

def _stats(vals: list[float]) -> dict:
    vals = sorted(v for v in vals if v is not None)
    if not vals:
        return {}
    n = len(vals)

    def pc(p: float) -> float:
        if n == 1:
            return vals[0]
        k = p * (n - 1)
        lo, hi = int(math.floor(k)), int(math.ceil(k))
        return vals[lo] + (vals[hi] - vals[lo]) * (k - lo)

    return {
        "med": round(median(vals), 4),
        "min": round(vals[0], 4),
        "max": round(vals[-1], 4),
        "p10": round(pc(0.10), 4),
        "p25": round(pc(0.25), 4),
        "p75": round(pc(0.75), 4),
        "p90": round(pc(0.90), 4),
        "n": n,
    }


def _kmeans_lab(points: list[tuple[tuple[float, float, float], float]], k: int,
                iters: int = 60) -> list[tuple[tuple[float, float, float], float, int]]:
    """k-means pondere en LAB. points = [(lab, poids)]. Semis deterministe k-means++."""
    if not points:
        return []
    k = min(k, len(points))
    # semis : le point le plus lourd, puis le plus eloigne des centres deja pris
    centres = [max(points, key=lambda p: p[1])[0]]
    while len(centres) < k:
        best, bd = None, -1.0
        for lab, _w in points:
            d = min(sum((lab[i] - c[i]) ** 2 for i in range(3)) for c in centres)
            if d > bd:
                bd, best = d, lab
        centres.append(best)  # type: ignore[arg-type]

    aff = [0] * len(points)
    for _ in range(iters):
        change = False
        for i, (lab, _w) in enumerate(points):
            j = min(range(k), key=lambda c: sum((lab[d] - centres[c][d]) ** 2 for d in range(3)))
            if j != aff[i]:
                aff[i] = j
                change = True
        for c in range(k):
            membres = [(lab, w) for i, (lab, w) in enumerate(points) if aff[i] == c]
            if not membres:
                continue
            tw = sum(w for _, w in membres) or 1.0
            centres[c] = tuple(sum(lab[d] * w for lab, w in membres) / tw for d in range(3))  # type: ignore
        if not change:
            break

    sorties = []
    for c in range(k):
        idx = [i for i in range(len(points)) if aff[i] == c]
        if not idx:
            continue
        sorties.append((centres[c], sum(points[i][1] for i in idx), len(idx)))
    return sorties


def agreger(mesures: list[dict], n_clusters: int = 9) -> dict:
    n = len(mesures)
    if n == 0:
        return {}

    def col(chemin: str) -> list[float]:
        out = []
        for m in mesures:
            cur = m
            ok = True
            for cle in chemin.split("."):
                if isinstance(cur, dict) and cle in cur and cur[cle] is not None:
                    cur = cur[cle]
                else:
                    ok = False
                    break
            if ok and isinstance(cur, (int, float)):
                out.append(float(cur))
        return out

    champs = [
        "format.ratio_l_sur_h",
        "tons.L_p05", "tons.L_p50", "tons.L_p95", "tons.etendue_p05_p95",
        "tons.part_sombre_L_moins_64", "tons.part_claire_L_plus_200",
        "saturation.S_hsv_p50", "saturation.S_hsv_p95",
        "saturation.C_lab_p50", "saturation.C_lab_p95",
        "saturation.part_quasi_gris_C_moins_10",
        "fond.h", "fond.C", "fond.L", "fond.part_de_surface", "fond.part_coloree_totale",
        "accent.h", "accent.C", "accent.L",
        "accent.part_de_surface", "accent.part_noyau_C30", "accent.ecart_teinte_au_fond",
        "composition.centroide_x", "composition.centroide_y",
        "composition.masse_bbox.part_surface", "composition.masse_bbox.centre_y",
        "composition.masse_bbox.largeur", "composition.masse_bbox.hauteur",
        "composition.part_vide_E_moins_4", "composition.energie_moyenne",
        "composition.part_bande_centrale", "composition.part_rangee_haute",
        "composition.part_rangee_basse",
    ]
    agg = {c: _stats(col(c)) for c in champs}

    # grille des tiers : mediane cellule par cellule
    grille = []
    for r in range(3):
        ligne = []
        for c in range(3):
            vals = [m["composition"]["tiers"][r][c] for m in mesures
                    if m.get("composition", {}).get("tiers")]
            ligne.append(round(median(vals), 4) if vals else 0.0)
        grille.append(ligne)

    # palette fusionnee : toutes les dominantes de toutes les oeuvres, clusterisees
    pts = []
    for m in mesures:
        for e in m.get("palette", []):
            pts.append((rgb_vers_lab(de_hexa(e["hex"])), float(e["part"])))
    clusters = _kmeans_lab(pts, n_clusters)
    clusters.sort(key=lambda t: -t[1])
    palette_maitre = []
    total_part = sum(t[1] for t in clusters) or 1.0
    for lab, poids, membres in clusters:
        rgb = lab_vers_rgb(lab)
        c, h = chroma_teinte(lab)
        palette_maitre.append({
            "hex": hexa(rgb),
            "part_moyenne": round(poids / n, 4),           # part de toile moyenne par oeuvre
            "part_relative": round(poids / total_part, 4),  # part du budget palette
            "L": round(lab[0], 1), "C": round(c, 1), "h": round(h, 1),
            "nom": nom_de_teinte(h, c, lab[0]),
            "n_dominantes": membres,
        })

    # le format est bimodal (affiche portrait B1 vs affiche paysage) : une mediane
    # unique mentirait, on separe les deux modes.
    port = [m["format"]["ratio_l_sur_h"] for m in mesures if m["format"]["portrait"]]
    pays = [m["format"]["ratio_l_sur_h"] for m in mesures if not m["format"]["portrait"]]
    formats = {
        "portrait": {"n": len(port), "ratio_med": round(median(port), 4) if port else None,
                     "ratio_min": round(min(port), 4) if port else None,
                     "ratio_max": round(max(port), 4) if port else None},
        "paysage": {"n": len(pays), "ratio_med": round(median(pays), 4) if pays else None,
                    "ratio_min": round(min(pays), 4) if pays else None,
                    "ratio_max": round(max(pays), 4) if pays else None},
    }
    n_mono = sum(1 for m in mesures if (m.get("fond") or {}).get("monochrome"))
    n_sans_accent = sum(1 for m in mesures if m.get("accent") is None)

    return {
        "n_oeuvres": n,
        "oeuvres": [m["fichier"] for m in mesures],
        "formats": formats,
        "n_monochromes": n_mono,
        "n_sans_accent_isole": n_sans_accent,
        "metriques": agg,
        "tiers_median": grille,
        "palette_maitre": palette_maitre,
        "conventions": {
            "L": "CIE L* (D65) remis a l'echelle 0..255",
            "C": "chroma CIE LCh (unites LAB)",
            "h": "teinte CIE LCh en degres",
            "S": "saturation HSV 0..255",
            "E": "|L - flou_gaussien(L, r=1.5% du petit cote)|",
            "seuils": {"sombre": "L<64", "clair": "L>200", "gris": "C<10", "vide": "E<4"},
            "bbox_masse": "intervalle contenant 80% de l'energie sur chaque axe",
        },
    }


# --------------------------------------------------------------------------
# verification d'une image generee contre une fiche
# --------------------------------------------------------------------------

# (cle, libelle, critique)
# << critique >> = l'axe sur lequel un generateur d'images derape par defaut.
# Un seul HORS sur un axe critique suffit a refuser l'image : ce sont eux qui
# separent une peinture sourde d'une illustration de fantasy generique.
CONTROLES = [
    ("tons.part_sombre_L_moins_64", "part sombre (L<64)", False),
    ("tons.part_claire_L_plus_200", "part claire (L>200)", True),
    ("tons.L_p50", "L median", True),
    ("tons.L_p95", "L p95", False),
    ("tons.etendue_p05_p95", "etendue tonale", False),
    ("saturation.C_lab_p50", "chroma mediane", True),
    ("saturation.C_lab_p95", "chroma p95", True),
    ("saturation.part_quasi_gris_C_moins_10", "part quasi-grise", True),
    ("fond.part_de_surface", "surface de la teinte dominante", False),
    ("accent.part_de_surface", "surface de l'accent", False),
    ("accent.part_noyau_C30", "noyau sature de l'accent", False),
    ("composition.centroide_y", "centroide vertical", False),
    ("composition.masse_bbox.part_surface", "surface de la masse", False),
    ("composition.masse_bbox.centre_y", "centre vertical de la masse", False),
    ("composition.part_vide_E_moins_4", "part de vide", True),
    ("composition.part_bande_centrale", "energie colonne centrale", False),
]

POIDS = {"DANS": 1.0, "LARGE": 0.5, "HORS": 0.0}


def _lire(d: dict, chemin: str):
    cur = d
    for cle in chemin.split("."):
        if not isinstance(cur, dict) or cle not in cur or cur[cle] is None:
            return None
        cur = cur[cle]
    return cur


def verifier(m: dict, fiche: dict) -> dict:
    """Juge une image contre les bornes d'une fiche.

    Bande verte  = [p10, p90] du corpus : 80 % des references y tombent par
                   construction, donc une oeuvre du style doit y tomber aussi.
    Bande jaune  = [min, max] : plausible mais en bord de corpus.
    Rouge        = hors de tout ce que le corpus a montre.

    p25-p75 serait un piege : c'est une bande a 50 %, une reference authentique
    en sort une fois sur deux et le juge la refuserait a tort.
    """
    mets = fiche.get("metriques", {})
    lignes = []
    points = 0.0
    total = 0
    hors_critiques = []
    for chemin, libelle, critique in CONTROLES:
        st = mets.get(chemin)
        v = _lire(m, chemin)
        if not st or v is None:
            continue
        total += 1
        lo, hi = st.get("p10", st["min"]), st.get("p90", st["max"])
        vlo, vhi = st["min"], st["max"]
        if lo <= v <= hi:
            etat, ecart = "DANS", 0.0
        elif vlo <= v <= vhi:
            etat = "LARGE"
            ecart = (lo - v) if v < lo else (v - hi)
        else:
            etat = "HORS"
            ecart = (vlo - v) if v < vlo else (v - vhi)
        points += POIDS[etat]
        if etat == "HORS" and critique:
            hors_critiques.append(libelle)
        lignes.append({
            "metrique": libelle, "cle": chemin, "valeur": round(v, 4),
            "critique": critique,
            "p10_p90": [lo, hi], "min_max": [vlo, vhi],
            "etat": etat, "ecart": round(ecart, 4),
        })

    # distance de palette : chaque teinte maitre trouve-t-elle un echo ?
    maitres = fiche.get("palette_maitre", [])
    mienne = [(rgb_vers_lab(de_hexa(e["hex"])), e["part"]) for e in m.get("palette", [])]
    echos = []
    for mt in maitres:
        lab = rgb_vers_lab(de_hexa(mt["hex"]))
        if mienne:
            d = min(math.sqrt(sum((lab[i] - o[i]) ** 2 for i in range(3))) for o, _ in mienne)
        else:
            d = 999.0
        echos.append({"hex": mt["hex"], "nom": mt["nom"], "dE_le_plus_proche": round(d, 1)})
    dE = [e["dE_le_plus_proche"] for e in echos]

    score = round(100.0 * points / total, 1) if total else 0.0
    dE_med = median(dE) if dE else 99.0
    if hors_critiques:
        verdict = "HORS STYLE"
    elif score >= 78 and dE_med <= 30:
        verdict = "TIENT"
    elif score >= 58:
        verdict = "A RETOUCHER"
    else:
        verdict = "HORS STYLE"
    return {
        "score_pondere": score,
        "n_controles": total,
        "n_dans": sum(1 for l in lignes if l["etat"] == "DANS"),
        "n_large": sum(1 for l in lignes if l["etat"] == "LARGE"),
        "n_hors": sum(1 for l in lignes if l["etat"] == "HORS"),
        "hors_critiques": hors_critiques,
        "verdict": verdict,
        "lignes": lignes,
        "palette_echos": echos,
        "dE_median_palette": round(dE_med, 1) if dE else None,
    }


# --------------------------------------------------------------------------
# rendu texte
# --------------------------------------------------------------------------

def _barre(part: float, largeur: int = 20) -> str:
    n = int(round(max(0.0, min(1.0, part)) * largeur))
    return "#" * n + "." * (largeur - n)


def tableau_une(m: dict) -> str:
    o = []
    f = m["format"]
    o.append("== %s  (%dx%d px, ratio %.3f, %s)" % (
        m["fichier"], f["largeur"], f["hauteur"], f["ratio_l_sur_h"],
        "portrait" if f["portrait"] else "paysage"))
    o.append("-- palette dominante")
    for e in m["palette"]:
        o.append("   %-8s %5.1f%%  L%5.1f C%5.1f h%6.1f  %-14s %s"
                 % (e["hex"], e["part"] * 100, e["L"], e["C"], e["h"], e["nom"],
                    _barre(e["part"])))
    t = m["tons"]
    o.append("-- tons   L p05/p50/p95 = %.1f / %.1f / %.1f   etendue %.1f"
             % (t["L_p05"], t["L_p50"], t["L_p95"], t["etendue_p05_p95"]))
    o.append("          sombre(L<64) %.1f%%   clair(L>200) %.1f%%"
             % (t["part_sombre_L_moins_64"] * 100, t["part_claire_L_plus_200"] * 100))
    s = m["saturation"]
    o.append("-- satur. S_hsv p50/p95 = %.0f / %.0f   C_lab p50/p95 = %.1f / %.1f   quasi-gris %.1f%%"
             % (s["S_hsv_p50"], s["S_hsv_p95"], s["C_lab_p50"], s["C_lab_p95"],
                s["part_quasi_gris_C_moins_10"] * 100))
    f2 = m.get("fond")
    if f2 and not f2.get("monochrome"):
        o.append("-- fond   %s  h%.0f C%.0f L%.0f  %-13s surface %.1f%%  (toile coloree %.1f%%)"
                 % (f2["hex"], f2["h"], f2["C"], f2["L"], f2["nom"],
                    f2["part_de_surface"] * 100, f2["part_coloree_totale"] * 100))
    elif f2:
        o.append("-- fond   MONOCHROME (toile coloree %.1f%%)" % (f2["part_coloree"] * 100))
    a = m.get("accent")
    if a:
        o.append("-- accent %s  h%.0f C%.0f L%.0f  %-13s surface %.1f%%  noyau %.1f%%  ecart %.0f deg"
                 % (a["hex"], a["h"], a["C"], a["L"], a["nom"],
                    a["part_de_surface"] * 100, a["part_noyau_C30"] * 100,
                    a["ecart_teinte_au_fond"]))
    else:
        o.append("-- accent aucun accent isole (>= %.0f deg du fond)" % ECART_ACCENT)
    c = m["composition"]
    b = c["masse_bbox"]
    o.append("-- compo  centroide (x %.3f, y %.3f)   vide %.1f%%   energie moy %.2f"
             % (c["centroide_x"], c["centroide_y"], c["part_vide_E_moins_4"] * 100,
                c["energie_moyenne"]))
    o.append("          masse bbox x[%.3f-%.3f] y[%.3f-%.3f]  surface %.1f%%  centre_y %.3f"
             % (b["x0"], b["x1"], b["y0"], b["y1"], b["part_surface"] * 100, b["centre_y"]))
    o.append("          tiers (part d'energie) :")
    for r in c["tiers"]:
        o.append("             " + "  ".join("%5.1f%%" % (v * 100) for v in r))
    return "\n".join(o)


def tableau_agrege(a: dict) -> str:
    o = []
    o.append("=" * 78)
    o.append("FICHE AGREGEE -- %d oeuvres" % a["n_oeuvres"])
    o.append("=" * 78)
    f = a.get("formats", {})
    if f:
        for cle in ("portrait", "paysage"):
            d = f.get(cle) or {}
            if d.get("n"):
                o.append("   format %-9s n=%-3d ratio med %.3f  (%.3f .. %.3f)"
                         % (cle, d["n"], d["ratio_med"], d["ratio_min"], d["ratio_max"]))
    o.append("   monochromes : %d / %d      sans accent isole : %d / %d"
             % (a.get("n_monochromes", 0), a["n_oeuvres"],
                a.get("n_sans_accent_isole", 0), a["n_oeuvres"]))
    o.append("")
    o.append("-- PALETTE MAITRE (dominantes de tout le corpus, clusterisees en LAB)")
    o.append("   %-8s %-15s %7s %7s  %6s %6s %6s  %s"
             % ("hex", "nom", "part_moy", "part_rel", "L", "C", "h", "n"))
    for e in a["palette_maitre"]:
        o.append("   %-8s %-15s %6.1f%% %7.1f%%  %6.1f %6.1f %6.1f  %d"
                 % (e["hex"], e["nom"], e["part_moyenne"] * 100, e["part_relative"] * 100,
                    e["L"], e["C"], e["h"], e["n_dominantes"]))
    o.append("")
    o.append("-- METRIQUES (mediane [p25-p75] etendue min-max)")
    for cle, st in a["metriques"].items():
        if not st:
            continue
        o.append("   %-46s %9.3f  [%8.3f - %8.3f]  (%.3f .. %.3f)"
                 % (cle, st["med"], st["p25"], st["p75"], st["min"], st["max"]))
    o.append("")
    o.append("-- GRILLE DES TIERS (part d'energie mediane par cellule)")
    for r in a["tiers_median"]:
        o.append("      " + "  ".join("%5.1f%%" % (v * 100) for v in r))
    return "\n".join(o)


def tableau_verif(v: dict) -> str:
    o = []
    o.append("=" * 78)
    o.append("VERIFICATION -- %s   (score %.1f%% sur %d controles : %d dans / %d large / %d hors)"
             % (v["verdict"], v["score_pondere"], v["n_controles"],
                v["n_dans"], v["n_large"], v["n_hors"]))
    o.append("=" * 78)
    o.append("   %-32s %9s  %-21s %s" % ("metrique (* = critique)", "mesure",
                                         "bande verte p10-p90", "etat"))
    for l in v["lignes"]:
        o.append("   %-32s %9.3f  [%8.3f-%8.3f] %-6s %s"
                 % (l["metrique"] + (" *" if l["critique"] else ""), l["valeur"],
                    l["p10_p90"][0], l["p10_p90"][1],
                    l["etat"], ("ecart %+.3f" % l["ecart"]) if l["ecart"] else ""))
    if v["hors_critiques"]:
        o.append("")
        o.append("   REFUS : axe(s) critique(s) hors corpus -> " + ", ".join(v["hors_critiques"]))
    o.append("")
    o.append("-- echos de palette (dE76 vers la dominante la plus proche de l'image)")
    for e in v["palette_echos"]:
        marque = "ok" if e["dE_le_plus_proche"] <= 25 else "loin"
        o.append("   %-8s %-15s dE %6.1f  %s" % (e["hex"], e["nom"], e["dE_le_plus_proche"], marque))
    if v["dE_median_palette"] is not None:
        o.append("   dE median = %.1f" % v["dE_median_palette"])
    return "\n".join(o)


# --------------------------------------------------------------------------

def lister(dossier: str) -> list[str]:
    out = []
    for nom in sorted(os.listdir(dossier)):
        if nom.lower().endswith(EXTS):
            out.append(os.path.join(dossier, nom))
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Mesureur de style visuel (PIL pur).")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--corpus", help="dossier d'images de reference a agreger")
    g.add_argument("--une", help="une seule image a mesurer")
    g.add_argument("--verifier", help="image generee a juger contre une fiche")
    p.add_argument("--fiche", help="fiche JSON produite par --corpus (requise par --verifier)")
    p.add_argument("--json", help="chemin de sortie JSON")
    p.add_argument("--inset", type=float, default=0.0,
                   help="fraction rognee sur chaque bord (ex. 0.06)")
    p.add_argument("--palette", type=int, default=8, help="couleurs dominantes par image")
    p.add_argument("--clusters", type=int, default=9, help="teintes maitres en sortie")
    p.add_argument("--quiet", action="store_true", help="pas de tableau, JSON seul")
    a = p.parse_args(argv)

    if a.corpus:
        fichiers = lister(a.corpus)
        if not fichiers:
            sys.stderr.write("aucune image dans %s\n" % a.corpus)
            return 2
        mesures = []
        for f in fichiers:
            try:
                m = mesurer(f, a.inset, a.palette)
            except Exception as e:  # une image cassee ne doit pas tuer le corpus
                sys.stderr.write("!! %s : %s\n" % (os.path.basename(f), e))
                continue
            mesures.append(m)
            if not a.quiet:
                print(tableau_une(m))
                print("")
        agg = agreger(mesures, a.clusters)
        agg["inset"] = a.inset
        agg["par_oeuvre"] = mesures
        if not a.quiet:
            print(tableau_agrege(agg))
        if a.json:
            with open(a.json, "w", encoding="utf-8") as fh:
                json.dump(agg, fh, ensure_ascii=False, indent=2)
            sys.stderr.write("JSON -> %s\n" % a.json)
        return 0

    if a.une:
        m = mesurer(a.une, a.inset, a.palette)
        if not a.quiet:
            print(tableau_une(m))
        if a.json:
            with open(a.json, "w", encoding="utf-8") as fh:
                json.dump(m, fh, ensure_ascii=False, indent=2)
        return 0

    # --verifier
    if not a.fiche:
        sys.stderr.write("--verifier exige --fiche\n")
        return 2
    with open(a.fiche, encoding="utf-8") as fh:
        fiche = json.load(fh)
    m = mesurer(a.verifier, a.inset, a.palette)
    v = verifier(m, fiche)
    if not a.quiet:
        print(tableau_une(m))
        print("")
        print(tableau_verif(v))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"mesure": m, "verification": v}, fh, ensure_ascii=False, indent=2)
    return 0 if v["verdict"] != "HORS STYLE" else 1


if __name__ == "__main__":
    sys.exit(main())
