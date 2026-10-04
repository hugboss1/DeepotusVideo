# -*- coding: utf-8 -*-
"""Card Forge — pièce 11, sidecar « livret, mockup, fiche produit » (tâche #87 PR C, plan-cartes T18-T19, 04/10/2026).

SIDECAR : aucun `router` (règle 8 — les routes vivent dans edition.py).

LE LIVRET : un livret demande du VRAI texte, et `print.py` n'embarque aucune police (son cartouche est tracé en
chemins) ; `reportlab` est absent du runtime. Les pages sont donc COMPOSÉES par PIL à 300 DPI avec les fontes
réellement servies en /fonts/ (type.fonts_dir — le plan lisait un `settings.fonts_path` qui n'existe pas, donc la
fonte par défaut de PIL partout), puis assemblées en PDF. L'ÉCART EST DIT, à l'écran ET dans l'en-tête du fichier :
le texte n'est pas sélectionnable (aucune couche OCR). Sans conséquence à l'impression ; à savoir à l'écran.
La coupure de ligne est MESURÉE avec la fonte, et un mot plus long qu'une ligne est COUPÉ, jamais jeté.

LE MOCKUP (décision de l'utilisateur, 04/10) : un éventail 2D de cartes déjà rendues, sur un fond uni, aux formats
des réseaux. Aucun moteur 3D ici — la tournette appartient à la pièce 05 (Volume), pas au Forge 3D comme l'écrivait
le plan.

LA FICHE PRODUIT : des chiffres, pas des slogans — format nommé, dimensions, épaisseur du paquet (pièce 05), boîte
calculée par le MÊME patron que la boîte dépliée (forge3d_jeu), langues lues dans la table.
"""
from __future__ import annotations

import io
import math
from typing import Any

from PIL import Image, ImageDraw, ImageFont

__all__ = ["FEUILLES_MM", "MARGE_MM", "CAP_PX", "INTERLIGNE", "FONTE_DEFAUT", "TEXTE_MAX", "IMAGES_MAX",
           "polices", "police", "paginer", "build_livret", "MOCKUP_CIBLES", "MOCKUP_MAX", "mockup_plan", "mockup",
           "fiche"]

DPI = 300
FEUILLES_MM = {"a5": (148.0, 210.0), "a4": (210.0, 297.0), "carre": (210.0, 210.0)}
MARGE_MM = 15.0
CAP_PX = 38            # corps du texte à 300 DPI ≈ 9 pt
INTERLIGNE = 1.45
FONTE_DEFAUT = "Inter.ttf"
TEXTE_MAX = 200_000    # caractères
IMAGES_MAX = 120       # cartes de la planche finale


def _px(mm: float) -> int:
    return int(round(mm / 25.4 * DPI))     # la règle d'arrondi du contrat (contract.px)


def polices() -> list:
    """Les fontes servies (.ttf / .otf), telles quelles : on ne devine jamais l'extension."""
    from .type import fonts_dir
    d = fonts_dir()
    return sorted(p.name for p in d.iterdir() if p.suffix.lower() in (".ttf", ".otf")) if d.is_dir() else []


def police(nom: str = "", taille: int = CAP_PX):
    """Une fonte servie par l'application, sinon la fonte par défaut de PIL (toujours lisible)."""
    from pathlib import Path
    from .type import fonts_dir
    for n in ([Path(str(nom)).name] if nom else []) + [FONTE_DEFAUT]:
        p = fonts_dir() / n
        if p.is_file():
            try:
                return ImageFont.truetype(str(p), int(taille))
            except OSError:
                continue
    return ImageFont.load_default(int(taille))


