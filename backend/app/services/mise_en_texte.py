# -*- coding: utf-8 -*-
"""t442 (lot M9 « Méthodes », 08/11/2026) — l'AJUSTEMENT DU TEXTE PAR LANGUE de l'agent métier ÉDITEUR ILLUSTRÉ
(méthodes the-picture-book, inside-a-heartbeat : « les mots sont composés, jamais dessinés, pour que les langues
s'échangent sans redessiner »).

`ajuster(textes, police, taille, largeur_px, lignes_max)` met chaque version (fr, en, de…) dans la même boîte de
texte avec une fonte EMBARQUÉE de l'app (mesure réelle des glyphes, Pillow) : lignes coupées aux mots, tient ou non,
et la plus grande taille qui fait tenir la version la plus longue. Local, gratuit, ne dessine rien.
"""
from __future__ import annotations

MAX_TEXTE = 2000
MAX_LANGUES = 12


def _fonte(police: str, taille: int):
    from PIL import ImageFont
    from app.services import subtitle_service as SS
    p = SS.font_path(police)
    if p is None:
        raise ValueError(f"Fonte inconnue : {police} (fontes de l'app : {', '.join(sorted(SS.FONT_FILES))})")
    return ImageFont.truetype(str(p), int(taille))


def couper(texte: str, fonte, largeur: int) -> list[str]:
    """Les lignes du texte coupé aux mots pour tenir dans `largeur` px (un mot plus long qu'une ligne reste seul)."""
    lignes, cour = [], ""
    for para in str(texte).split("\n"):
        for mot in para.split():
            essai = f"{cour} {mot}".strip()
            if not cour or fonte.getlength(essai) <= largeur:
                cour = essai
            else:
                lignes.append(cour)
                cour = mot
        lignes.append(cour)
        cour = ""
    return [l for l in lignes]


def _tient(texte, police, taille, largeur, lignes_max):
    f = _fonte(police, taille)
    ls = couper(texte, f, largeur)
    trop_large = any(f.getlength(l) > largeur for l in ls)
    return ls, len(ls) <= lignes_max and not trop_large


def ajuster(textes: dict, police: str = "Inter", taille: int = 32, largeur_px: int = 600, lignes_max: int = 3) -> dict:
    if not isinstance(textes, dict) or not textes:
        raise ValueError("Donne les textes par langue, par exemple {\"fr\": …, \"en\": …}.")
    if len(textes) > MAX_LANGUES:
        raise ValueError(f"{MAX_LANGUES} langues au plus.")
    try:
        taille, largeur, lmax = int(taille), int(largeur_px), int(lignes_max)
    except (TypeError, ValueError):
        raise ValueError("Taille, largeur et lignes : des entiers.") from None
    if not (6 <= taille <= 400 and 20 <= largeur <= 8000 and 1 <= lmax <= 40):
        raise ValueError("Taille (6-400), largeur (20-8000 px) ou nombre de lignes (1-40) hors bornes.")
    out = {}
    for lg, t in textes.items():
        if not isinstance(t, str) or not t.strip():
            raise ValueError(f"Texte vide pour la langue {lg}.")
        ls, ok = _tient(t[:MAX_TEXTE], police, taille, largeur, lmax)
        out[str(lg)[:8]] = {"lignes": ls, "n_lignes": len(ls), "tient": ok}
    # la plus grande taille (≤ taille demandée) qui fait tenir TOUTES les langues
    commune = None
    for s in range(taille, 5, -1):
        if all(_tient(t[:MAX_TEXTE], police, s, largeur, lmax)[1] for t in textes.values()):
            commune = s
            break
    return {"police": police, "taille": taille, "largeur_px": largeur, "lignes_max": lmax, "langues": out,
            "tout_tient": all(v["tient"] for v in out.values()), "taille_commune": commune}
