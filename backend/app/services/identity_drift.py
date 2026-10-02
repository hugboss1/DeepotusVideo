"""Tâche #62 (plan chapitres T6, 02/10/2026) — mesurer la dérive d'identité entre deux images, en PIL pur
(numpy est ABSENT du python embarqué — mesuré le 03/09). Lecture seule : la mesure est AFFICHÉE, elle ne décide rien.

CE QUE ÇA MESURE
  1. `ecart_couleur` — la distance entre les PALETTES : les 8 couleurs dominantes de chaque image (quantize MEDIANCUT,
     le moteur de board_service._palette_colors), appariées au plus proche voisin dans les DEUX sens, en ΔE76 sur
     L*a*b* (la colorimétrie de cards/style_walkuski, pas une seconde copie), pondérées par la part de surface.
     Unité : ΔE (0 = identique ; ~2,3 = seuil de perception ; > 10 = deux couleurs franchement différentes).
  2. `ecart_silhouette` — la distance entre les OCCUPATIONS : chaque image réduite à une grille 16×16 « sujet / fond »,
     le fond étant la couleur dominante du BORD. Distance = 1 − Jaccard (0 = mêmes cases, 1 = aucune case commune).
     Le fond est la MOYENNE EXACTE des pixels du bord de la famille dominante — le plan l'arrondissait au pas de 16
     (vers le bas) : un fond sombre décalé de ~8 ΔE faisait passer pour du sujet un voile à peine visible.

CE QUE ÇA NE MESURE PAS — et ne pourra pas dans ce runtime
  - LE VISAGE : aucun modèle d'identité faciale (numpy absent). Deux figures au même costume, à la même carrure, aux
    traits différents, sortent à 0. C'est une ALARME DE RÉGRESSION, jamais une preuve d'identité.
  - LA COMPARAISON ENTRE NATURES DIFFÉRENTES : un plan avec décor n'a ni la palette ni l'occupation d'un panneau de
    planche sur fond uni ; l'écran le dit à côté du chiffre.
  - LA POSE : un personnage identique vu de dos change de silhouette autant qu'un personnage remplacé.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from PIL import Image

from app.services.cards.style_walkuski import rgb_vers_lab as lab

CE_QUE_CA_NE_MESURE_PAS = (
    "le visage (aucun modèle d'identité faciale, numpy absent), la "
    "comparaison entre natures d'image différentes, et la pose"
)

SEUIL_COULEUR = 8.0      # ΔE76 au-delà duquel on parle de dérive
SEUIL_SILHOUETTE = 0.12  # 1 − Jaccard au-delà duquel idem


def de76(a, b) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5


def palette(im: Image.Image, n: int = 8) -> list[tuple[float, tuple]]:
    """[(part de surface, (r,g,b))], du plus dominant au moins. Somme = 1."""
    small = im.convert("RGB").resize((96, 96), Image.LANCZOS)
    q = small.quantize(colors=n, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal = q.getpalette()
    counts = {i: c for c, i in (q.getcolors(256) or [])}
    total = sum(counts.values()) or 1
    out = [(counts[i] / total, tuple(pal[i * 3:i * 3 + 3])) for i in sorted(counts) if counts[i]]
    return sorted(out, reverse=True)


def _sens(a, b) -> float:
    labs_b = [lab(c) for _, c in b]
    return sum(w * min(de76(lab(c), lb) for lb in labs_b) for w, c in a)


def ecart_couleur(pa, pb) -> float:
    """ΔE76 moyen, apparié au plus proche voisin dans les DEUX sens : un seul sens récompenserait l'image la plus
    pauvre en couleurs."""
    if not pa or not pb:
        return 100.0
    return round((_sens(pa, pb) + _sens(pb, pa)) / 2, 3)


def _fond(im: Image.Image) -> tuple[int, int, int]:
    """La couleur du BORD : la famille dominante (pas de 16) désigne le fond, sa MOYENNE exacte le donne."""
    w, h = im.size
    px = im.load()
    bord = ([px[x, 0] for x in range(w)] + [px[x, h - 1] for x in range(w)]
            + [px[0, y] for y in range(h)] + [px[w - 1, y] for y in range(h)])
    fam = Counter((r // 16, g // 16, b // 16) for r, g, b in bord).most_common(1)[0][0]
    sel = [p for p in bord if (p[0] // 16, p[1] // 16, p[2] // 16) == fam]
    return tuple(round(sum(p[i] for p in sel) / len(sel)) for i in range(3))


def occupation(im: Image.Image, grille: int = 16, seuil: float = 12.0) -> list[bool]:
    """Grille grille×grille : True = la case est majoritairement du SUJET (plus de la moitié de ses pixels à plus de
    `seuil` ΔE du fond)."""
    small = im.convert("RGB").resize((grille * 4, grille * 4), Image.LANCZOS)
    lf = lab(_fond(small))
    px = small.load()
    cells = []
    for cy in range(grille):
        for cx in range(grille):
            sujet = sum(1 for y in range(cy * 4, cy * 4 + 4) for x in range(cx * 4, cx * 4 + 4)
                        if de76(lab(px[x, y]), lf) > seuil)
            cells.append(sujet > 8)
    return cells


def ecart_silhouette(oa: list[bool], ob: list[bool]) -> float:
    """1 − Jaccard. Deux images sans aucun sujet détecté : 0 (rien à comparer, on ne crie pas au loup)."""
    inter = sum(1 for a, b in zip(oa, ob) if a and b)
    union = sum(1 for a, b in zip(oa, ob) if a or b)
    return 0.0 if not union else round(1 - inter / union, 4)


def derive(reference, genere) -> dict:
    """La mesure complète entre deux images (chemins ou Image). `verdict` = "stable" tant que les DEUX écarts sont
    sous leur seuil."""
    a = reference if isinstance(reference, Image.Image) else Image.open(Path(reference))
    b = genere if isinstance(genere, Image.Image) else Image.open(Path(genere))
    a, b = a.convert("RGB"), b.convert("RGB")
    ec = ecart_couleur(palette(a), palette(b))
    es = ecart_silhouette(occupation(a), occupation(b))
    return {"ecart_couleur": ec, "ecart_silhouette": es,
            "verdict": "stable" if ec <= SEUIL_COULEUR and es <= SEUIL_SILHOUETTE else "derive",
            "seuils": {"couleur": SEUIL_COULEUR, "silhouette": SEUIL_SILHOUETTE},
            "angle_mort": CE_QUE_CA_NE_MESURE_PAS}