def _lignes(texte: str, utile: int, fnt, fnt_titre) -> list:
    """Le texte -> [(genre, texte)] : « # … » en début de paragraphe est un intertitre, une ligne vide un blanc."""
    sonde = ImageDraw.Draw(Image.new("L", (8, 8)))
    out = []
    for para in str(texte or "").replace("\r\n", "\n").split("\n"):
        if not para.strip():
            out.append(("blanc", ""))
            continue
        genre, f = ("titre", fnt_titre) if para.lstrip().startswith("# ") else ("texte", fnt)
        para = para.lstrip()[2:].strip() if genre == "titre" else para
        cur = ""
        for mot in para.split(" "):
            essai = (cur + " " + mot).strip() if cur else mot
            if sonde.textlength(essai, font=f) <= utile:
                cur = essai
                continue
            if cur:
                out.append((genre, cur))
                cur = ""
            while sonde.textlength(mot, font=f) > utile and len(mot) > 1:     # COUPÉ, pas jeté
                lo, hi = 1, len(mot) - 1                  # le plus long préfixe qui tient : dichotomie, pas un recul
                while lo < hi:                            # caractère par caractère (O(n²) sur une URL collée)
                    mid = (lo + hi + 1) // 2
                    if sonde.textlength(mot[:mid], font=f) <= utile:
                        lo = mid
                    else:
                        hi = mid - 1
                n = lo
                out.append((genre, mot[:n]))
                mot = mot[n:]
            cur = mot
        if cur:
            out.append((genre, cur))
    return out


def paginer(texte: str, feuille: str = "a5", cap_px: int = CAP_PX, fonte: str = "", titre: str = "") -> dict:
    """-> {pages: [[(genre, texte)]], w, h, marge, ...}. La hauteur se COMPTE ligne par ligne (un intertitre est
    plus haut), et la première page réserve la place du titre."""
    if str(feuille) not in FEUILLES_MM:
        raise ValueError(f"Feuille inconnue : « {feuille} » ({', '.join(FEUILLES_MM)})")
    if not 20 <= int(cap_px) <= 90:
        raise ValueError("Le corps du texte doit tenir entre 20 et 90 px (à 300 DPI)")
    if len(str(texte or "")) > TEXTE_MAX:
        raise ValueError(f"Texte trop long ({len(texte)} caractères, {TEXTE_MAX} au plus)")
    w, h = (_px(v) for v in FEUILLES_MM[feuille])
    m = _px(MARGE_MM)
    fnt, fnt_t = police(fonte, cap_px), police(fonte, int(cap_px * 1.35))
    lignes = _lignes(texte, w - 2 * m, fnt, fnt_t)
    haut = {"texte": cap_px * INTERLIGNE, "blanc": cap_px * 0.6, "titre": cap_px * 1.35 * INTERLIGNE + cap_px * 0.4}
    bas = h - m - cap_px * 2.0                       # la place du folio
    pages, page, y = [], [], m + (cap_px * 2.0 * INTERLIGNE + cap_px if titre else 0)
    for g, t in lignes:
        if page and y + haut[g] > bas:
            pages.append(page)
            page, y = [], m
        if g == "blanc" and not page:
            continue                                  # pas de blanc en tête de page
        page.append((g, t))
        y += haut[g]
    if page or not pages:
        pages.append(page)
    return {"pages": pages, "w": w, "h": h, "marge": m, "cap": int(cap_px), "fnt": fnt, "fnt_t": fnt_t, "haut": haut}


def _planches(images: list, w: int, h: int, m: int) -> list:
    """La planche des cartes en fin de livret : 3 colonnes, proportions de la carte gardées."""
    if not images:
        return []
    cols = 3
    gap = _px(3.0)
    cw = (w - 2 * m - (cols - 1) * gap) // cols
    a, b = images[0].size
    ch = max(1, int(cw * b / a))
    par_col = max(1, (h - 2 * m + gap) // (ch + gap))
    par_page = cols * par_col
    out = []
    for k in range(0, len(images), par_page):
        pg = Image.new("RGB", (w, h), (255, 255, 255))
        for j, im in enumerate(images[k:k + par_page]):
            r, c = divmod(j, cols)
            pg.paste(im.convert("RGB").resize((cw, ch), Image.LANCZOS), (m + c * (cw + gap), m + r * (ch + gap)))
        out.append(pg)
    return out


def build_livret(titre: str, texte: str, images: list, feuille: str = "a5", cap_px: int = CAP_PX,
                 fonte: str = "") -> tuple:
    """Le livret complet -> (octets PDF, pages de texte, pages de cartes)."""
    if len(images or ()) > IMAGES_MAX:
        raise ValueError(f"Trop de cartes pour la planche ({len(images)}, {IMAGES_MAX} au plus)")
    P = paginer(texte, feuille, cap_px, fonte, titre)
    w, h, m, cap = P["w"], P["h"], P["marge"], P["cap"]
    ims = []
    for i, lignes in enumerate(P["pages"]):
        im = Image.new("RGB", (w, h), (255, 255, 255))
        d = ImageDraw.Draw(im)
        y = float(m)
        if titre and i == 0:
            d.text((m, y), str(titre), font=police(fonte, int(cap * 2.0)), fill=(0, 0, 0))
            y += cap * 2.0 * INTERLIGNE + cap
        for g, t in lignes:
            if g == "titre":
                y += cap * 0.4
                d.text((m, y), t, font=P["fnt_t"], fill=(0, 0, 0))
                y += cap * 1.35 * INTERLIGNE
            elif g == "texte":
                d.text((m, y), t, font=P["fnt"], fill=(25, 25, 25))
                y += cap * INTERLIGNE
            else:
                y += cap * 0.6
        d.text((w // 2, h - m // 2), str(i + 1), font=P["fnt"], fill=(120, 120, 120), anchor="mm")
        ims.append(im)
    n_txt = len(ims)
    ims += _planches(list(images or ()), w, h, m)
    Image.init()                                       # PIÈGE 14 DE LA SPEC : sinon KeyError 'JPEG' en production
    buf = io.BytesIO()
    ims[0].save(buf, "PDF", resolution=float(DPI), save_all=True, append_images=ims[1:])
    return buf.getvalue(), n_txt, len(ims) - n_txt


# ── MOCKUP ───────────────────────────────────────────────────────────────────────────────────────────────────────
MOCKUP_CIBLES = {"carre": (1080, 1080), "story": (1080, 1920), "paysage": (1600, 900)}
MOCKUP_MAX = 5          # au-delà, l'éventail devient bouillie — et c'est dit (en-tête)


def _couleur(v: Any, defaut: tuple) -> tuple:
    s = str(v or "").strip().lstrip("#")
    if len(s) == 6:
        try:
            return tuple(int(s[k:k + 2], 16) for k in (0, 2, 4))
        except ValueError:
            pass
    return defaut


def mockup_plan(tailles: list, cible: str = "carre") -> tuple:
    """-> ((w, h), plan). `tailles` = [(w, h)] des cartes montrées (5 au plus). L'éventail tient dans 80 % de la
    largeur et 62 % de la hauteur, cartes tournées de -12° à +12°."""
    if str(cible) not in MOCKUP_CIBLES:
        raise ValueError(f"Cible inconnue : « {cible} » ({', '.join(MOCKUP_CIBLES)})")
    if not tailles:
        raise ValueError("Aucune carte reçue pour le mockup")
    w, h = MOCKUP_CIBLES[cible]
    n = min(len(tailles), MOCKUP_MAX)
    a, b = tailles[0]
    ch = int(h * 0.62)
    cw = int(ch * a / b)
    pas = int(cw * 0.42)
    if cw + pas * (n - 1) > w * 0.8:                    # trop large : on réduit tout
        k = (w * 0.8) / (cw + pas * (n - 1))
        cw, ch, pas = int(cw * k), int(ch * k), int(pas * k)
    x0 = (w - (cw + pas * (n - 1))) // 2
    y0 = int(h * 0.53 - ch / 2)
    rot = [0.0] if n == 1 else [12.0 - 24.0 * i / (n - 1) for i in range(n)]
    plan = [{"i": i, "x": x0 + i * pas, "y": y0 + int(abs(rot[i]) * ch * 0.006), "w": cw, "h": ch, "rot": rot[i]}
            for i in range(n)]
    return (w, h), plan


def a_la_coupe(im: Image.Image, rogne: Any = None, rayon_px: float = 0.0) -> Image.Image:
    """La carte TELLE QU'ELLE SORT DU MASSICOT : rognée du fond perdu (`rogne` = boîte x0, y0, x1, y1) et aux coins
    arrondis (rayon en px du rendu). Un mockup qui montre le fond perdu montre des bandes que personne ne verra."""
    c = im.convert("RGBA")
    if rogne:
        c = c.crop(tuple(int(v) for v in rogne))
    r = int(round(rayon_px))
    if r > 0:
        masque = Image.new("L", c.size, 0)
        ImageDraw.Draw(masque).rounded_rectangle((0, 0, c.size[0] - 1, c.size[1] - 1), radius=r, fill=255)
        alpha = c.getchannel("A")
        c.putalpha(Image.composite(alpha, masque, masque))
    return c


def mockup(cartes: list, cible: str = "carre", titre: str = "", sous_titre: str = "", fond: Any = "",
           fonte: str = "") -> Image.Image:
    (w, h), plan = mockup_plan([c.size for c in cartes], cible)
    bg = _couleur(fond, (14, 18, 24))
    im = Image.new("RGB", (w, h), bg)
    for p in plan:
        c = cartes[p["i"]].convert("RGBA").resize((p["w"], p["h"]), Image.LANCZOS)
        c = c.rotate(p["rot"], expand=True, resample=Image.BICUBIC)
        im.paste(c, (p["x"] - (c.size[0] - p["w"]) // 2, p["y"] - (c.size[1] - p["h"]) // 2), c)
    d = ImageDraw.Draw(im)
    clair = sum(bg) / 3 < 128
    cap = max(24, w // 18)
    if titre:
        d.text((w // 2, int(h * 0.11)), str(titre), font=police(fonte, cap), anchor="mm",
               fill=(240, 244, 248) if clair else (16, 18, 22))
    if sous_titre:
        d.text((w // 2, int(h * 0.92)), str(sous_titre), font=police(fonte, int(cap * 0.6)), anchor="mm",
               fill=(170, 180, 190) if clair else (70, 76, 84))
    return im


# ── FICHE PRODUIT ────────────────────────────────────────────────────────────────────────────────────────────────
def fiche(doc: dict, cartes: int, ep_carte_mm: float) -> dict:
    """Des chiffres : ce qu'une boutique demande, et ce que le vendeur recopie de travers à la main."""
    from .contract import FORMATS
    from .core import geom_of
    from .data import LANG_NOMS, langues_table
    from .forge3d_jeu import JEU_MM_DEFAUT, RABAT_MM_DEFAUT, epaisseur_deck_mm, patron_boite
    n = int(cartes)
    if not 1 <= n <= 5000:
        raise ValueError("« cartes » doit tenir entre 1 et 5000")
    g = geom_of(doc)
    ep = round(epaisseur_deck_mm(n, ep_carte_mm), 2)
    try:
        boite = patron_boite(g.trim_mm[0], g.trim_mm[1], ep, JEU_MM_DEFAUT, RABAT_MM_DEFAUT,
                             {"libre": (10000.0, 10000.0)}, "libre")["boite_mm"]
    except ValueError:
        boite = None
    cols = ((doc.get("data") or {}).get("columns") or []) if isinstance(doc.get("data"), dict) else []
    codes = [l["code"] for l in langues_table(cols)["langues"]]
    langues = [LANG_NOMS.get(c.split("-")[0], c) for c in codes]
    fmt = FORMATS.get(g.fmt, {}).get("label", g.fmt)
    dims = [round(v, 2) for v in g.trim_mm]
    fr = lambda v: ("%g" % v).replace(".", ",")
    texte = (f"{n} cartes au format {fmt} ({fr(dims[0])} × {fr(dims[1])} mm). Paquet de {fr(ep)} mm "
             f"({fr(ep_carte_mm)} mm par carte)."
             + (f" Boîte de {fr(boite[0])} × {fr(boite[1])} × {fr(boite[2])} mm." if boite else "")
             + (f" Langues : {', '.join(langues)}." if langues else ""))
    return {"nom": str(doc.get("name") or ""), "cartes": n, "format": fmt, "dimensions_mm": dims,
            "epaisseur_carte_mm": float(ep_carte_mm), "epaisseur_deck_mm": ep, "boite_mm": boite,
            "langues": langues, "texte": texte}
